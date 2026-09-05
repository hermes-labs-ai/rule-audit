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
    assert __version__ == "0.2.0"
