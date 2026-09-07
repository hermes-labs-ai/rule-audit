"""Hermes Agent host adapter for the `/rule-audit` slash command.

Everything about *what* is reported lives in `audit_report.py`, which is a
byte-for-byte copy of the Claude Code plugin's adapter
(`integrations/claude-code/scripts/audit_report.py`) and is pinned to it by
`tests/test_hermes_agent_plugin.py`. `hermes plugins install` copies one
directory out of the repository, so this tree cannot import a shared module
from a common parent — the same packaging constraint the Gemini CLI extension
documents. A vendored copy with an equality test is the only reuse the
packaging permits; detection and rendering still exist once.

This file adds only what the *host* requires. Four things.

**1. The report is returned, not printed.**

A Hermes plugin slash command is `handler(raw_args: str) -> str | None`, and the
host decides where the string goes: `cli.py::_run_plugin_slash_command` prints
it to the terminal, the TUI returns it over JSON-RPC, and the gateway sends it
as the reply message on Telegram/Discord/Slack. In every case it goes **to the
user and never into the model's context** — the handler runs before any API
call and its result is not appended to the conversation.

That is the substantive difference from the Claude Code and Gemini CLI lanes,
where the identical report is text a model is asked to read. Here nothing this
returns can instruct the agent, so the report needs no prompt-injection
containment. It needs terminal containment instead, which is (2).

**2. Control characters are stripped from the returned string.**

`_run_plugin_slash_command` hands the string to `_cprint`, which renders it
through prompt_toolkit's ANSI parser. An escape sequence surviving into that
string would be *interpreted* — cursor moves, colour, screen clears — by a
terminal showing the user a security report about a file they do not trust.
`audit_report.py` already collapses control characters in every value it
interpolates; this is the host-specific second pass at the boundary that owns
the hazard, because this is the host whose display channel parses them.

**3. The status is transposed into text.**

`rule-audit` exits 0 for LOW/MEDIUM, 2 for HIGH/CRITICAL and 1 on failure. That
exit code has nowhere to go here — the handler returns a string — so it is
carried in-band as a final `[rule-audit status N]` line. Without it a failed
audit and a clean one would be told apart only by the presence of a report,
which is exactly the confusion the Gemini CLI lane had to fix.

**4. Bare `/rule-audit` audits the agent's own SOUL.md.**

`SOUL.md` is the first section of the Hermes system prompt and replaces the
default agent identity, so it is a user-authored system prompt — the input
rule-audit is calibrated for. It is resolved through `get_hermes_home()`, the
host's own accessor, so the active profile is honoured rather than assuming
`~/.hermes`.

**Why a command and not a hook.** Hermes offers `on_session_start` and
`post_tool_call`, and this plugin registers neither. rule-audit's risk label
fires on 65-86% of real instruction and prompt files, ~44% of those verdicts
contain no contradiction at all, and an empty file scores HIGH at 40/100 from
the coverage-gap floor alone. Those numbers are a property of the analyzer, not
of any host. They are fine for an audit a user asked for and read; they are not
a basis for interrupting every session unbidden. The measurements are in the
plugin README.
"""

from __future__ import annotations

import os
import signal
import subprocess
import unicodedata
import sys
from pathlib import Path
from typing import List, Optional

#: The vendored copy of the shared adapter, alongside this file.
_ADAPTER_PATH = Path(__file__).resolve().parent / "audit_report.py"

#: Whether to put the adapter in its own process group. POSIX only — `setsid`
#: has no Windows equivalent, and there `Popen.kill` reaches the adapter but not
#: the `rule-audit` analyzer beneath it. Stated rather than silently
#: platform-dependent.
_NEW_SESSION = os.name == "posix"

#: Wall-clock ceiling for the whole audit. `audit_report.py` allows its own
#: `rule-audit` call 120s, but a Hermes slash command is dispatched
#: synchronously — `_run_plugin_slash_command` blocks the REPL, and the 30s
#: guard in `resolve_plugin_command_result` covers async handlers only. The
#: adapter refuses inputs over 64 KB and 64 KB of dense rule text measures in
#: single-digit seconds, so this is roughly 20x headroom over the worst input
#: the adapter will accept, chosen to bound the session rather than the audit.
TIMEOUT_SECONDS = 60

#: Runaway guard on the returned string. The adapter already caps findings per
#: family and characters per quote, which puts a real report in the low
#: kilobytes; this only catches a report that somehow escapes those caps. Chat
#: platforms impose their own, smaller limits (Telegram splits at 4096
#: characters) and will split or truncate independently of this.
MAX_OUTPUT_CHARS = 12_000

#: What each status means, said plainly. Keys are `audit_report.main`'s return
#: values, which are the `rule-audit` CLI's own.
_STATUS_NOTES = {
    0: "risk LOW or MEDIUM.",
    2: "risk HIGH or CRITICAL. This is a finding, not a command failure.",
    1: "the audit could not be run. The message above says why.",
}

_USAGE = "Usage: /rule-audit [path]  —  with no path, audits your SOUL.md."

#: Every message this returns is prefixed `rule-audit: `, and the adapter
#: prefixes its own stderr the same way. Without stripping one, a failure
#: relayed from the adapter reads `rule-audit: rule-audit: file not found`.
_ADAPTER_PREFIX = "rule-audit: "

#: Unicode general categories that are never displayed as themselves: Cc is the
#: C0/C1 control characters, Cf the format characters. Newline is exempt because
#: it is the report's own line structure.
#:
#: Cf matters as much as Cc here and is easy to miss. It carries the bidi
#: overrides (U+202A-202E, U+2066-2069): a rule quoted out of a hostile prompt
#: file containing U+202E renders right-to-left from that point, so the report
#: can be made to show the reverse of what was found — in a terminal, and on
#: Telegram, Discord and Slack, all of which apply the bidi algorithm. It also
#: carries the zero-width and invisible characters (U+200B, U+00AD, U+FEFF)
#: that hide text outright.
#:
#: Matching on the category rather than a hand-written range list is deliberate:
#: an explicit list is exactly as incomplete as whoever wrote it, and this text
#: comes out of a file the user has been told not to trust.
_DISPLAYABLE_EXEMPT = "\n"


def _sanitize(text: str) -> str:
    """Neutralise anything the terminal or a chat client would act on rather than show."""
    return "".join(
        character
        if character in _DISPLAYABLE_EXEMPT
        or unicodedata.category(character) not in ("Cc", "Cf")
        else " "
        for character in text
    )


def hermes_home() -> Path:
    """The active Hermes home, via the host's own accessor when it is importable.

    `get_hermes_home()` resolves the context-local override, then `HERMES_HOME`,
    then the platform default, so a user running a non-default profile gets that
    profile's SOUL.md. The fallback mirrors `hermes_constants` for the two cases
    it can reach and exists so this module is importable outside a Hermes
    process (its own tests, or a direct `python hermes_audit.py` run).
    """
    try:
        from hermes_constants import get_hermes_home  # type: ignore[import-not-found]

        return Path(get_hermes_home())
    except Exception:
        override = os.environ.get("HERMES_HOME", "").strip()
        if override:
            return Path(override)
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
            if local_appdata:
                return Path(local_appdata) / "hermes"
        try:
            base = Path.home()
        except (RuntimeError, OSError):
            # `Path.home()` raises when no home directory can be determined.
            # There is then no SOUL.md to default to, so return a path that
            # simply will not exist: the caller reports "file not found" and
            # the usage hint, which is true and useful, rather than crashing.
            return Path(".hermes")
        if sys.platform == "win32":
            return base / "AppData" / "Local" / "hermes"
        return base / ".hermes"


def soul_path() -> Path:
    """The SOUL.md of the active profile."""
    return hermes_home() / "SOUL.md"


def _clean_arg(raw_args: str) -> str:
    """The typed argument with surrounding whitespace and one quote pair removed.

    Users type quotes out of shell habit, and `/rule-audit ""` means the same
    thing as `/rule-audit` — so emptiness is re-tested after unquoting rather
    than before, which is what keeps `""` from resolving to `Path(".")` and
    reporting that the current directory is not a file.
    """
    text = raw_args.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


def resolve_target(raw_args: str) -> Path:
    """Turn the raw argument string into the path to audit.

    The host hands over everything typed after the command name as one unsplit
    string and no shell is involved, so a path containing spaces is simply
    itself — splitting it into words would break exactly the filenames that need
    no escaping. `~` is expanded because there is no shell here to do it.

    `expanduser()` raises rather than returning the input for `~nosuchuser`, and
    on a system where the home directory cannot be determined at all. This must
    not raise: `audit()` calls it before its own try block, and a slash-command
    handler that raises is not merely ugly — on the gateway,
    `run_inbound.py` treats the exception as "not handled" and falls through to
    sending the user's text to the model as an ordinary chat turn, which is a
    billed LLM call for a command that was supposed to run locally.
    """
    text = _clean_arg(raw_args)
    if not text:
        return soul_path()
    try:
        return Path(text).expanduser()
    except (RuntimeError, OSError):
        # An unresolvable `~user` is not a path this can audit, but the adapter
        # saying "file not found: ~nosuchuser/x.md" is a true and useful answer.
        return Path(text)


def _status_line(status: int) -> str:
    note = _STATUS_NOTES.get(status, "unexpected status; treat the report as unreliable.")
    return "[rule-audit status %d] %s" % (status, note)


def _kill_process_tree(process: "subprocess.Popen[str]") -> bool:
    """Kill the adapter *and* the analyzer it started. True if the tree was reached.

    There are two processes below this one — this module starts
    `audit_report.py`, which starts `rule-audit` — and the O(n^2), CPU-bound
    work that makes a timeout necessary at all is in that grandchild. Killing
    the adapter alone leaves it orphaned and still running, while the caller
    reports that the audit "was stopped": a false statement and a runaway
    process on the user's machine at once. (Found by the Codex lane's review
    of the identical shape in that plugin's wrapper, then confirmed here.)

    Two mechanisms, because there is no portable one. On POSIX,
    `start_new_session` puts the adapter in its own process group and one
    `killpg` reaches every descendant. On Windows there is no `setsid`, so this
    shells out to `taskkill /T`, which walks the child tree by PID.

    The POSIX branch signals the process group by *number*, not by looking it
    up through `os.getpgid(process.pid)`. That lookup is a real race, not a
    hypothetical one: `start_new_session=True` makes the adapter the leader of
    a new session, so its PGID equals its PID at the moment it is created — we
    already know the number. Querying it anyway fails exactly when it matters
    most: if the adapter itself has already exited while its `rule-audit`
    grandchild is still running and holding the inherited stdout/stderr pipes
    (which is why `communicate()` timed out at all), `process.pid` no longer
    names a live process, `getpgid` raises `ProcessLookupError`, and the
    fallback `process.kill()` cannot reach a PID that is already gone —
    leaving the live grandchild unsignalled. Killing by the known PGID number
    has no such lookup step to race. (Found by `hermes-gate review`, critical,
    after the lookup form shipped in both this wrapper and the Codex lane's.)

    The return value is not decoration. Both mechanisms can fail — most
    plausibly a permissions refusal, or `taskkill` not on `PATH` — and the
    caller words its message differently when the analyzer may still be
    alive. Claiming "stopped" for something that was not stopped is the
    defect this function exists to prevent; doing that in the failure branch
    would be the same defect in a smaller place.
    """
    if _NEW_SESSION and hasattr(os, "killpg"):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return True
        except (OSError, ProcessLookupError):
            # The whole group is already gone (nothing left to signal — the
            # good case) or signalling it was refused. Either way, fall
            # through to the direct kill on `process.pid` itself, which is
            # still strictly better than doing nothing.
            pass
    elif os.name == "nt":
        try:
            completed = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            if completed.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    process.kill()
    return False


def _run_adapter(target: Path) -> "subprocess.CompletedProcess[str]":
    """Run the vendored adapter in its own process group.

    A subprocess rather than an in-process import, for two reasons that both
    come from this host being a long-lived process the user is sitting in:
    a timeout that actually stops the work (the adapter's contradiction pass is
    O(n^2) and pure CPU, so a thread could not be interrupted), and a heap that
    is reclaimed when the audit ends rather than retained for the life of the
    session.

    `--` keeps argparse from reading a path that begins with a dash as an
    option, so `/rule-audit --help` reports that no such file exists rather than
    printing argparse's help.

    `Popen` rather than `subprocess.run(timeout=...)`: `run` kills only the
    process it started, and the slow half — `rule-audit` — is a grandchild.
    See `_kill_process_tree`.
    """
    process = subprocess.Popen(
        [sys.executable, str(_ADAPTER_PATH), "--", str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        # The adapter is pure stdlib and resolves its own rule-audit runtime;
        # inheriting cwd is deliberate so a relative path means what the user
        # typed it to mean.
        start_new_session=_NEW_SESSION,
    )
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as expired:
        reached_whole_tree = _kill_process_tree(process)
        # Drain after killing, or the pipes can keep this blocked on a child
        # that is already dead but whose buffers were never read.
        try:
            process.communicate(timeout=10)
        except (subprocess.TimeoutExpired, OSError, ValueError):  # pragma: no cover
            pass
        # Carried on the exception rather than returned, because the caller
        # reaches this through `except` and needs it to word its message.
        expired.rule_audit_tree_killed = reached_whole_tree  # type: ignore[attr-defined]
        raise
    return subprocess.CompletedProcess(
        process.args, process.returncode, stdout=stdout, stderr=stderr
    )


def _finish(message: str, status: int) -> str:
    """The single exit for every path: cap, append the status line, sanitize.

    Routing all six returns through here is what makes the three output
    guarantees unconditional. Capping only the report body, as an earlier
    version did, left the failure paths unbounded — and they are not small by
    construction: the adapter's stderr and the user's own path are both
    interpolated into them, and in the CLI everything printed is also retained
    in `_OUTPUT_HISTORY` and replayed on each redraw.

    The status line is appended *after* truncation, so it survives it. A report
    that lost its verdict to a length cap would be exactly the ambiguity the
    line exists to remove.
    """
    message = message.rstrip()
    if len(message) > MAX_OUTPUT_CHARS:
        message = message[:MAX_OUTPUT_CHARS] + (
            "\n\n[truncated at %d characters. Run `rule-audit --file` against the file "
            "for the full report.]" % MAX_OUTPUT_CHARS
        )
    return _sanitize("%s\n\n%s" % (message, _status_line(status)))


def audit(raw_args: str) -> str:
    """Handle `/rule-audit [path]`. Returns the text shown to the user.

    Never raises. A slash command that raises is handled differently by each
    surface and badly by all three: the CLI prints `Plugin command error: ...`
    with no report, the TUI reports the command as unrecognised, and the gateway
    falls through and sends the user's message to the model as a chat turn.
    """
    # Resolution runs before the subprocess call, so it needs its own guard or
    # an exception here escapes the handler entirely. `Path.home()` and
    # `expanduser()` both raise when no home directory can be determined, and
    # `soul_path()` is reached by the bare form before anything else.
    try:
        target = resolve_target(raw_args)
        used_default = not _clean_arg(raw_args)
        # Resolved once, inside the guard, so the failure branch below never
        # has to call `soul_path()` again outside it.
        default_note = (
            "\nNo path was given, so this looked for your SOUL.md at %s." % soul_path()
            if used_default
            else ""
        )
    except Exception as error:
        return _finish(
            "rule-audit: could not work out which file to audit (%s). "
            "Name the file explicitly.\n%s" % (error, _USAGE),
            1,
        )

    if not _ADAPTER_PATH.exists():
        return _finish(
            "rule-audit: the plugin is incomplete — %s is missing. Reinstall with "
            "`hermes plugins install hermes-labs-ai/rule-audit/integrations/hermes-agent "
            "--force`." % _ADAPTER_PATH,
            1,
        )

    try:
        completed = _run_adapter(target)
    except subprocess.TimeoutExpired as expired:
        # Say "was stopped" only when it was. See `_kill_process_tree`: both of
        # its mechanisms can fail, and claiming a kill that did not happen is
        # the same defect the process-tree kill exists to prevent.
        if getattr(expired, "rule_audit_tree_killed", True):
            outcome = "and was stopped, so your session stays responsive."
        else:
            outcome = (
                "and was killed, but the analyzer it had started could not be "
                "stopped with it and may still be running — check your process list."
            )
        return _finish(
            "rule-audit: the audit of %s did not finish within %ds %s Run "
            "`rule-audit --file` against it directly to audit it without a time limit."
            % (target, TIMEOUT_SECONDS, outcome),
            1,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # ValueError is not decoration, and it is doing two jobs. `subprocess.run`
        # raises it (not OSError) for an embedded NUL byte in the path, and
        # `UnicodeEncodeError` — raised when encoding an argv entry holding an
        # unpaired surrogate, which a JSON `\ud800` escape from a chat surface
        # can produce — is a *subclass* of ValueError, so it is caught here too.
        # Do not narrow this to OSError: both escape the handler, and on the
        # gateway an escaping exception becomes a billed model turn.
        return _finish("rule-audit: could not run the audit: %s" % error, 1)

    status = completed.returncode
    body = (completed.stdout or "").rstrip()
    problem = (completed.stderr or "").strip()

    if status not in _STATUS_NOTES or not body:
        # Status 1 is the adapter's own "could not run", and its reason is on
        # stderr. Anything else with no report is a failure this does not
        # recognise; say so rather than presenting emptiness as a clean result.
        detail = problem or "the audit produced no report."
        if detail.startswith(_ADAPTER_PREFIX):
            detail = detail[len(_ADAPTER_PREFIX):]
        return _finish("rule-audit: %s%s\n%s" % (detail, default_note, _USAGE), 1)

    if used_default:
        body = "Auditing your SOUL.md (%s) — no path was given.\n\n%s" % (target, body)

    return _finish(body, status)


def main(argv: Optional[List[str]] = None) -> int:
    """Direct `python hermes_audit.py [path]` run, for checking the plugin outside Hermes."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    sys.stdout.write(audit(" ".join(arguments)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
