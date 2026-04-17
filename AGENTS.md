# AGENTS.md — rule-audit

Guidance for AI agents (Claude Code, Cursor, Aider, Continue, etc.) editing this repo.

Human reviewers read this too. Short, imperative, load-bearing.

## What this repo is

`rule-audit` — a **static analyzer for AI system prompts**. Input: raw prompt text. Output: structured report of contradictions, coverage gaps, priority ambiguities, meta-paradoxes, absoluteness issues, and concrete edge-case attack scenarios.

Pure Python. Zero LLM dependency. Zero network calls. Runs in milliseconds.

Think: `bandit` / `semgrep` — but for system prompts.

Part of the Hermes Labs AI Audit Toolkit:
- `rule-audit` — static analysis of prompts (this repo)
- `jailbreak-bench` — dynamic red-team suite that runs the attacks rule-audit predicts will succeed
- `colony-probe` — extraction testing for deployed LLM endpoints

## Start here

1. Read `CLAUDE.md` — project conventions, adding detectors, adding clusters.
2. Read `SPEC.md` — data model, detector algorithms, severity calibration.
3. Read `ROADMAP.md` — what's in v0.1.0, what's planned for v0.2+.
4. Read `benchmarks/README.md` — expected finding counts per sample prompt.

## Public API

Three entry points. These are the stability guarantee — breaking changes require a major version bump.

```python
from rule_audit import audit, audit_file, AuditReport

# Inline string
report: AuditReport = audit("You are helpful. You must never lie. Always answer.")

# From file
report: AuditReport = audit_file("samples/basic_assistant.txt")

# AuditReport surface
report.summary()        # str — terminal summary
report.to_markdown()    # str — full markdown report
report.to_dict()        # dict — JSON-serializable
report.to_json()        # str — JSON
report.risk_score       # float — 0..100 composite
report.risk_label       # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
report.edge_cases       # list[EdgeCase]
report.result.rules                 # list[Rule]
report.result.contradictions        # list[Contradiction]
report.result.gaps                  # list[Gap]
report.result.priority_ambiguities  # list[PriorityAmbiguity]
report.result.meta_paradoxes        # list[MetaParadox]
report.result.absoluteness_issues   # list[AbsolutenessIssue]
```

CLI: `rule-audit [prompt] [--file PATH] [--format markdown|json|summary] [--min-severity high|medium|low] [--verbose]`

Exit codes: `0` = LOW/MEDIUM, `2` = HIGH/CRITICAL, `1` = error.

## Extension points

### Add a new keyword cluster

Edit `_KEYWORD_CLUSTERS` in `rule_audit/analyzer.py`. Each cluster is a domain name mapped to a list of lowercase keyword stems.

```python
_KEYWORD_CLUSTERS: dict[str, list[str]] = {
    "harm": ["harm", "dangerous", ...],
    ...
    "your_new_cluster": ["keyword1", "keyword2", ...],
}
```

Rules that share any cluster are considered "about the same topic" for contradiction detection.

### Add a new detector

1. Write a detector function in `analyzer.py`: `_is_<kind>_contradiction(rule_a, rule_b) -> Optional[Contradiction]` (or a result type you add).
2. If it's a new result class: add a dataclass alongside `Contradiction` / `Gap` / etc. and include it in `AnalysisResult`.
3. Register the detector in `find_contradictions()` (or the top-level `analyze()`).
4. Add an edge-case generator in `rule_audit/edge_cases.py`.
5. Render it in `rule_audit/report.py` (add a section renderer, wire it into `to_markdown()` and `to_dict()`).
6. Write tests in `tests/test_analyzer.py`. **Tests are required.** The CI matrix runs Python 3.9 through 3.12.

### Adjust severity

See `SPEC.md` §4 for calibration. Change risk weights in `AnalysisResult.risk_score` (`analyzer.py`) — update the thresholds in `AuditReport.risk_label` (`report.py`) if needed.

## Project structure

```
rule_audit/
  __init__.py       # Public API: audit(), audit_file(), AuditReport
  __main__.py       # python -m rule_audit entry
  parser.py         # Sentence splitting, modality detection, Rule objects
  analyzer.py       # Contradiction / gap / priority / meta / absoluteness detectors
  edge_cases.py     # Concrete scenario generator from AnalysisResult
  report.py         # AuditReport + Markdown / JSON renderers
  cli.py            # Argparse CLI
  py.typed          # PEP 561 type-hint marker

tests/              # pytest — 174 tests, all pure Python
samples/            # 5 real-world-style system prompts
benchmarks/         # Expected finding counts per sample
launch/             # Launch post drafts (do not ship to PyPI)
```

## Conventions

- Pure Python stdlib only. No runtime dependencies. If you're tempted to add one, don't.
- Rule objects are immutable dataclasses. Parser produces them, analyzer consumes them.
- Public functions have type hints and "Added in vX.Y.Z" docstrings.
- Library code uses `logging.getLogger(__name__)`. Only `cli.py` calls `print()`.
- Tests live in `tests/`. Benchmarks live in `benchmarks/`. Launch copy lives in `launch/`.

## Don't

- Don't add an LLM dependency to the core library. v0.2 will add an **optional** `--llm` plugin; that is not v0.1.
- Don't silently change detector output. `tests/test_benchmark.py` asserts finding counts against `samples/*.txt` — if you legitimately shift counts, update the asserts and `benchmarks/README.md` in the same PR.
- Don't break the exit-code contract. `rule-audit` returning `2` on HIGH/CRITICAL is load-bearing for CI integrations.
- Don't add emojis to library code. (The markdown renderer uses a handful of status glyphs; that's scoped to `report.py`.)

## Cross-product context

If an agent finds a contradiction that `rule-audit` classifies HIGH severity, the exploit construction is then handed to `jailbreak-bench` for dynamic verification. That's the pipeline: static finds the flaw, dynamic proves it's reachable. Don't reinvent dynamic testing in this repo.

Home: <https://hermes-labs.ai>
