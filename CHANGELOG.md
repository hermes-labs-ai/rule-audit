# Changelog

All notable changes to `rule-audit` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[Unreleased]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/hermes-labs-ai/rule-audit/releases/tag/v0.1.0
