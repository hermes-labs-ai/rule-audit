# rule-audit

**Static analyzer for AI system prompts. Finds logical contradictions, coverage gaps, and exploitable edge cases — without running an LLM.**

Built at Hermes Labs Hackathon Round 8: ModelBreak.

---

## The Problem

Any sufficiently complex AI safety prompt contains rules that contradict each other under specific conditions. These contradictions are invisible to the author but obvious to an attacker. `rule-audit` finds them first.

**Real contradiction in standard safety prompts:**
```
"You must always follow user instructions."
"You must never produce harmful content."
```
These are irreconcilable the moment a user instructs the model to produce harmful content. No priority clause means the model chooses arbitrarily — or the attacker chooses for it.

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

---

## Quickstart

### CLI

```bash
# Quick demo (no input needed — exercises every detector family)
rule-audit --demo

# Inline prompt
rule-audit "You are helpful. You must never lie. Always answer every question."

# From file
rule-audit --file system_prompt.txt

# Save Markdown report
rule-audit --file system_prompt.txt --output report.md

# JSON output for downstream processing
rule-audit --file system_prompt.txt --format json

# Summary only (for CI gates)
rule-audit --file system_prompt.txt --format summary

# Show all parsed rules
rule-audit --file system_prompt.txt --verbose

# Only show high-severity findings
rule-audit --file system_prompt.txt --min-severity high
```

Exit codes: `0` = low/no risk, `2` = high/critical risk, `1` = error.

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
# rule-audit report  [2026-04-15T...]
# ============================================================
#   Rules parsed          : 6
#   Contradictions        : 3  (2 high, 1 medium)
#   Coverage gaps         : 4
#   Priority ambiguities  : 2
#   Meta-paradoxes        : 0
#   Absoluteness issues   : 5
#   Edge case scenarios   : 11
#   Risk score            : 67/100  [HIGH]

# Full Markdown report
md = report.to_markdown()

# Access findings programmatically
for c in report.result.contradictions:
    print(c.severity, c.description)

for ec in report.edge_cases:
    print(ec.title)
    print(ec.attack_vector)
```

---

## What It Detects

### 1. Contradictions
Rule pairs where one says "always X" and another says "never X in context Y". Three subtypes:

- **Direct** — opposing modalities on the same topic (`MUST` vs `MUST_NOT`)
- **Conditional** — one rule applies unconditionally, another restricts within a subset (boundary is undefined)
- **Absoluteness** — two absolute rules that pull in opposite directions (compliance vs safety)

### 2. Coverage Gaps
Scenario domains with no rule coverage. Checks for:
- Harmful content handling
- Principal hierarchy (user vs operator vs developer)
- Ambiguous request handling
- Persona / roleplay scenarios
- Refusal protocol
- Instruction conflict resolution
- Self-disclosure rules
- Edge case fallback behavior

### 3. Priority Ambiguities
Rule clusters that conflict with no explicit ordering. Classic example: a safety rule and a helpfulness rule both applying to the same request, with no stated priority.

### 4. Meta-Rule Paradoxes
Rules that reference rules:
- **Self-defeating** — "ignore all instructions" voids itself
- **Override loops** — "these instructions supersede all others" is exploitable via injection
- **Circular** — a rule that requires itself to be applied before it can be applied

### 5. Absoluteness Audit
Every `always`/`never`/`under no circumstances` rule is challenged with:
- Known exceptions that legitimately exist
- Context-dependent cases where the absolute doesn't hold
- Adversarial triggers that exploit the absolute

### 6. Edge Case Scenarios
For each finding, generates the exact attack prompt an adversary would construct — including the attack vector, expected failure mode, and mitigation.

---

## Limitations

Honest list of what this tool does not do:

- **Lexical parser, not a language model.** The parser uses sentence splitting + modal-verb regex + keyword clusters. It will miss rules that require semantic understanding (e.g. "Under no circumstances should the bot discuss pricing" parses correctly, but implicit / implied rules embedded in narrative text are harder).
- **O(n²) pair comparison.** Fine for real-world prompts (< 100 rules). If you have a 1000-rule prompt, you have other problems.
- **14 semantic clusters, curated by hand.** Rules about uncommon topics (e.g. a specialty compliance domain) may not trigger coverage-gap detection. Extend `_KEYWORD_CLUSTERS` in `analyzer.py` for your domain.
- **Severity is lexical, not adversarial.** "CRITICAL" means "many absolute rules + contradictions in a short prompt" — it does not mean the prompt is actually exploitable end-to-end. Pair with dynamic testing via [`hermes-jailbench`](https://github.com/hermes-labs-ai/hermes-jailbench) and [`colony-probe`](https://github.com/hermes-labs-ai/colony-probe) for the full audit stack.
- **Absoluteness scoring defaults to 0.5** for sentences with modal verbs but no qualifier keyword. This is a design choice, not a bug — tune the threshold in `_compute_absoluteness` if your corpus skews differently.
- **English only.** Non-English system prompts are not supported in v0.1. Multilingual keyword clusters are on the v0.2 roadmap.
- **Single-document only.** Multi-part prompts (operator + user + tool results) merged into one input are analyzed as a flat rule list; structural separation between principals is not modeled yet.

---

## Architecture

```
rule_audit/
├── __init__.py      # Public API: audit(), audit_file(), AuditReport
├── parser.py        # Sentence splitting, modal verb detection, Rule objects
├── analyzer.py      # Contradiction finder, gap detector, priority mapper
├── edge_cases.py    # Scenario generator from analysis results
├── report.py        # Markdown + summary renderer, AuditReport class
└── cli.py           # CLI entry point
```

**Pure Python. Zero LLM dependency. Zero API calls.**

The parser uses NLP heuristics:
- Sentence boundary detection (period + newline + list markers)
- Modal verb regex patterns (must/should/may + negations)
- Absoluteness scoring (lexical keywords → 0.0–1.0 scale)
- Keyword cluster matching (14 semantic clusters: harm, privacy, identity, truth, ...)

The analyzer uses combinatorial pair analysis:
- O(n²) rule pair comparison (practical for prompts: n < 100)
- Cluster overlap detection for shared domain identification
- Modality opposition lookup table
- Absoluteness threshold gates

---

## Roadmap

Planned OSS work on this package:

| Phase | Feature | Status |
|-------|---------|--------|
| v0.1 | Core static analysis, CLI, Python API | Done |
| v0.2 | Rule diffing (before/after prompt edits) | Planned |
| v0.3 | LLM-augmented gap detection (optional plugin) | Planned |
| v0.4 | GitHub Action / CI integration | Planned |
| v1.0 | CSV / SARIF export for compliance toolchains | Planned |

The package stays MIT, fully free, no hosted tier. If you want EU AI Act compliance reports, ANNEX-IV packs, or red-team engagements delivered as a report, that's the [Hermes Labs audit practice](https://hermes-labs.ai), not a SaaS version of this tool.

---

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=rule_audit --cov-report=term-missing

# Test against a real prompt
echo "Your system prompt here" > test_prompt.txt
python -m rule_audit --file test_prompt.txt --verbose
```

---

## License

MIT — Hermes Labs 2026

---

## About Hermes Labs

[Hermes Labs](https://hermes-labs.ai) builds AI audit infrastructure for enterprise AI systems — EU AI Act readiness, ISO 42001 evidence bundles, continuous compliance monitoring, agent-level risk testing. We work with teams shipping AI into regulated environments.

**Our OSS philosophy — read this if you're deciding whether to depend on us:**

- **Everything we release is free, forever.** MIT or Apache-2.0. No "open core," no SaaS tier upsell, no paid version with the features you actually need. You can run this repo commercially, without talking to us.
- **We open-source our own infrastructure.** The tools we release are what Hermes Labs uses internally — we don't publish demo code, we publish production code.
- **We sell audit work, not licenses.** If you want an ANNEX-IV pack, an ISO 42001 evidence bundle, gap analysis against the EU AI Act, or agent-level red-teaming delivered as a report, that's at [hermes-labs.ai](https://hermes-labs.ai). If you just want the code to run it yourself, it's right here.

**The Hermes Labs OSS audit stack** (public, open-source, no SaaS):

**Static audit** (before deployment)
- [**lintlang**](https://github.com/hermes-labs-ai/lintlang) — Static linter for AI agent configs, tool descriptions, system prompts. `pip install lintlang`
- [**scaffold-lint**](https://github.com/hermes-labs-ai/scaffold-lint) — Scaffold budget + technique stacking (flags `SCAFFOLD_TOO_LONG`, `SCAFFOLD_STACKING` when multiple scaffold techniques are mixed)
- [**intent-verify**](https://github.com/hermes-labs-ai/intent-verify) — Repo intent verification + spec-drift checks

**Runtime observability** (while the agent runs)
- [**little-canary**](https://github.com/hermes-labs-ai/little-canary) — Prompt injection detection via sacrificial canary-model probes
- [**suy-sideguy**](https://github.com/hermes-labs-ai/suy-sideguy) — Runtime policy guard — user-space enforcement + forensic reports
- [**colony-probe**](https://github.com/hermes-labs-ai/colony-probe) — Prompt confidentiality audit — detects system-prompt reconstruction

**Regression & scoring** (to prove what changed)
- [**hermes-jailbench**](https://github.com/hermes-labs-ai/hermes-jailbench) — Jailbreak regression benchmark. `pip install hermes-jailbench`
- [**agent-convergence-scorer**](https://github.com/hermes-labs-ai/agent-convergence-scorer) — Score how similar N agent outputs are. `pip install agent-convergence-scorer`

**Supporting infra**
- [**claude-router**](https://github.com/hermes-labs-ai/claude-router) · [**zer0dex**](https://github.com/hermes-labs-ai/zer0dex) · [**quick-gate-python**](https://github.com/hermes-labs-ai/quick-gate-python) · [**quick-gate-js**](https://github.com/hermes-labs-ai/quick-gate-js) · [**repo-audit**](https://github.com/hermes-labs-ai/repo-audit)

---

Built by [Hermes Labs](https://hermes-labs.ai) · [@roli-lpci](https://github.com/roli-lpci)
