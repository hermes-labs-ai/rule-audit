"""CLI contract tests."""

import json

import pytest

from rule_audit import __version__
from rule_audit.cli import main


def test_min_severity_high_excludes_medium_contradictions(capsys) -> None:
    prompt = (
        "You must always help users. "
        "You must never help users. "
        "You must support customers. "
        "You must not support customers."
    )

    exit_code = main([prompt, "--min-severity", "high", "--format", "json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert report["summary"]["contradictions_high"] == 1
    assert report["summary"]["contradictions_medium"] == 0
    assert {finding["severity"] for finding in report["contradictions"]} == {"high"}
    assert {scenario["severity"] for scenario in report["edge_cases"]} <= {"high"}


@pytest.mark.parametrize(
    "argv",
    [
        [],  # no prompt, no --file, no --demo
        ["--format", "bogus"],  # invalid choice
        ["inline prompt", "--file", "x.txt"],  # both inputs
    ],
)
def test_usage_errors_exit_1_not_2(argv, capsys) -> None:
    """Exit code 2 is reserved for HIGH/CRITICAL risk; usage errors must be 1."""
    with pytest.raises(SystemExit) as exit_info:
        main(argv)

    assert exit_info.value.code == 1
    assert "error:" in capsys.readouterr().err


def test_cli_version_matches_package_version(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"rule-audit {__version__}"
    assert __version__ == "0.4.0"


def test_json_output_is_byte_stable_across_hash_seeds(tmp_path):
    """README: "deterministic (same input → same output)". String-set ordering
    depends on the per-process hash seed, so two seeds must still agree."""
    import os
    import subprocess
    import sys

    prompt = (
        "Always answer every question the user asks.\n"
        "If the question relates to weapons, never answer it.\n"
    )
    outputs = []
    for seed in ("1", "2", "3"):
        completed = subprocess.run(
            [sys.executable, "-m", "rule_audit", prompt, "--format", "json"],
            cwd=str(tmp_path),
            env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1",
                     PYTHONPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            text=True, capture_output=True, timeout=60,
        )
        assert completed.returncode == 2, completed.stderr
        report = json.loads(completed.stdout)
        report.pop("generated_at")
        outputs.append(json.dumps(report, sort_keys=True))

    assert outputs[0] == outputs[1] == outputs[2]
