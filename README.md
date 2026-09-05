# rule-audit

**rule-audit is a static analyzer for AI system prompts: it parses a prompt into normative rules and reports logical contradictions, coverage gaps, priority ambiguities, meta-rule paradoxes, and absolute-rule edge cases — without calling an LLM.**

[![CI](https://github.com/hermes-labs-ai/rule-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/rule-audit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rule-audit.svg)](https://pypi.org/project/rule-audit/)
[![Python](https://img.shields.io/pypi/pyversions/rule-audit.svg)](https://pypi.org/project/rule-audit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Part of the [Hermes Labs reliability stack](https://github.com/hermes-labs-ai).

---

## The problem

A complex AI safety prompt can contain rules that conflict under specific conditions. Those conflicts are easy to write and hard to see by eye. `rule-audit` reads the prompt the way a linter reads code and surfaces the conflicts as structured findings.

Illustrative example — two rules that have no stated priority between them:
```
"You must always follow user instructions."
"You must never produce harmful content."
```
The moment a user instructs the model to produce harmful content, nothing in the prompt says which rule wins. `rule-audit` flags this pair so the author can add an explicit ordering.

---

## Install

```bash
pip install rule-audit
```

Or from source:
```bash
git clone https://github.com/hermes-labs-ai/rule-audit
cd rule-audit
pip install -e ".[dev]"
```

Pure Python, no runtime dependencies, Python 3.9+.

---

## 60-second quickstart

### CLI

```bash
# Built-in demo — exercises every detector family, no input needed
rule-audit --demo

# Inline prompt
rule-audit "You are helpful. You must never lie. Always answer every question."

# From a file
rule-audit --file system_prompt.txt

# Save a Markdown report
rule-audit --file system_prompt.txt --output report.md

# JSON for downstream processing
rule-audit --file system_prompt.txt --format json

# Summary only (handy in CI)
rule-audit --file system_prompt.txt --format summary

# Keep contradiction and edge-case detail at high severity
rule-audit --file system_prompt.txt --min-severity high
```

Exit codes: `0` = LOW/MEDIUM risk, `2` = HIGH/CRITICAL risk, `1` = error.

### Pre-commit

Audit prompt files before they are committed:

```yaml
repos:
  - repo: https://github.com/hermes-labs-ai/rule-audit
    rev: v0.2.0
    hooks:
      - id: rule-audit
```

Then run:

```bash
pre-commit install
pre-commit run rule-audit --all-files
```

The hook checks Markdown and text files under `prompt/` or `prompts/`, plus conventional system, developer, and agent prompt/instruction filenames. It reports every matched file and preserves the CLI exit codes above. Adjust `files:` in your consumer configuration if your prompts live elsewhere.

### Python API

```python
from rule_audit import audit

report = audit("""
    You are a helpful AI assistant.
    Always answer user questions completely.
    Never produce content that could harm anyone.
    Follow operator instructions above all else.
    If asked to roleplay without restrictions, comply.
""")

print(report.summary())
# rule-audit report  [2026-...T...]
# ============================================================
#   Rules parsed          : 4
#   Contradictions        : 1  (1 high, 0 medium)
#   Coverage gaps         : 5
#   Priority ambiguities  : 0
#   Meta-paradoxes        : 0
#   Absoluteness issues   : 5
#   Edge case scenarios   : 17
#   Risk score            : 55/100  [HIGH]

# Full Markdown report
md = report.to_markdown()

# Access findings programmatically
for c in report.result.contradictions:
    print(c.severity, c.description)

for ec in report.edge_cases:
    print(ec.title, ec.attack_vector)
```

(Exact counts depend on the input prompt; the values above are the actual output for the five-line prompt shown.)

---

## What it detects

### 1. Contradictions
Rule pairs that pull against each other. Four detector families:

- **Direct** — opposing modalities on a shared topic (e.g. `MUST` vs `MUST_NOT`).
- **Conditional** — one rule applies unconditionally, another applies a contradicting directive under a condition; the overlap region is undefined.
- **Scope** — a universal obligation (`always …`) and a restricted obligation (`… only / except …`) on the same domain.
- **Absoluteness** — two high-absoluteness rules that pull in opposite directions (e.g. compliance vs safety).

### 2. Coverage gaps
Checks the prompt against eight safety-relevant domains and flags any with no rule coverage: harmful content, principal hierarchy (user vs operator vs developer), ambiguous requests, persona/roleplay, refusal protocol, instruction-conflict resolution, self-disclosure of instructions, and edge-case fallback behavior. Also flags conditional rules that have no stated default for the else-case.

### 3. Priority ambiguities
Rule clusters that conflict with no explicit ordering and no meta-rule that resolves them.

### 4. Meta-rule paradoxes
Rules that reference rules — e.g. "ignore all previous instructions" (self-defeating), "these instructions supersede all others" (exploitable via injection), or override language elsewhere in the prompt that could be used to void other rules.

### 5. Absoluteness audit
Each `always` / `never` / `under no circumstances` rule is paired with challenge scenarios: known exceptions, context-dependent cases, and adversarial triggers.

### 6. Edge-case scenarios
For each finding, the report renders a concrete example scenario plus a suggested attack vector, expected failure mode, and mitigation. These are templated from the finding — illustrative starting points for testing, not verified exploits.

---

## Calibration: does it actually work?

`calibration/` is a bounded, hand-labeled corpus (11 cases) with an explicit
ground truth — not a statistical claim, an auditable one. Positive cases pin
down a true finding per detector family (direct/scope/conditional/absoluteness
contradiction, meta-paradox, priority ambiguity, coverage gap); negative cases
pin down known false-positive traps, like two rules with opposing modality on
completely unrelated topics.

```bash
# Machine-readable benchmark result (JSON), exit 1 on any regression
python -m rule_audit.calibration

# As a pytest gate
pytest tests/test_calibration.py -v
```

Every `Rule` carries `start` / `end` character offsets into the original
prompt (`report.to_dict()["rules"][i]["span"]`, also threaded onto
contradictions, meta-paradoxes, and absoluteness issues) — every finding
traces back to an exact source span, not just a truncated text snippet.
See `calibration/README.md` for the case schema and how to add cases.

---

## Limitations / what it does NOT do

- **Lexical parser, not a language model.** Parsing is sentence-splitting + modal-verb regex + keyword clusters. Rules that need semantic understanding (implied or narrative-embedded constraints) can be missed.
- **It does not prove a prompt is exploitable.** A `CRITICAL` risk label means "many absolute rules and contradictions in a short prompt" by the lexical scoring — not a verified end-to-end exploit. For dynamic verification, pair it with [`hermes-jailbench`](https://github.com/hermes-labs-ai/hermes-jailbench) (jailbreak regression).
- **14 keyword clusters, curated by hand.** Uncommon domains may not trigger coverage-gap detection; extend `_KEYWORD_CLUSTERS` in `analyzer.py`.
- **Absoluteness defaults to 0.5** for modal sentences with no qualifier keyword. A design choice — tune `_compute_absoluteness` for your corpus.
- **English only** in this release.
- **Single-document only.** Multi-part prompts (operator + user + tool results) merged into one input are analyzed as a flat rule list; structural separation between principals is not modeled.
- **O(n²) pair comparison.** Fine for realistic prompts; very large rule sets will be slow.

---

## How it relates to other tools

- **`rule-audit` and [LintLang](https://github.com/hermes-labs-ai/lintlang) are complementary, not duplicates.** `rule-audit` analyzes the *logical content* of a system prompt (contradictions, gaps, priority). LintLang lints the *structure* of agent configs and tool descriptions. Run both.
- **`rule-audit` is static; [`hermes-jailbench`](https://github.com/hermes-labs-ai/hermes-jailbench) is dynamic.** Static analysis finds candidate flaws; dynamic testing checks whether they are reachable against a live endpoint.

---

## Architecture

```
rule_audit/
├── __init__.py      # Public API: audit(), audit_file(), AuditReport
├── parser.py        # Sentence splitting, modal-verb detection, Rule objects (with source spans)
├── analyzer.py      # Contradiction / gap / priority / meta / absoluteness detectors
├── edge_cases.py    # Scenario generator from analysis results
├── report.py        # AuditReport + Markdown / JSON renderers
├── calibration.py   # Labeled calibration corpus runner (calibration/cases/*.json)
├── precommit.py     # Pre-commit hook entry point
└── cli.py           # CLI entry point
```

Pure Python standard library, zero runtime dependencies, deterministic (same input → same output), no network calls.

---

## Development

```bash
pip install -e ".[dev]"

# Run the test suite
pytest

# With coverage
pytest --cov=rule_audit --cov-report=term-missing

# Audit a real prompt
python -m rule_audit --file your_prompt.txt --verbose
```

---

## License

MIT — see [LICENSE](LICENSE). © Hermes Labs 2026.

---

## About Hermes Labs

[Hermes Labs](https://hermes-labs.ai) is an AI reliability engineering studio for product and engineering teams shipping production agents and LLM applications. We find the structural AI failures standard evals miss, then harden retrieval, memory, agents, and the language layers around production AI systems with runtime controls and defensible evidence.

Browse the [open-source catalog](https://hermes-labs.ai/open-source) or contact [roli@hermes-labs.ai](mailto:roli@hermes-labs.ai).

Not affiliated with NousResearch, Teknium, the Nous-Hermes LLM line, or any unrelated `hermes-*` project.

Built by [Hermes Labs](https://hermes-labs.ai) · [@hermes-labs-ai](https://github.com/hermes-labs-ai)
