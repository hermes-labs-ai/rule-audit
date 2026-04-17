# Contributing to rule-audit

Thanks for the interest. This is a small, focused project with a high bar for precision — detectors ship with tests, period.

By participating, you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you open a PR

1. An issue exists describing the bug or feature, or you're fixing something trivial (typo, broken link).
2. You've read `CLAUDE.md` (project conventions), `SPEC.md` (detector algorithms), and `AGENTS.md` (public API, extension points).
3. Tests pass locally: `pytest -q` → 174 tests (or more if you added some).
4. Your change is scoped. One contribution = one concern.

## Dev setup

```bash
git clone https://github.com/roli-lpci/rule-audit
cd rule-audit
python -m pip install -e ".[dev]"
pytest -q
```

Python 3.9+ supported. CI runs the matrix 3.9 / 3.10 / 3.11 / 3.12.

## Adding a new detector

A detector is a function that takes `Rule` objects and returns a list of finding dataclasses.

1. **Decide the finding shape.** If it fits an existing class (`Contradiction`, `Gap`, `PriorityAmbiguity`, `MetaParadox`, `AbsolutenessIssue`), use that. Otherwise add a new dataclass in `rule_audit/analyzer.py`.
2. **Write the detector function.** Signature: `def _is_<kind>(rule_a, rule_b) -> Optional[Contradiction]` (pairwise) or `def find_<kind>(rules: list[Rule]) -> list[Finding]` (corpus-level).
3. **Register it.** Add to the detector chain in `find_contradictions()` or call from `analyze()`.
4. **Generate edge cases.** Add a `_edge_cases_from_<kind>()` function in `rule_audit/edge_cases.py` and call it from `generate_edge_cases()`.
5. **Render the report.** Add a section renderer in `rule_audit/report.py` and wire it into `to_markdown()` and `to_dict()`.
6. **Write tests.** `tests/test_analyzer.py` — positive cases, negative cases, severity calibration, an adversarial case that *should* trigger it and a lookalike that *should not*.
7. **Update the sample benchmark.** Running `pytest tests/test_benchmark.py` will fail if finding counts shift. If the shift is intentional, update the asserts and `benchmarks/README.md` in the same PR.
8. **Update `CHANGELOG.md`** under `## [Unreleased]`.

## Adding a new keyword cluster

Edit `_KEYWORD_CLUSTERS` in `rule_audit/analyzer.py`:

```python
_KEYWORD_CLUSTERS: dict[str, list[str]] = {
    "harm": ["harm", "dangerous", "violence", ...],
    # ...
    "your_cluster": ["keyword1", "keyword2", "keyword3"],
}
```

Guidelines:
- Cluster names are short, singular, lowercase nouns: `harm`, `privacy`, `access`, `policy`.
- 8–20 keywords per cluster. More is fine when the domain is broad.
- Keywords are lowercase stems. The parser lowercases text before matching.
- Don't overlap with existing clusters unless the overlap is intentional (e.g., `harm` and `safety` share `dangerous` by design).

Add tests that confirm your cluster triggers contradiction detection on a realistic pair of rules.

## Severity rules

Severity isn't arbitrary. The calibration in `SPEC.md` §4 defines:

| Severity | Exploitability |
|---|---|
| `high` | Deterministic attack path exists — ≤ 3 messages, both rules absolute |
| `medium` | Requires domain knowledge or social engineering |
| `low` | Theoretical conflict, unlikely to manifest |

If you change weights in `AnalysisResult.risk_score` or thresholds in `AuditReport.risk_label`, document the rationale and update `SPEC.md`. Expect pushback — scoring changes invalidate customer audit reports.

## Tests required

Every new detector, cluster, severity rule, or parser pattern needs a test. PRs without tests will not be merged. Use the existing `tests/test_*.py` style — pytest, no fixtures for simple cases, descriptive names (`test_direct_contradiction_on_shared_cluster`).

## Style

- Standard library only in `rule_audit/*`. No runtime deps. If you need a new dep, open an issue first.
- Type hints on every public function. `py.typed` is shipped; don't break it.
- Library code uses `logging.getLogger(__name__)`. Only `cli.py` calls `print()`.
- Formatting: whatever `black` produces, line length 100.
- Docstrings for public functions: one-line summary, `Args:` / `Returns:`, `Added in vX.Y.Z.` footer.

## What not to contribute

- **LLM calls in the core library.** v0.2 will add `--llm` as an optional plugin. The core stays offline.
- **Heuristic changes without benchmarks.** "I think this detector should also catch X" is not enough. Add a test case; run the sample benchmarks; show the delta.
- **Emojis in library code.** The markdown renderer uses a handful of status glyphs; don't spread them.
- **Scope creep toward dynamic testing.** Dynamic red-teaming lives in the sibling repo `jailbreak-bench`. This repo is static analysis only.

## Commits

- Conventional-style is appreciated but not required: `feat: add override-loop detector`, `fix: off-by-one in gap heuristic`, `docs: clarify severity ladder`.
- One logical change per commit. Squash at merge.

## Release process

Maintainers only. Tag `v*` → CI builds wheel + sdist → publishes to PyPI via trusted publishing.

Before tagging:
- [ ] `CHANGELOG.md` has a dated section for the new version.
- [ ] `pyproject.toml` version bumped.
- [ ] `rule_audit/__init__.py` `__version__` bumped.
- [ ] `CITATION.cff` version + date bumped.
- [ ] Full test suite green on main for Python 3.9–3.12.

## Contact

- Bugs / features: [GitHub Issues](https://github.com/roli-lpci/rule-audit/issues).
- Security: `security@hermes-labs.ai` (see [SECURITY.md](SECURITY.md)).
- Code of conduct violations: `conduct@hermes-labs.ai`.
- General: <https://hermes-labs.ai>.
