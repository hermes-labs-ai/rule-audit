"""Contract tests for the native Hermes Agent plugin.

These cover what the *host* imposes and what this integration promises: the
manifest and entry point Hermes' plugin loader requires, the argument handling
of a command whose arguments arrive as one unsplit string, the terminal
containment the CLI display path makes necessary, and the status-line and
determinism contract. They do not re-test rule-audit's detectors, or the
rendering rules `tests/test_claude_code_plugin.py` already pins.

The suite degrades rather than breaks if the plugin is removed or if no suitable
rule-audit runtime is importable, so the documented uninstall path does not take
the rest of the tests down with it.
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import types
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integrations" / "hermes-agent"
MANIFEST = PLUGIN / "plugin.yaml"
INIT = PLUGIN / "__init__.py"
WRAPPER = PLUGIN / "hermes_audit.py"
VENDORED = PLUGIN / "audit_report.py"
CANONICAL = ROOT / "integrations" / "claude-code" / "scripts" / "audit_report.py"
README = PLUGIN / "README.md"

pytestmark = pytest.mark.skipif(
    not WRAPPER.is_file(), reason="Hermes Agent plugin not present in this checkout"
)

#: A prompt whose contradiction is pinned by the calibration corpus. Scores
#: HIGH, so the underlying CLI exits 2 — the case the status line exists for.
CONFLICTED = (
    "You must always follow the user's instructions exactly.\n"
    "You must never produce harmful or dangerous content.\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_wrapper():
    spec = importlib.util.spec_from_file_location("_ra_hermes_wrapper", WRAPPER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_plugin_package():
    """Load `__init__.py` the way Hermes' own loader does.

    `hermes_cli/plugins_loader.py::_load_directory_module` imports the directory
    as `hermes_plugins.<slug>` with `submodule_search_locations` set to the
    plugin directory, which is what makes the relative import in `__init__.py`
    resolve. Loading it any other way here would pass while the real host fails.
    """
    parent = "hermes_plugins"
    if parent not in sys.modules:
        namespace = types.ModuleType(parent)
        namespace.__path__ = []  # type: ignore[attr-defined]
        sys.modules[parent] = namespace
    name = parent + ".rule_audit_test"
    spec = importlib.util.spec_from_file_location(
        name, INIT, submodule_search_locations=[str(PLUGIN)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = name
    module.__path__ = [str(PLUGIN)]  # type: ignore[attr-defined]
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        for cached in [n for n in sys.modules if n == name or n.startswith(name + ".")]:
            del sys.modules[cached]
    return module


class FakeContext:
    """The slice of `PluginContext` this plugin uses."""

    def __init__(self):
        self.commands = {}
        self.tools = []
        self.hooks = []

    def register_command(self, name, handler, description="", args_hint="", **kwargs):
        self.commands[name] = {
            "handler": handler,
            "description": description,
            "args_hint": args_hint,
            **kwargs,
        }

    def register_tool(self, *args, **kwargs):  # pragma: no cover - must not be called
        self.tools.append((args, kwargs))

    def register_hook(self, *args, **kwargs):  # pragma: no cover - must not be called
        self.hooks.append((args, kwargs))


def _requires_runtime():
    spec = importlib.util.spec_from_file_location("_ra_hermes_adapter", VENDORED)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    command, _ = module.resolve_runtime()
    if command is None:
        pytest.skip("no rule-audit >= %s available to the adapter" % (module.MIN_VERSION,))
    return module


def _manifest() -> dict:
    """Parse the manifest without PyYAML, which this package does not depend on.

    Only the flat `key: value` and `- item` forms the manifest actually uses.
    `test_manifest_matches_pyyaml` compares this against the real parser when
    PyYAML happens to be installed, which is what keeps it honest.
    """
    data: dict = {}
    key = None
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            assert key is not None
            data.setdefault(key, []).append(line[4:].strip())
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            # YAML types a bare integer as an int. Returning the string would
            # make `test_manifest_matches_pyyaml_when_it_is_available` fail,
            # which is the point of that test.
            data[key] = int(value) if value.isdigit() else value
    return data


def _flat(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# The reuse contract
# ---------------------------------------------------------------------------


def test_vendored_adapter_is_identical_to_the_claude_code_adapter():
    """The rendering exists once.

    `hermes plugins install` copies one directory out of the repository, so this
    tree cannot import a shared module from a common parent. A pinned copy is
    the only reuse the packaging permits — and it is only reuse while it stays
    byte-identical, which is what this asserts.
    """
    assert VENDORED.read_bytes() == CANONICAL.read_bytes()


def test_the_wrapper_does_not_reimplement_any_detection():
    """The host-specific file stays host-specific.

    If it ever imports rule_audit directly it has started deciding something
    about severity or findings, which is the shared adapter's job.
    """
    source = WRAPPER.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+rule_audit", source, re.M)


# ---------------------------------------------------------------------------
# What the host's plugin loader requires
# ---------------------------------------------------------------------------


def test_the_plugin_directory_has_what_the_loader_needs():
    """`plugin.yaml` + `__init__.py` exposing `register(ctx)`, per the loader."""
    assert MANIFEST.is_file()
    assert INIT.is_file()
    assert VENDORED.is_file()
    assert WRAPPER.is_file()


def test_manifest_declares_the_name_the_install_path_depends_on():
    data = _manifest()
    # The manifest name decides the install directory and the key every
    # documented enable/disable/remove command uses. The READMEs spell it.
    assert data["name"] == "rule-audit"
    assert data["version"]
    assert data["description"]


def test_manifest_requests_no_privileged_capability_and_adds_no_ambient_surface():
    """No capabilities, no tools, no hooks.

    Each is load-bearing and separately claimed in both READMEs: no capability
    means `hermes plugins enable` has nothing to consent to, no `provides_tools`
    means the tool schema sent on every API call is unchanged, and no
    `provides_hooks` means nothing runs unless the user types the command.
    """
    data = _manifest()
    assert "capabilities" not in data
    assert "provides_tools" not in data
    assert "provides_hooks" not in data


def test_manifest_declares_no_version_the_installer_would_reject():
    """`hermes plugins install` caps `manifest_version` lower than the loader does.

    On Hermes Agent 0.21.0 the loader accepts 2
    (`plugins_manifest.SUPPORTED_MANIFEST_VERSION`) but the installer accepts 1
    (`plugins_cmd._SUPPORTED_MANIFEST_VERSION`), so a manifest declaring 2 loads
    fine from a hand-copied directory and fails the documented install with
    "requires manifest_version 2, but this installer only supports up to 1".
    Absent means v1, which is supported forever, and nothing here needs v2.
    """
    data = _manifest()
    assert data.get("manifest_version", 1) == 1


def test_manifest_matches_pyyaml_when_it_is_available():
    """Keep the hand parser above honest against the parser the host uses."""
    yaml = pytest.importorskip("yaml")
    parsed = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert parsed == _manifest()


def test_register_adds_exactly_one_slash_command_and_nothing_else():
    plugin = _load_plugin_package()
    ctx = FakeContext()
    plugin.register(ctx)
    assert list(ctx.commands) == ["rule-audit"]
    assert ctx.tools == []
    assert ctx.hooks == []


def test_the_command_declares_an_optional_argument():
    """`[path]`, not `<path>`.

    The bare form audits SOUL.md, so the hint has to say the argument is
    optional in the host's own convention. Supplying a hint at all is also what
    sets `argument_mode="text"`, which is what makes Discord render a free-text
    argument field.
    """
    plugin = _load_plugin_package()
    ctx = FakeContext()
    plugin.register(ctx)
    assert ctx.commands["rule-audit"]["args_hint"] == "[path]"


def test_the_registered_handler_is_the_wrapper_entry_point():
    plugin = _load_plugin_package()
    ctx = FakeContext()
    plugin.register(ctx)
    handler = ctx.commands["rule-audit"]["handler"]
    assert handler.__name__ == "audit"
    # The host calls it with exactly one positional argument, the raw string.
    assert handler("") is not None


# ---------------------------------------------------------------------------
# Argument handling — the host hands over one unsplit string
# ---------------------------------------------------------------------------


def test_bare_invocation_targets_the_active_profiles_soul(monkeypatch, tmp_path):
    """No argument means SOUL.md, and it follows HERMES_HOME rather than ~."""
    wrapper = _load_wrapper()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert wrapper.resolve_target("") == tmp_path / "SOUL.md"
    assert wrapper.resolve_target("   ") == tmp_path / "SOUL.md"


def test_a_path_with_spaces_is_not_split_into_words(tmp_path):
    """The argument arrives unsplit and no shell is involved, so it is a path.

    Splitting on whitespace would break exactly the filenames that need no
    escaping anywhere else in this command.
    """
    wrapper = _load_wrapper()
    target = tmp_path / "my system prompt.md"
    assert wrapper.resolve_target(str(target)) == target


def test_one_layer_of_surrounding_quotes_is_removed(tmp_path):
    wrapper = _load_wrapper()
    target = tmp_path / "my system prompt.md"
    assert wrapper.resolve_target('"%s"' % target) == target
    assert wrapper.resolve_target("'%s'" % target) == target
    # Not a matching pair: left alone rather than mangled.
    assert wrapper.resolve_target('"%s' % target) == Path('"%s' % target)


def test_a_tilde_is_expanded_because_there_is_no_shell_here():
    wrapper = _load_wrapper()
    assert wrapper.resolve_target("~/x.md") == Path.home() / "x.md"


def test_hermes_home_falls_back_to_the_platform_default(monkeypatch):
    """The fallback exists so this module imports outside a Hermes process."""
    wrapper = _load_wrapper()
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert wrapper.hermes_home() == Path.home() / ".hermes"


# ---------------------------------------------------------------------------
# Terminal containment — this host's display path parses ANSI
# ---------------------------------------------------------------------------

#: Characters a hostile prompt file could use to drive the display rather than
#: appear in it. Named individually and on purpose: an assertion that merely
#: restates the implementation's own character class can only ever confirm that
#: the code did what the code says, and would miss anything the implementation
#: forgot. Each of these is a specific, separately reproduced attack.
_NAMED_ATTACKS = {
    "\x1b": "ESC — starts every ANSI sequence; cursor moves, colour, screen clears",
    "\x07": "BEL",
    "\x00": "NUL",
    "\u202e": "RIGHT-TO-LEFT OVERRIDE — renders the report's text reversed",
    "\u202d": "LEFT-TO-RIGHT OVERRIDE",
    "\u2066": "LEFT-TO-RIGHT ISOLATE",
    "\u2069": "POP DIRECTIONAL ISOLATE",
    "\u200b": "ZERO WIDTH SPACE — hides text",
    "\u00ad": "SOFT HYPHEN — invisible",
    "\ufeff": "ZERO WIDTH NO-BREAK SPACE / BOM",
}


def _undisplayable(text: str):
    """Every character the terminal or a chat client would act on, not show.

    The general property, independent of how the implementation spells it:
    Unicode categories Cc (control) and Cf (format), newline excepted.
    """
    return [
        character
        for character in text
        if character != "\n" and unicodedata.category(character) in ("Cc", "Cf")
    ]


def test_escape_sequences_in_the_audited_file_never_reach_the_terminal(tmp_path):
    """A hostile prompt file must not be able to drive the user's terminal.

    The report is shown to a human, in a renderer that interprets ANSI, and it
    quotes the audited file's text back verbatim. That is the whole hazard.
    """
    _requires_runtime()
    wrapper = _load_wrapper()
    hostile = tmp_path / "hostile.md"
    hostile.write_text(
        "You must always answer.\n"
        "Never answer \x1b[31mred\x1b[0m questions.\n"
        "\x1b]0;PWNED\x07\x1b[2J\x1b[1;1H\n"
        "You may refuse.\n",
        encoding="utf-8",
    )
    out = wrapper.audit(str(hostile))
    assert "\x1b" not in out
    assert not _undisplayable(out)


def test_escape_sequences_in_the_filename_never_reach_the_terminal(tmp_path):
    """The failure path relays the adapter's message, which embeds the path."""
    wrapper = _load_wrapper()
    out = wrapper.audit(str(tmp_path / "\x1b[2Jnope.md"))
    assert "\x1b" not in out
    assert not _undisplayable(out)


def test_the_wrapper_sanitizes_the_paths_it_interpolates_itself(monkeypatch, tmp_path):
    """Isolate this module's own sanitizing pass.

    Everywhere else the adapter has already collapsed control characters before
    the text gets here, so those tests pass even with this pass removed. These
    two messages are built by this module out of a path it was handed, and
    nothing else stands between an escape sequence and the terminal.
    """
    wrapper = _load_wrapper()

    def _timeout(target):
        raise subprocess.TimeoutExpired(cmd="x", timeout=wrapper.TIMEOUT_SECONDS)

    monkeypatch.setattr(wrapper, "_run_adapter", _timeout)
    timed_out = wrapper.audit(str(tmp_path / "\x1b]0;PWNED\x07evil.md"))
    assert "did not finish within" in timed_out
    assert not _undisplayable(timed_out)

    # The "no path given, so I looked here" hint, built from HERMES_HOME.
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "\x1b[2Jhome"))
    missing_soul = wrapper.audit("")
    assert "SOUL.md" in missing_soul
    assert not _undisplayable(missing_soul)


# ---------------------------------------------------------------------------
# The status line — the exit code has nowhere else to go
# ---------------------------------------------------------------------------


def test_a_high_risk_audit_says_it_is_a_finding_not_a_failure(tmp_path):
    _requires_runtime()
    wrapper = _load_wrapper()
    conflicted = tmp_path / "conflicted.md"
    conflicted.write_text(CONFLICTED, encoding="utf-8")
    out = wrapper.audit(str(conflicted))
    assert "[rule-audit status 2]" in out
    assert "not a command failure" in out


def test_a_failure_is_status_1_and_says_why_and_shows_usage(tmp_path):
    wrapper = _load_wrapper()
    out = wrapper.audit(str(tmp_path / "absent.md"))
    assert "[rule-audit status 1]" in out
    assert "file not found" in out
    assert "/rule-audit [path]" in out


def test_the_status_line_is_the_last_line(tmp_path):
    """A truncated or split chat message still ends with the verdict."""
    _requires_runtime()
    wrapper = _load_wrapper()
    conflicted = tmp_path / "conflicted.md"
    conflicted.write_text(CONFLICTED, encoding="utf-8")
    assert wrapper.audit(str(conflicted)).strip().splitlines()[-1].startswith(
        "[rule-audit status "
    )


def test_a_relayed_adapter_message_is_not_double_prefixed(tmp_path):
    """`rule-audit: rule-audit: file not found` is what this prevents."""
    wrapper = _load_wrapper()
    out = wrapper.audit(str(tmp_path / "absent.md"))
    assert "rule-audit: rule-audit:" not in out


def test_the_bare_form_names_the_file_it_chose(monkeypatch, tmp_path):
    """The user did not type a path, so the report has to say what it audited."""
    _requires_runtime()
    wrapper = _load_wrapper()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "SOUL.md").write_text(CONFLICTED, encoding="utf-8")
    out = wrapper.audit("")
    assert str(tmp_path / "SOUL.md") in out


def test_a_missing_soul_says_where_it_looked(monkeypatch, tmp_path):
    wrapper = _load_wrapper()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    out = wrapper.audit("")
    assert str(tmp_path / "SOUL.md") in out
    assert "[rule-audit status 1]" in out


# ---------------------------------------------------------------------------
# Never raise, never block forever, never flood
# ---------------------------------------------------------------------------


def test_the_handler_returns_a_string_rather_than_raising(tmp_path, monkeypatch):
    """A raising handler surfaces as `Plugin command error:` with no report.

    Every failure mode must come back as text the user can act on instead.
    """
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper, "_ADAPTER_PATH", tmp_path / "gone.py")
    out = wrapper.audit("whatever.md")
    assert isinstance(out, str)
    assert "incomplete" in out
    assert "[rule-audit status 1]" in out


def test_a_timeout_is_reported_rather_than_wedging_the_session(monkeypatch):
    """The CLI dispatches slash commands synchronously, so this blocks the REPL.

    `resolve_plugin_command_result`'s 30s guard covers async handlers only.
    """
    wrapper = _load_wrapper()

    def _boom(target):
        raise subprocess.TimeoutExpired(cmd="x", timeout=wrapper.TIMEOUT_SECONDS)

    monkeypatch.setattr(wrapper, "_run_adapter", _boom)
    out = wrapper.audit("x.md")
    assert "did not finish within" in out
    assert "[rule-audit status 1]" in out


def test_the_timeout_bounds_the_session_not_just_the_audit():
    """Pinned so it cannot be raised past the adapter's own 120s inner limit.

    The point of this number is that the user gets their prompt back; raising it
    to or beyond the adapter's limit would silently give that up.
    """
    wrapper = _load_wrapper()
    assert wrapper.TIMEOUT_SECONDS == 60
    assert wrapper.TIMEOUT_SECONDS < 120


# ---------------------------------------------------------------------------
# The timeout must kill the analyzer, not just the adapter — same bug and fix
# as the Codex lane's `codex_audit.py::_kill_process_tree`, found there first
# by `hermes-gate review`, then confirmed here on the identical shape.
# ---------------------------------------------------------------------------


def test_the_timeout_message_does_not_claim_a_kill_that_failed(monkeypatch):
    """Both kill mechanisms can fail, and on Windows there is no process group.

    "was stopped" for something still running is the same defect the
    process-tree kill exists to prevent, just in a smaller place — so the
    message is worded from what actually happened, not from what was
    attempted.
    """
    wrapper = _load_wrapper()

    class _Zombie:
        args = ["fake"]
        pid = -1

        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(self.args, timeout)

        def kill(self):
            pass

    monkeypatch.setattr(wrapper.subprocess, "Popen", lambda argv, **kwargs: _Zombie())
    monkeypatch.setattr(wrapper, "_kill_process_tree", lambda process: False)
    out = wrapper.audit("x.md")
    assert "may still be running" in out
    assert "was stopped" not in out
    assert "[rule-audit status 1]" in out


def test_the_timeout_message_does_claim_a_kill_that_worked(monkeypatch):
    """The other half of the pair, so the wording cannot be pinned to one branch."""
    wrapper = _load_wrapper()

    class _Zombie:
        args = ["fake"]
        pid = -1

        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(self.args, timeout)

        def kill(self):
            pass

    monkeypatch.setattr(wrapper.subprocess, "Popen", lambda argv, **kwargs: _Zombie())
    monkeypatch.setattr(wrapper, "_kill_process_tree", lambda process: True)
    out = wrapper.audit("x.md")
    assert "was stopped" in out
    assert "may still be running" not in out
    assert "[rule-audit status 1]" in out


def test_kill_process_tree_reports_whether_it_reached_the_tree(monkeypatch):
    """The return value is the message's only source of truth."""
    wrapper = _load_wrapper()
    killed = []

    class _Fake:
        pid = 4242

        def kill(self):
            killed.append("direct")

    if wrapper._NEW_SESSION:
        calls = []
        monkeypatch.setattr(
            wrapper.os, "killpg", lambda pgid, sig: calls.append(pgid) or None
        )
        assert wrapper._kill_process_tree(_Fake()) is True
        assert killed == []
        # Signalled by the known PGID directly, not looked up through
        # `getpgid`. That lookup is the race `hermes-gate review` found: it
        # fails exactly when the adapter has already exited but its
        # grandchild is still alive holding the pipes open, which is the one
        # case this function has to reach.
        assert calls == [4242]

        def _boom(pgid, sig):
            raise OSError("no such process group")

        monkeypatch.setattr(wrapper.os, "killpg", _boom)
        assert wrapper._kill_process_tree(_Fake()) is False
        assert killed == ["direct"]


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="process groups are POSIX-only")
def test_kill_process_tree_never_looks_up_the_process_group(monkeypatch):
    """The exact regression `hermes-gate review` found: `getpgid(process.pid)`
    races against the adapter exiting before its grandchild does, at which
    point the lookup raises and the live grandchild is never signalled. The
    PGID equals the PID by construction (`start_new_session=True`), so nothing
    should ever call `getpgid` here.
    """
    wrapper = _load_wrapper()

    class _Fake:
        pid = 4242

        def kill(self):
            pass

    def _must_not_be_called(pid):
        raise AssertionError("getpgid was called — the lookup race is back")

    monkeypatch.setattr(wrapper.os, "getpgid", _must_not_be_called)
    monkeypatch.setattr(wrapper.os, "killpg", lambda pgid, sig: None)
    assert wrapper._NEW_SESSION, "expected POSIX to take the process-group branch"
    assert wrapper._kill_process_tree(_Fake()) is True


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX-only")
def test_the_timeout_kills_the_analyzer_and_not_just_the_adapter(tmp_path, monkeypatch):
    """The slow half is the grandchild, so killing the child proves nothing.

    This module starts `audit_report.py`, which starts `rule-audit`. The
    O(n^2), CPU-bound work is in the grandchild. `subprocess.run(timeout=...)`
    kills only its direct child, so the analyzer would keep running — while
    this reports that the audit "was stopped". That is a false statement and a
    runaway process at once.

    The fake adapter below stands in for the real one: it spawns a long-lived
    grandchild that writes its pid where the test can see it, then hangs. If
    the kill does not reach the whole process group, that pid is still alive
    afterwards.
    """
    import time as _time

    wrapper = _load_wrapper()
    pidfile = tmp_path / "grandchild.pid"
    fake_adapter = tmp_path / "fake_adapter.py"
    fake_adapter.write_text(
        "import subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])\n"
        "open(%r, 'w').write(str(child.pid))\n"
        "time.sleep(600)\n" % str(pidfile),
        encoding="utf-8",
    )
    monkeypatch.setattr(wrapper, "_ADAPTER_PATH", fake_adapter)
    monkeypatch.setattr(wrapper, "TIMEOUT_SECONDS", 3)

    out = wrapper.audit(str(tmp_path / "irrelevant.md"))
    assert "did not finish within 3s" in out
    assert "was stopped" in out

    assert pidfile.is_file(), "the fake adapter never started its grandchild"
    grandchild = int(pidfile.read_text())
    deadline = _time.time() + 10
    while _time.time() < deadline:
        # `kill -0` probes for existence without signalling.
        if subprocess.run(["kill", "-0", str(grandchild)], capture_output=True).returncode != 0:
            break
        _time.sleep(0.2)
    else:
        subprocess.run(["kill", "-9", str(grandchild)], capture_output=True)
        raise AssertionError(
            "the analyzer subprocess %d survived the timeout — the kill reached "
            "the adapter but not its process group" % grandchild
        )


def test_output_is_capped(monkeypatch):
    """Both the flood size and the expected notice are literals.

    An earlier version sized the input as `MAX_OUTPUT_CHARS + n` and built the
    expected substring from the same constant, which made the assertion true
    for any cap — raising the cap did not fail it.
    """
    wrapper = _load_wrapper()
    assert wrapper.MAX_OUTPUT_CHARS == 12_000
    flood = types.SimpleNamespace(returncode=0, stdout="x" * 17_000, stderr="")
    monkeypatch.setattr(wrapper, "_run_adapter", lambda target: flood)
    out = wrapper.audit("x.md")
    assert "truncated at 12000 characters" in out
    assert len(out) < 12_500
    # Truncation must not cost the verdict.
    assert "[rule-audit status 0]" in out


def test_an_unrecognised_status_is_not_presented_as_a_clean_result(monkeypatch):
    """An empty report with a surprising code must not read as `no findings`."""
    wrapper = _load_wrapper()
    odd = types.SimpleNamespace(returncode=97, stdout="", stderr="something broke")
    monkeypatch.setattr(wrapper, "_run_adapter", lambda target: odd)
    out = wrapper.audit("x.md")
    assert "something broke" in out
    assert "[rule-audit status 1]" in out


def test_an_argument_beginning_with_a_dash_is_treated_as_a_path(tmp_path):
    """`--` guards argparse, so `/rule-audit --help` cannot print argparse help."""
    _requires_runtime()
    wrapper = _load_wrapper()
    out = wrapper.audit("--help")
    assert "file not found" in out
    assert "usage: audit_report.py" not in out.lower()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_two_runs_over_unchanged_input_are_byte_identical(tmp_path):
    """`generated_at` is never read, in the adapter or here."""
    _requires_runtime()
    wrapper = _load_wrapper()
    conflicted = tmp_path / "conflicted.md"
    conflicted.write_text(CONFLICTED, encoding="utf-8")
    assert wrapper.audit(str(conflicted)) == wrapper.audit(str(conflicted))


# ---------------------------------------------------------------------------
# Documentation the user needs to actually run this
# ---------------------------------------------------------------------------


def test_the_readme_documents_install_use_disable_and_uninstall():
    text = _flat(README.read_text(encoding="utf-8"))
    assert "hermes plugins install hermes-labs-ai/rule-audit/integrations/hermes-agent" in text
    assert "hermes plugins enable rule-audit" in text
    assert "hermes plugins disable rule-audit" in text
    assert "hermes plugins remove rule-audit" in text
    assert "/rule-audit" in text


def test_the_readme_states_the_calibration_caveat_that_rules_out_a_hook():
    """The measurement is why this is a command and not `on_session_start`.

    If it stops being stated, the next person reading this tree has no record of
    why the ambient surface was declined.
    """
    text = _flat(README.read_text(encoding="utf-8"))
    assert "40" in text and "coverage-gap" in text.lower()
    assert "on_session_start" in text


def test_the_readme_names_the_surface_where_the_profile_claim_does_not_hold():
    """`get_hermes_home()` does not mean the session's profile on every surface.

    `tui_gateway/methods_tools.py::_dispatch_plugin` invokes a plugin command
    without binding the session's `profile_home`, unlike `_is_profile_skill_command`
    beside it. A user running profiles has to know that, and it is the kind of
    caveat that quietly gets edited out.
    """
    text = _flat(README.read_text(encoding="utf-8"))
    assert "_dispatch_plugin" in text
    assert "profile" in text.lower()


def test_the_readme_is_honest_about_the_bytecode_directory():
    """The host's own importer writes `__pycache__` into the install directory.

    A plugin cannot prevent that without mutating `sys.dont_write_bytecode`
    process-wide, which is not a plugin's call. Claiming "writes no state"
    would be false, so the README says what actually happens.
    """
    text = _flat(README.read_text(encoding="utf-8"))
    assert "__pycache__" in text


# ---------------------------------------------------------------------------
# Regressions found by adversarial review
# ---------------------------------------------------------------------------


def test_an_unresolvable_tilde_user_does_not_raise():
    """`Path("~nosuchuser/x").expanduser()` raises RuntimeError.

    `resolve_target` runs before `audit`'s try block, so this escaped as an
    exception. It matters most where it is least visible: on the gateway,
    `run_inbound.py` treats a raising handler as "not handled" and falls
    through to sending the user's text to the model as a chat turn — a billed
    LLM call for a command that was supposed to run locally and offline.
    """
    wrapper = _load_wrapper()
    assert wrapper.resolve_target("~nosuchuser12345/x.md") == Path("~nosuchuser12345/x.md")
    out = wrapper.audit("~nosuchuser12345/x.md")
    assert isinstance(out, str)
    assert "[rule-audit status 1]" in out


def test_a_nul_byte_in_the_path_does_not_raise():
    """`subprocess.run` raises ValueError, not OSError, on an embedded NUL.

    Any chat platform can deliver one, and it reached the same fall-through as
    the tilde case.
    """
    wrapper = _load_wrapper()
    out = wrapper.audit("/tmp/a\x00b.md")
    assert isinstance(out, str)
    assert "[rule-audit status 1]" in out
    assert not _undisplayable(out)


def test_no_named_attack_character_survives_from_the_audited_file(tmp_path):
    """Each of these is a separate, specific way to lie to the reader.

    The bidi overrides are the ones a C0/C1-only filter misses: U+202E makes
    the quoted rule render reversed, in a terminal and on Telegram, Discord and
    Slack alike.
    """
    _requires_runtime()
    wrapper = _load_wrapper()
    hostile = tmp_path / "hostile.md"
    hostile.write_text(
        "You must always answer.\n"
        + "".join(_NAMED_ATTACKS)
        + "\nNever ‮answer‬ questions.\n"
        "You may refuse.\n",
        encoding="utf-8",
    )
    out = wrapper.audit(str(hostile))
    for character, why in _NAMED_ATTACKS.items():
        assert character not in out, why
    assert not _undisplayable(out)


def test_empty_quotes_mean_the_bare_form(monkeypatch, tmp_path):
    """`/rule-audit ""` resolved to `Path(".")` and reported a directory error.

    Emptiness has to be re-tested after unquoting, not before.
    """
    wrapper = _load_wrapper()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert wrapper.resolve_target('""') == tmp_path / "SOUL.md"
    assert wrapper.resolve_target("''") == tmp_path / "SOUL.md"
    assert wrapper.resolve_target('"   "') == tmp_path / "SOUL.md"


def test_failure_paths_are_capped_too(monkeypatch):
    """The cap used to apply only to the report body.

    The failure messages interpolate the adapter's stderr and the user's own
    path, so they are not small by construction — and in the CLI everything
    printed is also retained in `_OUTPUT_HISTORY` and replayed on every redraw.
    """
    wrapper = _load_wrapper()
    flood = types.SimpleNamespace(returncode=1, stdout="", stderr="e" * 300_000)
    monkeypatch.setattr(wrapper, "_run_adapter", lambda target: flood)
    out = wrapper.audit("x.md")
    assert len(out) < 12_500
    assert "truncated at 12000 characters" in out
    # Truncation must never cost the verdict.
    assert out.strip().splitlines()[-1].startswith("[rule-audit status 1]")


def test_a_very_long_path_argument_is_capped(monkeypatch, tmp_path):
    wrapper = _load_wrapper()
    monkeypatch.setattr(
        wrapper, "_run_adapter",
        lambda target: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="x", timeout=wrapper.TIMEOUT_SECONDS)
        ),
    )
    out = wrapper.audit(str(tmp_path / ("a" * 20_000)))
    assert len(out) < 12_500
    assert out.strip().splitlines()[-1].startswith("[rule-audit status 1]")


def test_the_host_accessor_is_preferred_over_the_environment(monkeypatch, tmp_path):
    """`get_hermes_home()` wins over HERMES_HOME — the profile claim depends on it.

    Under pytest `hermes_constants` is not importable, so every other test in
    this file exercises the fallback and the host-accessor branch could be
    deleted outright without failing any of them. This stubs the module the way
    the host would provide it and pins the ordering: the accessor already
    resolves the context-local override, then the env var, then the platform
    default, so consulting the environment first here would audit the wrong
    profile's SOUL.md.
    """
    wrapper = _load_wrapper()
    chosen = tmp_path / "profile-from-accessor"
    stub = types.ModuleType("hermes_constants")
    stub.get_hermes_home = lambda: chosen  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_constants", stub)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "ignored-env-home"))
    assert wrapper.hermes_home() == chosen
    assert wrapper.soul_path() == chosen / "SOUL.md"


def test_a_broken_host_accessor_falls_back_rather_than_raising(monkeypatch, tmp_path):
    wrapper = _load_wrapper()
    stub = types.ModuleType("hermes_constants")

    def _boom():
        raise RuntimeError("no profile")

    stub.get_hermes_home = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_constants", stub)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert wrapper.hermes_home() == tmp_path


def test_an_unavailable_home_directory_does_not_raise(monkeypatch):
    """`Path.home()` raises when no home can be determined — same class as `expanduser()`.

    The bare form reaches it through `soul_path()` *before* `audit()` enters the
    subprocess try block, so it escaped the handler exactly as the tilde case
    did. Fixing one call site and not its sibling would have left the
    "never raises" guarantee false for the command's default invocation.
    """
    wrapper = _load_wrapper()
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setitem(sys.modules, "hermes_constants", None)

    def _no_home():
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "home", staticmethod(_no_home))
    # Neither the accessor nor the environment nor the platform default works.
    assert wrapper.hermes_home() == Path(".hermes")
    out = wrapper.audit("")
    assert isinstance(out, str)
    assert "[rule-audit status 1]" in out


def test_the_handler_survives_any_resolution_failure(monkeypatch):
    """The guard is on the resolution step, not on one known exception."""
    wrapper = _load_wrapper()

    def _boom(raw_args):
        raise ValueError("resolution exploded")

    monkeypatch.setattr(wrapper, "resolve_target", _boom)
    out = wrapper.audit("")
    assert "could not work out which file to audit" in out
    assert "resolution exploded" in out
    assert "[rule-audit status 1]" in out


def test_an_unpaired_surrogate_in_the_path_does_not_raise():
    """`UnicodeEncodeError` from encoding argv is a `ValueError` subclass.

    A JSON `\\ud800` escape from a chat surface produces one. It is already
    caught, and this pins that: narrowing the except tuple to `OSError` — which
    reads like a tidy-up — would let it escape the handler.
    """
    wrapper = _load_wrapper()
    assert issubclass(UnicodeEncodeError, ValueError)
    out = wrapper.audit("/tmp/\ud800.md")
    assert isinstance(out, str)
    assert "[rule-audit status 1]" in out
