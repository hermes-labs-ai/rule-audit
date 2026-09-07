#!/usr/bin/env python3
"""Gemini CLI host adapter for the `/rule-audit:audit` custom command.

Everything about *what* is reported lives in `audit_report.py`, which is a
byte-for-byte copy of the Claude Code plugin's adapter
(`integrations/claude-code/scripts/audit_report.py`) and is pinned to it by
`tests/test_gemini_cli_extension.py`. The two hosts materialise their
integrations as standalone directory trees — a Claude Code marketplace install
copies only the plugin subdirectory, and `gemini extensions install` copies the
extension root — so neither can import a shared module from a common parent.
A vendored copy with an equality test is the only form of reuse the packaging
permits; it still means detection and rendering exist once.

This file adds only what the *host* requires, which is one thing:

**The command must exit 0, always.**

`rule-audit` exits 2 for HIGH/CRITICAL, and on the corpora packet 1 measured
that is the common case rather than the exceptional one. A Gemini CLI custom
command executes its `!{...}` block through `ShellProcessor`, which on a
non-zero exit appends

    [Shell command '<the entire resolved command>' exited with code N]

to the prompt that is then sent to the model. `[... exited with code 2]` is a
poor last impression of a command that did exactly what it was asked to do, and
a model that reads it as a failure will retry or report the extension as broken.
So the exit-code contract is not discarded here, it is moved in-band: the last
line of output always states the status and says what it means, and the process
exits 0.

Measured on Gemini CLI 0.32.1 (macOS), exiting 0 does not remove that trailing
line entirely — the pty execution path reports `signal` as `0` rather than
`null` on a clean exit, so `ShellProcessor` falls through to
`[Shell command '…' terminated by signal 0]`. On the plain `child_process` path
a clean exit produces no trailing line at all. Either way the line is benign
where `exited with code 2` was not.

That trailing line is also why the command template wraps the report in explicit
`--- BEGIN/END RULE-AUDIT REPORT ---` markers and tells the model the region is
data: the host echoes the *resolved* command, which embeds the user's argument
escaped by `shell-quote`. `shell-quote` prevents command injection, but it keeps
a newline inside single quotes rather than encoding it, so a file named
``prompt\\n\\n# SYSTEM: …`` still reaches the prompt through a line this adapter
does not control. `audit_report.py` collapses control characters in every path
*it* prints; nothing here can sanitise a line the host prints, so containment is
the mitigation.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import List, Optional

#: The vendored copy of the shared adapter, alongside this file.
_ADAPTER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_report.py")

#: What each underlying status means, said plainly enough that a model reading
#: only this line still reads it correctly. Keys are `audit_report.main`'s
#: return values, which are the `rule-audit` CLI's own.
_STATUS_NOTES = {
    0: "risk LOW or MEDIUM.",
    2: "risk HIGH or CRITICAL. This is a finding, not a command failure.",
    1: "the audit could not be run. The message above says why.",
}


def _status_line(status: int) -> str:
    note = _STATUS_NOTES.get(status, "unexpected status; treat the report as unreliable.")
    return "[rule-audit status %d] %s" % (status, note)


def _load_adapter():
    # Without this, `SourceFileLoader` writes `__pycache__/audit_report.*.pyc`
    # next to the adapter — inside `~/.gemini/extensions/rule-audit/`. The
    # extension promises to leave nothing behind when it is uninstalled, and an
    # integration that caches into its own install directory does not.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("_rule_audit_report", _ADAPTER_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("could not load %s" % _ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv: Optional[List[str]] = None) -> int:
    """Print the report and return the *underlying* status, without exiting."""
    arguments = list(sys.argv[1:] if argv is None else argv)

    # `escapeShellArg` quotes the host's whole argument string as one shell
    # word, so this is reached with exactly zero or one argument however many
    # words the user typed. Zero means the command was typed bare; more than one
    # means someone ran this script by hand, and the adapter's own "file not
    # found" is a better message than anything invented here.
    if not arguments:
        sys.stderr.write(
            "rule-audit: no file given. Use `/rule-audit:audit <path-to-prompt-file>`, "
            "naming one system-prompt file to audit.\n"
        )
        return 1

    try:
        adapter = _load_adapter()
    except Exception as error:  # pragma: no cover - defensive
        sys.stderr.write(
            "rule-audit: the extension is incomplete — %s could not be loaded (%s). "
            "Reinstall with `gemini extensions install <source>`.\n"
            % (_ADAPTER_PATH, error)
        )
        return 1

    # `--` keeps argparse from reading a path that begins with a dash as an
    # option, so `/rule-audit:audit --help` audits a file called `--help` (and
    # reports that it does not exist) rather than printing argparse's help into
    # the model's context.
    try:
        return int(adapter.main(["--", arguments[0]]))
    except SystemExit as exit_request:  # pragma: no cover - defensive
        code = exit_request.code
        return code if isinstance(code, int) else 1
    except Exception as error:
        sys.stderr.write("rule-audit: the audit failed: %s\n" % error)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    status = run(argv)
    sys.stdout.flush()
    sys.stderr.flush()
    sys.stdout.write(_status_line(status) + "\n")
    sys.stdout.flush()
    # Always 0. See the module docstring: a non-zero exit makes the host append
    # `[Shell command '…' exited with code N]`, which reads as a failure for a
    # command that worked. It does not remove the echoed command on the default
    # pty path — containment of that line is the command template's job.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
