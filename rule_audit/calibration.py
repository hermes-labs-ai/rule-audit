"""
rule_audit/calibration.py

Runs the bounded labeled calibration corpus in calibration/cases/*.json
against the live detectors and produces a machine-readable benchmark
result: per-case pass/fail plus a corpus-level precision/recall summary.

Each case file declares a `prompt` and an `expected` block. `expected` may
combine any of:
  - contradictions: [{conflict_type, severity, rule_a_contains, rule_b_contains}]
  - max_contradictions: int          (false-positive control)
  - meta_paradoxes: [{paradox_type, rule_contains}]
  - max_meta_paradoxes: int
  - min_priority_ambiguities: int
  - min_gaps: int
  - min_absoluteness_issues: int

This is intentionally a small, hand-labeled fixture set (not a statistical
sample) — it exists to catch detector regressions with an explicit, auditable
ground truth, not to claim population-level accuracy.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rule_audit import audit
from rule_audit.analyzer import Contradiction, MetaParadox

logger = logging.getLogger(__name__)

DEFAULT_CASES_DIR = Path(__file__).resolve().parent.parent / "calibration" / "cases"


@dataclass
class CaseResult:
    case_id: str
    description: str
    passed: bool
    failures: list[str] = field(default_factory=list)


def load_cases(cases_dir: Path = DEFAULT_CASES_DIR) -> list[dict[str, Any]]:
    """Load every labeled case file from `cases_dir`, sorted by id for determinism."""
    cases = []
    for path in sorted(cases_dir.glob("*.json")):
        with open(path, "r", encoding="utf-8") as fh:
            case = json.load(fh)
        case.setdefault("id", path.stem)
        cases.append(case)
    return cases


def _text_match(rule_text: str, substring: str) -> bool:
    return substring.lower() in rule_text.lower()


def _contradiction_matches(
    contradictions: list[Contradiction], expectation: dict[str, Any]
) -> bool:
    conflict_type = expectation.get("conflict_type")
    severity = expectation.get("severity")
    a_sub = expectation.get("rule_a_contains", "")
    b_sub = expectation.get("rule_b_contains", "")

    for c in contradictions:
        if conflict_type and c.conflict_type != conflict_type:
            continue
        if severity and c.severity != severity:
            continue
        forward = _text_match(c.rule_a.text, a_sub) and _text_match(c.rule_b.text, b_sub)
        backward = _text_match(c.rule_a.text, b_sub) and _text_match(c.rule_b.text, a_sub)
        if forward or backward:
            return True
    return False


def _meta_paradox_matches(
    paradoxes: list[MetaParadox], expectation: dict[str, Any]
) -> bool:
    paradox_type = expectation.get("paradox_type")
    rule_sub = expectation.get("rule_contains", "")

    for mp in paradoxes:
        if paradox_type and mp.paradox_type != paradox_type:
            continue
        if rule_sub and not _text_match(mp.rule.text, rule_sub):
            continue
        return True
    return False


def evaluate_case(case: dict[str, Any]) -> CaseResult:
    """Run one labeled case through `audit()` and check it against `expected`."""
    prompt = case["prompt"]
    expected = case.get("expected", {})
    failures: list[str] = []

    report = audit(prompt)
    result = report.result

    for exp_contradiction in expected.get("contradictions", []):
        if not _contradiction_matches(result.contradictions, exp_contradiction):
            failures.append(f"missing expected contradiction: {exp_contradiction}")

    if "max_contradictions" in expected:
        limit = expected["max_contradictions"]
        if len(result.contradictions) > limit:
            failures.append(
                f"expected at most {limit} contradictions, found "
                f"{len(result.contradictions)}: "
                f"{[repr(c) for c in result.contradictions]}"
            )

    for exp_paradox in expected.get("meta_paradoxes", []):
        if not _meta_paradox_matches(result.meta_paradoxes, exp_paradox):
            failures.append(f"missing expected meta-paradox: {exp_paradox}")

    if "max_meta_paradoxes" in expected:
        limit = expected["max_meta_paradoxes"]
        if len(result.meta_paradoxes) > limit:
            failures.append(
                f"expected at most {limit} meta-paradoxes, found "
                f"{len(result.meta_paradoxes)}"
            )

    if "min_priority_ambiguities" in expected:
        min_count = expected["min_priority_ambiguities"]
        if len(result.priority_ambiguities) < min_count:
            failures.append(
                f"expected at least {min_count} priority ambiguities, found "
                f"{len(result.priority_ambiguities)}"
            )

    if "min_gaps" in expected:
        min_count = expected["min_gaps"]
        if len(result.gaps) < min_count:
            failures.append(
                f"expected at least {min_count} gaps, found {len(result.gaps)}"
            )

    if "min_absoluteness_issues" in expected:
        min_count = expected["min_absoluteness_issues"]
        if len(result.absoluteness_issues) < min_count:
            failures.append(
                f"expected at least {min_count} absoluteness issues, found "
                f"{len(result.absoluteness_issues)}"
            )

    return CaseResult(
        case_id=case["id"],
        description=case.get("description", ""),
        passed=not failures,
        failures=failures,
    )


def run_calibration(cases_dir: Path = DEFAULT_CASES_DIR) -> dict[str, Any]:
    """Run the full labeled corpus and return a machine-readable benchmark result."""
    cases = load_cases(cases_dir)
    results = [evaluate_case(case) for case in cases]

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    return {
        "cases_dir": str(cases_dir),
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": (passed / total) if total else 0.0,
        "cases": [
            {
                "id": r.case_id,
                "description": r.description,
                "passed": r.passed,
                "failures": r.failures,
            }
            for r in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: `python -m rule_audit.calibration [cases_dir]`.

    Prints the machine-readable benchmark result as JSON to stdout and
    exits non-zero if any labeled case fails — the CI regression gate.
    """
    import sys

    args = sys.argv[1:] if argv is None else argv
    cases_dir = Path(args[0]) if args else DEFAULT_CASES_DIR

    result = run_calibration(cases_dir)
    print(json.dumps(result, indent=2))

    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
