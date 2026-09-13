# CLAUDE.md — rule-audit

## What This Is
Static analyzer for AI system prompts. Finds contradictions, gaps, and exploitable edge cases.
Pure Python, no LLM dependency. Built at Hermes Labs Hackathon Round 8.

## Project Structure
```
rule_audit/
├── __init__.py      # audit(), audit_file(), AuditReport exports
├── parser.py        # Rule extraction from raw text
├── analyzer.py      # Core analysis: contradictions, gaps, priority, meta, absoluteness
├── edge_cases.py    # EdgeCase generation from AnalysisResult
├── report.py        # AuditReport class + Markdown renderer
└── cli.py           # CLI entry point (python -m rule_audit)

tests/
├── test_parser.py   # Parser unit tests
└── test_analyzer.py # Analyzer unit tests (includes hackathon prompt integration test)
```

## Run Tests
```bash
cd /path/to/rule-audit
pip install -e ".[dev]"
pytest
pytest --cov=rule_audit --cov-report=term-missing
```

## Key Design Decisions
- **No LLM dependency**: All analysis is regex + heuristics. Fast, deterministic, offline.
- **Rule objects are immutable dataclasses**: Parser produces them, analyzer consumes them, nothing mutates.
- **Severity is propagated**: Contradictions have severity; EdgeCases inherit or derive severity. AuditReport.risk_score is a weighted sum.
- **Keyword clusters**: 14 semantic clusters in `analyzer.py` → `_KEYWORD_CLUSTERS`. Add new clusters there to expand detection coverage.
- **Modality opposition table**: `_CONTRADICTORY_PAIRS` in analyzer.py defines which modality pairs are contradictory. Extend this set to add new contradiction logic.

## Adding New Detectors
1. Add detection function in `analyzer.py` returning a list of result objects
2. Add result dataclass in `analyzer.py`
3. Call it in `analyze()` and include in `AnalysisResult`
4. Add edge case generator in `edge_cases.py` → `generate_edge_cases()`
5. Add renderer in `report.py`
6. Add tests in `tests/test_analyzer.py`

## Adding New Keyword Clusters
Edit `_KEYWORD_CLUSTERS` in `analyzer.py`. Each cluster is a list of keywords.
Cluster membership is used to determine if two rules are "about the same topic".

## Known Limitations
- Parser is heuristic — it will miss some rules and may over-parse others
- Absoluteness scoring is lexical only — semantic absoluteness isn't captured
- Contradiction detection is O(n²) in rules — fine for real prompts (n < 100)
- No support for multi-document prompts (operator + user + tool results)

## Backlog (don't start unless asked)
- Rule diffing between prompt versions
- LLM-augmented semantic contradiction detection (optional plugin)
- GitHub Action for CI integration
- Web UI with prompt editor
- Export to CSV / SARIF format for compliance toolchains
