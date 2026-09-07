# Changelog

All notable changes to `rule-audit` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Native Claude Code plugin under `integrations/claude-code/`, providing the `/rule-audit:audit <file>` slash command. It shells out to `rule-audit --file=PATH --format json`, renders a size-bounded report (5 findings per family, 160 characters per quoted span, true totals always stated), and re-raises the CLI's exit code unchanged. Adds no detection logic and no runtime dependency; `rule-audit` itself is a prerequisite the command resolves and version-checks (`>=0.3.1`), with `RULE_AUDIT_PYTHON` to point at a project virtualenv. Inputs above 64 KB are refused with a pointer to the CLI, since the contradiction pass is O(n²) in parsed rules and the library caps nothing itself. Prompt text and the audited path are rendered as inline code with a backtick fence longer than any run inside them, the analyzer's own descriptions have their inline Markdown and HTML delimiters escaped (several interpolate `rule.text[:80]` verbatim), and control characters are collapsed, so neither a file's contents nor its filename can restructure a report the model is asked to act on. Covered by 29 cases in `tests/test_claude_code_plugin.py`.

- Native Gemini CLI extension: `gemini-extension.json` at the repository root and `commands/rule-audit/audit.toml`, providing the same `/rule-audit:audit <file>` command, plus `integrations/gemini-cli/`. `audit_report.py` there is a byte-for-byte copy of the Claude Code adapter, pinned by test — neither host can import a shared module, since a Claude Code marketplace install materialises only the plugin subdirectory and `gemini extensions install` copies the extension root. The host-specific part is `gemini_audit.py`, which prints `[rule-audit status N]` and exits 0 rather than re-raising the CLI's code: a custom command's `!{…}` block appends `[Shell command '<resolved command>' exited with code N]` to the model's prompt on a non-zero exit, and `rule-audit` exits 2 for HIGH/CRITICAL, which is the common case. `{{args}}` is referenced only inside the shell block, where the host escapes it, so nothing the user types reaches the model as instructions. Covered by 27 cases in `tests/test_gemini_cli_extension.py`.

- Native Hermes Agent plugin under `integrations/hermes-agent/`, providing the in-session `/rule-audit [path]` slash command. Typed bare it audits your `SOUL.md` — the first section of the Hermes system prompt — resolved through the host's own `get_hermes_home()` rather than by assuming `~/.hermes`; the report always names the file it chose, because the TUI/desktop path does not bind the session's profile home (`tui_gateway/methods_tools.py::_dispatch_plugin`, unlike `_is_profile_skill_command` beside it). `audit_report.py` there is a third byte-for-byte copy of the Claude Code adapter, pinned by test, because `hermes plugins install` copies one directory out of the repository and this tree cannot reach a shared parent either. The host-specific part is `hermes_audit.py`. Unlike the other two hosts, a Hermes plugin command's return value goes **to the user and never into the model's context**, so the report needs no prompt-injection containment; it needs terminal containment instead, because `cli.py::_cprint` renders it through prompt_toolkit's ANSI parser — every character in Unicode category Cc or Cf but newline is stripped from the returned string, which covers the bidi overrides (U+202E and friends) that would otherwise let a hostile file render the report reversed in a terminal and on Telegram, Discord and Slack alike. The `rule-audit` exit code has nowhere to go in a handler that returns a string, so it is carried in-band as a final `[rule-audit status N]` line. The plugin registers no model tool (the tool schema sent on every API call is unchanged), no lifecycle hook, and declares no capabilities, so `hermes plugins enable` has nothing to consent to. The audit runs in a subprocess with a 60-second ceiling because Hermes dispatches slash commands synchronously. Covered by 46 cases in `tests/test_hermes_agent_plugin.py`.

- Native Codex plugin under `integrations/codex/`, plus a plugin-marketplace index at `.agents/plugins/marketplace.json` so the repository is itself an installable Codex marketplace (`codex plugin marketplace add hermes-labs-ai/rule-audit` then `codex plugin add rule-audit@rule-audit`). It contributes one skill, `$rule-audit:audit`, invoked deliberately by mention or from `/skills` — selecting it inserts the mention into the composer rather than sending, so nothing runs until you do. `audit_report.py` there is a fourth byte-for-byte copy of the Claude Code adapter, pinned by test, for the fourth confirmation of the same packaging constraint: `codex plugin add` copies one directory into `$CODEX_HOME/plugins/cache/`, so this tree cannot reach a shared parent either. The host-specific part is `codex_audit.py`. This host differs structurally from the other three: a Codex skill is *text*, injected into the turn as a user-role message (`core/src/session/turn.rs`, `core-skills/src/skill_instructions.rs`), and the model composes the shell call itself — so no template can carry a guarantee, and every guarantee is made by the wrapper process instead. It always exits 0 and states the status in-band as a final `[rule-audit status N]` line, because `rule-audit` exits 2 for HIGH/CRITICAL — the common case — and Codex renders a non-zero exit as a failed command to both the user and the model. It always fences its output, including on every failure path, because here the report lands in the model's context *and* the TUI transcript at once; the closing marker is defanged if the audited file restates it. It strips Unicode categories Cc and Cf for the same bidi-override reason as the Hermes Agent plugin. And it refuses more than one argument rather than joining words, so an unquoted path containing a space is reported back instead of silently auditing a different file. The plugin declares no MCP server, no app and no hook. Covered by 51 cases in `tests/test_codex_plugin.py`.

### Fixed
- The shared integration adapter rendered rule index `0` as an empty citation (`rule []` instead of `rule [0]`), because `str(value or "")` treats a falsy int as absent — and the first rule of every report is index 0, so every report was affected.

### Notes
- The Codex plugin ships **no** lifecycle hook, for the same measured reason as below — a fourth host, same conclusion. It is also honest about what it does cost: an installed, enabled skill has its name, description and path injected into every turn's developer instructions, inside a budget Codex caps at 2% of the model's context window. `[[skills.config]] name = "rule-audit:audit"` / `enabled = false` removes even that without uninstalling.
- The Hermes Agent plugin ships **no** `on_session_start` or `post_tool_call` hook, for the same measured reason as below. A session-start hook would fire on roughly two of every three real prompt files, ~44% of the time with nothing behind it, and hardest on the shortest files because of the coverage-gap floor.
- The Gemini CLI extension ships **no** `AfterTool` hook, for the same measured reason as below. The precision finding is a property of the analyzer's scoring, not of any host.
- The plugin deliberately ships **no** `PostToolUse` hook. On 588 real files matching this project's own prompt-file pattern, 72% of distinct files (86% of all files) score HIGH or CRITICAL, and ~44% of those verdicts contain zero contradictions — they are the 40/100 coverage-gap floor, which an empty file also trips. Narrower gates did not help: all 18 `meta_paradox` findings across the same corpus were false positives on the token "ignore"/"forget". An unsolicited edit-time interrupt would assert a precision `README.md` already disclaims. Rationale and measurements are recorded in `integrations/claude-code/README.md`.

## [0.3.1] — 2026-09-07

### Fixed
- The calibration corpus was not in the published 0.3.0 wheel: `rule_audit.calibration.DEFAULT_CASES_DIR` pointed at a repo-level `calibration/cases/` directory that no install has, so `python -m rule_audit.evidence --case negative_clean_prompt` exited 1 (`input.unknown-case`) from a PyPI install while passing from a source checkout. The cases now live in `rule_audit/calibration_cases/` as package data, and `tests/test_packaging.py` builds the distribution with `python -m build` and runs that command from the built wheel outside the checkout. Envelope `source` labels are unchanged.

## [0.3.0] — 2026-09-07

### Added
- `python -m rule_audit.evidence`: emit an audit as a Hermes Reliability Lab result envelope (tool, version, status, input hash, per-finding source spans, exit code, timestamp, Git commit) with the ordinary JSON report embedded verbatim. `--case ID` runs a labeled calibration case. No detection or scoring change.

### Fixed
- JSON and Markdown output were not byte-stable across processes: `shared_keywords` and shared-cluster lists were built from string sets, whose order follows the per-process hash seed. They now keep source order. Members are unchanged; only their order is fixed.

### Why 0.3.0, not 0.2.1
`rule_audit.evidence` is a new public module and CLI entry point (`python -m rule_audit.evidence`) — an additive, backward-compatible feature, not a bug fix. Per the same rule applied to 0.2.0, that's a MINOR bump, not a patch.

## [0.2.0] — 2026-09-04

Problem: a flagged contradiction or gap was hard to trust or act on — there
was no way to point at *where* in the prompt a rule came from, and no
checkable evidence that the detectors actually catch what they claim to
(versus five hand-picked demo samples).

### Added
- Source-span evidence: every `Rule` now carries `start`/`end` character offsets into the original prompt, surfaced in `AuditReport.to_dict()` for rules, contradictions, meta-paradoxes, and absoluteness issues — so a flagged finding points at exact source text instead of a paraphrase.
- `calibration/` — a bounded, hand-labeled corpus (11 cases) with an explicit ground truth per detector family, plus true-negative false-positive controls (opposing modality on unrelated topics, a clean prompt).
- `rule_audit.calibration` — runs the labeled corpus and emits a machine-readable benchmark result (`python -m rule_audit.calibration`); wired into CI as a regression gate (`tests/test_calibration.py`, `.github/workflows/ci.yml` `calibration` job).

### Evidence
- Calibration: **11/11 cases passed** (`pass_rate: 1.0`), `python -m rule_audit.calibration`, 2026-09-04.
- Full suite: **196 tests passed**.
- Boundary, unchanged by this release: detection is **lexical/regex-based, not semantic**, and **English only** — a `CRITICAL` label means "many absolute rules and contradictions by keyword/modality overlap," not a verified exploit. See README § Limitations.

### Why 0.2.0, not 0.1.4
This adds a new public module (`rule_audit.calibration`) and a new field on every emitted rule/finding (`start`/`end` spans) — both additive, backward-compatible surface changes a patch version shouldn't carry.

## [0.1.3] — 2026-09-02

### Added
- Added a native pre-commit hook that audits matched prompt files and preserves the documented CLI exit semantics across multi-file runs.

### Changed
- Documented the copy-paste pre-commit consumer configuration and filename matching boundary.

## [0.1.2] — 2026-08-04

### Fixed
- Made `--min-severity high` exclude medium-severity contradictions and edge-case scenarios from CLI output.
- Aligned `rule-audit --version` and the package `__version__` with the `0.1.2` project version.

### Changed
- Reworked the README and package metadata to describe the implemented detectors, limitations, and supported Python versions accurately.

## [0.1.1] — 2026-05-31

### Changed
- Updated public documentation, project links, citation metadata, and Zenodo metadata for the Hermes Labs repository.
- Removed internal launch-planning material from the public package repository.

## [0.1.0] — 2026-04-17

Initial public release. Pure Python static analyzer for AI system prompts. Zero LLM dependency.

### Added
- **Parser** (`rule_audit.parser`) — sentence splitter, modal-verb detection (7 modality classes), rule-type classification (8 types), absoluteness scoring (0.0–1.0 lexical scale), negation detection, condition extraction.
- **Analyzer** (`rule_audit.analyzer`) — five detector families:
  1. **Direct contradictions** — opposing modalities on shared topics (`MUST` vs `MUST_NOT` etc.).
  2. **Conditional contradictions** — unconditional rule vs conditional rule on the same cluster; boundary undefined.
  3. **Scope conflicts** — universal obligation vs restricted obligation on the same domain.
  4. **Absoluteness dilemmas** — two absolute rules on opposing sides (compliance vs safety).
  5. **Priority ambiguity** — conflicting rules with no stated resolution order.
  - Plus: completeness gap analysis over 8 safety-critical domains, meta-rule paradox detection, absoluteness stress-testing.
- **14 semantic keyword clusters** — `harm`, `privacy`, `identity`, `truth`, `assistance`, `refusal`, `instruction`, `content`, `safety`, `user`, `override`, `context`, `access`, `policy`.
- **Edge case generator** (`rule_audit.edge_cases`) — concrete attack scenarios for every contradiction, gap, paradox, and absoluteness issue; plus philosophical cases per rule (mechanical-vs-reasoned, contextual-harm, value-vs-constraint).
- **Report** (`rule_audit.report`) — `AuditReport` with `summary()`, `to_markdown()`, `to_dict()`, `to_json()`; composite `risk_score` (0–100) and `risk_label` (LOW / MEDIUM / HIGH / CRITICAL).
- **CLI** — `rule-audit [prompt] [--file] [--format markdown|json|summary] [--min-severity] [--verbose] [--log-level] [--output] [--version]`. Exit codes: `0` = LOW/MEDIUM, `2` = HIGH/CRITICAL, `1` = error.
- **Public API** — `audit(prompt)`, `audit_file(path)`, `AuditReport`, `Rule`.
- **Five real-world-style sample prompts** in `samples/` — `basic_assistant`, `code_assistant`, `content_moderator`, `customer_support`, `enterprise_rag`.
- **174 passing tests** — parser, analyzer, benchmark (finding-count regression gate), philosophical-case coverage.
- **CI matrix** — Python 3.9 / 3.10 / 3.11 / 3.12. Tests, coverage gate ≥ 70 %, mypy (warn-only), audit-samples smoke job.
- **Docs** — `README.md`, `SPEC.md` (full technical spec), `ROADMAP.md` (v0.2 / v0.3 / v1.0), `CLAUDE.md` (agent guidance), `AGENTS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CITATION.cff`, `llms.txt`.

### Design
- Pure Python standard library. Zero runtime dependencies.
- `Rule` objects are immutable dataclasses; parser produces, analyzer consumes.
- Deterministic: same input → same output. No sampling, no randomness, no model calls.
- O(n²) contradiction detection — fine for realistic prompts (n < 200 rules).
- Typical prompt: parse + analyze + edge-case generation in < 50 ms.

### Known limitations (tracked for v0.2)
- Parser is regex-based — misses paraphrases.
- Absoluteness scoring is lexical, not semantic.
- No subject-object distinction (rules about "users" vs rules about "the assistant" are conflated).
- Single-document only (no operator + user + tool-result multi-context).
- English only.

[Unreleased]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/hermes-labs-ai/rule-audit/releases/tag/v0.1.0
