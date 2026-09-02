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


def test_cli_version_matches_package_version(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"rule-audit {__version__}"
    assert __version__ == "0.1.3"
