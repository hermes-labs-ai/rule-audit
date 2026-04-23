# Changelog

All notable changes to `rule-audit` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/hermes-labs-ai/rule-audit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hermes-labs-ai/rule-audit/releases/tag/v0.1.0
