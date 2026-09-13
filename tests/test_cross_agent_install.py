"""The repository root is one Agent Plugin with one canonical skill.

  plugin.json                        portable Agent Plugins 1.0.0 manifest
                                     (read by Codex CLI)
  .agents/plugins/marketplace.json   Codex repo marketplace, source "./"
  .claude-plugin/plugin.json         Claude Code plugin manifest
  .claude-plugin/marketplace.json    Claude Code marketplace, source "./"
  gemini-extension.json              Gemini CLI extension manifest

Every manifest resolves to the repository root, and the root carries exactly
one `SKILL.md`: `skills/rule-audit/SKILL.md`. No host ships its own copy.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTABLE_MANIFEST = ROOT / "plugin.json"
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
GEMINI_MANIFEST = ROOT / "gemini-extension.json"
CANONICAL_SKILL = ROOT / "skills" / "rule-audit" / "SKILL.md"
SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
NAME_PATTERN = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
PORTABLE_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage",
    "repository", "license", "keywords", "extensions",
}
IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", ".pytest_cache"}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _entry(marketplace: Path) -> dict:
    data = _json(marketplace)
    (entry,) = [p for p in data["plugins"] if p["name"] == "rule-audit"]
    assert data["name"] == "rule-audit"
    return entry


def _skill_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("SKILL.md")
        if not IGNORED_DIRS.intersection(path.relative_to(ROOT).parts)
    )


def test_portable_manifest_follows_agent_plugins_schema():
    manifest = _json(PORTABLE_MANIFEST)
    assert manifest["$schema"] == SCHEMA_ID
    assert NAME_PATTERN.match(manifest["name"]) and len(manifest["name"]) <= 64
    assert set(manifest) <= PORTABLE_KEYS, set(manifest) - PORTABLE_KEYS
    assert set(manifest.get("author", {})) <= {"name", "email", "url"}


def test_every_manifest_names_the_same_plugin_and_version():
    portable = _json(PORTABLE_MANIFEST)
    assert portable["name"] == "rule-audit"
    for path in (CLAUDE_MANIFEST, GEMINI_MANIFEST):
        manifest = _json(path)
        assert manifest["name"] == portable["name"], path
        assert manifest["version"] == portable["version"], path


def test_both_marketplaces_resolve_to_the_repository_root():
    claude_source = _entry(CLAUDE_MARKETPLACE)["source"]
    assert (CLAUDE_MARKETPLACE.parents[1] / claude_source).resolve() == ROOT
    codex = _entry(CODEX_MARKETPLACE)
    assert codex["source"]["source"] == "local"
    assert (CODEX_MARKETPLACE.parents[2] / codex["source"]["path"]).resolve() == ROOT
    assert codex["policy"]["installation"] in {"AVAILABLE", "INSTALLED_BY_DEFAULT"}
    assert codex["policy"]["authentication"] in {"ON_INSTALL", "ON_USE"}


def test_every_manifest_resolves_the_one_canonical_skill():
    """All three hosts load `skills/<name>/SKILL.md` from the plugin root, and
    the plugin root of every manifest above is the repository root."""
    for manifest in (PORTABLE_MANIFEST, CLAUDE_MANIFEST, GEMINI_MANIFEST):
        assert manifest.is_file()
        assert "skills" not in _json(manifest), "%s must use the default skills/" % manifest
    assert _skill_files() == [CANONICAL_SKILL]
    text = CANONICAL_SKILL.read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1]
    assert re.search(r"^name: rule-audit$", frontmatter, re.MULTILINE)
    assert re.search(r"^description: \S", frontmatter, re.MULTILINE)


def test_no_host_ships_its_own_skill_surface():
    for extra in (
        ROOT / ".codex-plugin",
        ROOT / ".agents" / "skills",
        ROOT / ".gemini",
        ROOT / ".claude" / "skills",
        ROOT / "integrations" / "codex" / ".codex-plugin",
        ROOT / "integrations" / "codex" / "skills",
        ROOT / "integrations" / "claude-code" / ".claude-plugin",
    ):
        assert not extra.exists(), "%s would be a second, driftable plugin surface" % extra


def test_claude_manifest_adds_the_existing_command_by_path():
    commands = _json(CLAUDE_MANIFEST)["commands"]
    assert commands == ["./integrations/claude-code/commands/audit.md"]
    assert all((ROOT / path).is_file() for path in commands)


def test_the_skill_pins_the_uvx_fallback():
    text = CANONICAL_SKILL.read_text(encoding="utf-8")
    assert "uvx --from rule-audit==0.4.0" in text
    assert re.search(r"uvx --from rule-audit(?!==)", text) is None


def test_documented_gemini_install_pins_a_ref():
    """An unpinned GitHub install takes the latest release, which predates `skills/`."""
    pattern = re.compile(r"gemini extensions install https://github\.com/hermes-labs-ai/rule-audit[^\n`]*")
    for doc in (ROOT / "README.md", ROOT / "integrations" / "gemini-cli" / "README.md"):
        commands = pattern.findall(doc.read_text(encoding="utf-8"))
        assert commands, "%s no longer documents the Gemini install" % doc.name
        for command in commands:
            assert "--ref main" in command, "%s: %r must pass --ref main" % (doc.name, command)


def test_readme_documents_every_host_install():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for command in (
        "claude plugin marketplace add hermes-labs-ai/rule-audit",
        "claude plugin install rule-audit@rule-audit",
        "codex plugin marketplace add hermes-labs-ai/rule-audit",
        "codex plugin add rule-audit@rule-audit",
        "gemini extensions install https://github.com/hermes-labs-ai/rule-audit --ref main",
    ):
        assert command in text
