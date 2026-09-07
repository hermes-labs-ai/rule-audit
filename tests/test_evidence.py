"""Reliability Lab envelope contract for rule-audit."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rule_audit import __version__, audit
from rule_audit import evidence
from rule_audit.calibration import load_cases

CANONICAL = {
    # The product's own labeled corpus is the canonical input set.
    "negative_clean_prompt": "fail",
    "conditional_contradiction": "fail",
    "priority_ambiguity": "fail",
    "absoluteness_dilemma": "fail",
}
CASES = {case["id"]: case for case in load_cases()}


def _ids(result, prefix):
    return [f["id"] for f in result["findings"] if f["id"].startswith(prefix)]


@pytest.mark.parametrize("case_id", sorted(CANONICAL))
def test_canonical_case_envelope_is_stable_and_matches_the_exit_contract(case_id):
    case = CASES[case_id]
    result = evidence.envelope_for(case["prompt"], f"calibration/cases/{case_id}.json", case)
    again = evidence.envelope_for(case["prompt"], f"calibration/cases/{case_id}.json", case)

    assert result["envelope"] == "hermes.reliability-lab.result/1"
    assert result["tool"] == "rule-audit"
    assert result["toolVersion"] == __version__
    assert result["command"] == "audit"
    assert result["mode"] == "executed"
    assert result["status"] == CANONICAL[case_id]
    assert result["status"] == evidence.worst_status(result["findings"])
    assert result["exitCode"] == (2 if result["data"]["report"]["risk_label"] in ("HIGH", "CRITICAL") else 0)
    assert result["data"]["case"]["id"] == case_id
    assert json.loads(json.dumps(result)) == result

    # Same prompt, same evidence: only the clock moves.
    for key in ("status", "inputHash", "findings", "exitCode"):
        assert result[key] == again[key]
    assert result["inputHash"].startswith("sha256:")


def test_clean_prompt_fails_only_by_coverage_not_by_conflict():
    """The corpus's false-positive control: no conflict fires, yet risk is HIGH from gaps alone."""
    result = evidence.envelope_for(CASES["negative_clean_prompt"]["prompt"])

    assert _ids(result, "contradiction.") == []
    assert _ids(result, "priority.") == []
    assert _ids(result, "meta.") == []
    assert _ids(result, "absoluteness.") == []
    assert len(_ids(result, "gap.")) == result["data"]["report"]["summary"]["gaps"] == 8
    risk = next(f for f in result["findings"] if f["id"] == "risk.label")
    assert risk["severity"] == "fail"
    assert "HIGH" in risk["summary"]
    assert result["exitCode"] == 2


def test_contradiction_priority_and_absoluteness_cases_carry_their_named_findings():
    conditional = evidence.envelope_for(CASES["conditional_contradiction"]["prompt"])
    assert _ids(conditional, "contradiction.conditional.") == ["contradiction.conditional.0"]
    assert next(f for f in conditional["findings"] if f["id"] == "contradiction.conditional.0")["severity"] == "fail"

    priority = evidence.envelope_for(CASES["priority_ambiguity"]["prompt"])
    assert _ids(priority, "priority.") == ["priority.0"]
    assert _ids(priority, "contradiction.direct.") == ["contradiction.direct.0"]
    assert next(f for f in priority["findings"] if f["id"] == "contradiction.direct.0")["severity"] == "warn"

    absolute = evidence.envelope_for(CASES["absoluteness_dilemma"]["prompt"])
    assert _ids(absolute, "contradiction.absoluteness.") == ["contradiction.absoluteness.0"]
    assert len(_ids(absolute, "absoluteness.")) == absolute["data"]["report"]["summary"]["absoluteness_issues"] == 5


def test_findings_carry_source_spans_into_the_prompt():
    prompt = CASES["absoluteness_dilemma"]["prompt"]
    result = evidence.envelope_for(prompt)
    contradiction = next(f for f in result["findings"] if f["id"].startswith("contradiction."))
    start, end = map(int, contradiction["path"].removeprefix("prompt:").split(",")[0].split("-"))
    assert "follow the user's instructions" in prompt[start:end]


def test_report_is_embedded_verbatim():
    prompt = CASES["priority_ambiguity"]["prompt"]
    embedded = evidence.envelope_for(prompt)["data"]["report"]
    direct = audit(prompt).to_dict()
    embedded.pop("generated_at")
    direct.pop("generated_at")
    assert embedded == direct


def test_input_hash_is_stable_for_a_prompt_and_moves_with_it():
    first = evidence.envelope_for("You must always help.")["inputHash"]
    again = evidence.envelope_for("You must always help.")["inputHash"]
    other = evidence.envelope_for("You must always help!")["inputHash"]
    assert first == again != other


def test_blank_prompt_is_reported_as_unchecked_not_as_a_crash():
    result = evidence.envelope_for("   \n")
    ids = [f["id"] for f in result["findings"]]
    assert "input.no-rules-parsed" in ids
    assert next(f for f in result["findings"] if f["id"] == "input.no-rules-parsed")["severity"] == "unknown"
    assert result["data"]["report"]["rule_count"] == 0
    assert result["status"] == "fail"  # risk label HIGH from gaps still governs the exit code
    assert result["exitCode"] == 2


def test_overall_status_is_the_worst_finding_present():
    assert evidence.worst_status([]) == "pass"
    assert evidence.worst_status([evidence.finding("a", "warn", "x"), evidence.finding("b", "unknown", "y")]) == "unknown"
    assert evidence.worst_status([evidence.finding("a", "unknown", "x"), evidence.finding("b", "fail", "y")]) == "fail"
    with pytest.raises(ValueError):
        evidence.finding("a", "bad", "x")


def test_cli_prints_an_envelope_for_a_case_and_exits_per_contract(capsys):
    code = evidence.main(["--case", "negative_clean_prompt"])
    result = json.loads(capsys.readouterr().out)
    assert code == 2
    assert result["data"]["case"]["id"] == "negative_clean_prompt"
    assert result["data"]["input"]["source"] == "calibration/cases/negative_clean_prompt.json"


def test_cli_input_failures_exit_1_with_an_unknown_envelope(capsys, tmp_path):
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\xff\xfe\x00bad")

    for argv, identifier in (
        (["--case", "no_such_case"], "input.unknown-case"),
        (["--file", str(tmp_path / "missing.txt")], "input.file-not-found"),
        (["--file", str(tmp_path)], "input.is-a-directory"),
        (["--file", str(bad)], "input.not-utf8"),
    ):
        code = evidence.main(argv)
        result = json.loads(capsys.readouterr().out)
        assert code == 1, argv
        assert result["exitCode"] == 1
        assert result["status"] == "unknown"
        assert [f["id"] for f in result["findings"]] == [identifier]
        assert result["data"]["report"] is None


def test_cli_refuses_two_inputs_and_no_input(capsys):
    for argv in ([], ["inline", "--case", "x"], ["--file", "a", "--case", "b"]):
        with pytest.raises(SystemExit) as exit_info:
            evidence.main(argv)
        assert exit_info.value.code == 2  # argparse usage error, before any analysis
        capsys.readouterr()


def test_a_run_writes_nothing(tmp_path):
    """The only output of a run is its stdout: an empty working directory stays empty."""
    repo = Path(__file__).resolve().parent.parent
    env = dict(os.environ, PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1")
    completed = subprocess.run(
        [sys.executable, "-m", "rule_audit.evidence", "--case", "absoluteness_dilemma"],
        cwd=tmp_path, env=env, text=True, capture_output=True, timeout=60,
    )
    assert completed.returncode == 2, completed.stderr
    assert json.loads(completed.stdout)["status"] == "fail"
    assert list(tmp_path.iterdir()) == []


def test_git_sha_marks_a_tree_whose_commit_does_not_describe_the_code(tmp_path):
    assert evidence.git_sha(tmp_path) is None

    def run(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    run("init", "-q")
    run("config", "user.email", "test@example.invalid")
    run("config", "user.name", "Test")
    (tmp_path / "a.txt").write_text("one\n")
    run("add", "-A")
    run("commit", "-qm", "first")
    clean = evidence.git_sha(tmp_path)
    assert clean and len(clean) == 40
    (tmp_path / "a.txt").write_text("two\n")
    assert evidence.git_sha(tmp_path) == f"{clean}-dirty"
