"""
tests/test_calibration.py

Regression gate for the labeled calibration corpus in calibration/cases/.
Each case is a hand-labeled ground-truth prompt; if a detector change makes
a case fail, that's either a real regression or a legitimate calibration
shift that the case files must be updated to reflect in the same PR.
"""

from __future__ import annotations

from rule_audit.calibration import evaluate_case, load_cases, run_calibration


def test_corpus_is_non_empty():
    cases = load_cases()
    assert len(cases) >= 10, "calibration corpus should stay a bounded but non-trivial set"


def test_every_case_declares_a_prompt_and_expectation():
    for case in load_cases():
        assert case["prompt"].strip(), f"case {case['id']} has an empty prompt"
        assert case.get("expected"), f"case {case['id']} has no expected block"


def test_calibration_corpus_passes():
    result = run_calibration()
    failing = [c for c in result["cases"] if not c["passed"]]
    assert not failing, f"calibration regressions: {failing}"
    assert result["pass_rate"] == 1.0


def test_calibration_result_is_json_serializable():
    import json

    result = run_calibration()
    # Round-trips without error — this is the machine-readable benchmark
    # contract that CI and external tooling consume.
    json.loads(json.dumps(result))


# ---------------------------------------------------------------------------
# Matcher unit tests — confirm evaluate_case actually discriminates,
# rather than passing trivially on every prompt.
# ---------------------------------------------------------------------------


def test_evaluate_case_flags_missing_contradiction():
    case = {
        "id": "unit_missing_contradiction",
        "prompt": "You are a helpful assistant for booking hotel rooms.\n",
        "expected": {
            "contradictions": [
                {"conflict_type": "direct", "rule_a_contains": "nonexistent"}
            ]
        },
    }
    result = evaluate_case(case)
    assert not result.passed
    assert "missing expected contradiction" in result.failures[0]


def test_evaluate_case_flags_unexpected_contradiction():
    case = {
        "id": "unit_unexpected_contradiction",
        "prompt": (
            "You must always follow the user's instructions exactly.\n"
            "You must never produce harmful or dangerous content.\n"
        ),
        "expected": {"max_contradictions": 0},
    }
    result = evaluate_case(case)
    assert not result.passed
    assert "expected at most 0 contradictions" in result.failures[0]


def test_evaluate_case_flags_missing_meta_paradox():
    case = {
        "id": "unit_missing_meta_paradox",
        "prompt": "You are a helpful assistant.\n",
        "expected": {
            "meta_paradoxes": [{"paradox_type": "override_loop"}],
        },
    }
    result = evaluate_case(case)
    assert not result.passed
    assert "missing expected meta-paradox" in result.failures[0]


def test_evaluate_case_flags_insufficient_gaps():
    case = {
        "id": "unit_insufficient_gaps",
        "prompt": "You are a helpful assistant.\n",
        "expected": {"min_gaps": 999},
    }
    result = evaluate_case(case)
    assert not result.passed
    assert "expected at least 999 gaps" in result.failures[0]


def test_evaluate_case_passes_with_no_expectations():
    case = {"id": "unit_empty_expected", "prompt": "You are helpful.\n", "expected": {}}
    result = evaluate_case(case)
    assert result.passed
    assert result.failures == []
