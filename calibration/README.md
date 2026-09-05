# Calibration corpus

A small, hand-labeled fixture set with an explicit ground truth, used to catch
detector regressions and to give an honest, checkable answer to "does this
actually work?" beyond the five demo samples in `samples/`.

This is **not** a statistical accuracy claim over real-world prompts — it's
11 bounded cases, each asserting a specific, auditable expectation against
the live detectors. Positive cases pin down true positives per detector
family; negative cases pin down known false-positive traps (e.g. opposing
modality alone, on unrelated topics, must not be enough to flag a
contradiction).

## Layout

```
calibration/
├── README.md
└── cases/
    ├── absoluteness_dilemma.json
    ├── absoluteness_issue_present.json
    ├── conditional_contradiction.json
    ├── direct_medium.json
    ├── gaps_domestic_prompt.json
    ├── meta_override_loop.json
    ├── meta_potential_override.json
    ├── negative_clean_prompt.json
    ├── negative_disjoint_topics.json
    ├── priority_ambiguity.json
    └── scope_conflict.json
```

## Case schema

```json
{
  "id": "case_name",
  "description": "One line: what this case proves.",
  "prompt": "Raw system-prompt text.",
  "expected": {
    "contradictions": [
      {"conflict_type": "direct", "severity": "high",
       "rule_a_contains": "substring", "rule_b_contains": "substring"}
    ],
    "max_contradictions": 0,
    "meta_paradoxes": [
      {"paradox_type": "override_loop", "rule_contains": "substring"}
    ],
    "max_meta_paradoxes": 0,
    "min_priority_ambiguities": 1,
    "min_gaps": 8,
    "min_absoluteness_issues": 1
  }
}
```

`expected` fields are optional and composable. `*_contains` matchers are
case-insensitive substring checks against the matched rule's text — the
source-span evidence (`Rule.start` / `Rule.end`, surfaced in
`AuditReport.to_dict()["rules"][i]["span"]`) lets you trace any match back to
the exact character range in the original prompt.

## Running it

```bash
# Machine-readable benchmark result (JSON) to stdout, exit 1 on any failing case
python -m rule_audit.calibration

# As a pytest regression gate
pytest tests/test_calibration.py -v
```

## Adding a case

1. Write the prompt and run `python -c "from rule_audit import audit; ..."` to see
   what the detectors actually produce — don't guess the expected block.
2. Add the JSON file to `calibration/cases/`.
3. Run `python -m rule_audit.calibration` to confirm it passes.
4. If a detector legitimately changes behavior, update the affected case
   files in the same PR (mirrors the `tests/test_benchmark.py` policy for
   the sample corpus).
