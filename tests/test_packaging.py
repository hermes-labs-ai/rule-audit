"""
tests/test_packaging.py

Release-boundary regression: build the distribution the way the release
workflow does (``python -m build``: sdist, then wheel from that sdist) and
run the shipped wheel from outside the source checkout.

Every other test imports ``rule_audit`` from the working tree, so a file that
exists in the repo but never reaches the wheel is invisible to them. That is
exactly how 0.3.0 shipped without its calibration corpus: the source checkout
passed, the published wheel exited 1 on
``python -m rule_audit.evidence --case negative_clean_prompt``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from rule_audit import evidence
from rule_audit.calibration import DEFAULT_CASES_DIR, load_cases

REPO_ROOT = Path(__file__).resolve().parent.parent
CASE_ID = "negative_clean_prompt"


def _run(args, cwd, env):
    return subprocess.run(
        args, cwd=str(cwd), env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600,
    )


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory) -> Path:
    """The wheel ``python -m build`` produces from this checkout, via the sdist."""
    outdir = tmp_path_factory.mktemp("dist")
    result = _run(
        [sys.executable, "-m", "build", "--outdir", str(outdir), str(REPO_ROOT)],
        cwd=outdir, env=dict(os.environ),
    )
    assert result.returncode == 0, (
        "python -m build failed (is the `build` package installed? "
        "it is part of the [dev] extras):\n" + result.stdout + result.stderr
    )
    wheels = list(outdir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel in {outdir}, got {wheels}"
    return wheels[0]


def test_wheel_contains_the_whole_calibration_corpus(built_wheel):
    expected = {
        f"rule_audit/calibration_cases/{path.name}"
        for path in DEFAULT_CASES_DIR.glob("*.json")
    }
    assert expected, f"no case files found in {DEFAULT_CASES_DIR}"
    shipped = set(zipfile.ZipFile(built_wheel).namelist())
    missing = sorted(expected - shipped)
    assert not missing, f"calibration cases missing from the built wheel: {missing}"


def test_installed_wheel_runs_a_calibration_case_outside_the_checkout(built_wheel, tmp_path):
    """The exact command that failed on the public 0.3.0 wheel, run against
    the freshly built wheel from a directory that is not the repo."""
    site = tmp_path / "site"
    zipfile.ZipFile(built_wheel).extractall(site)
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(site)

    # Prove the subprocess resolves the wheel, not the working tree.
    where = _run(
        [sys.executable, "-c", "import rule_audit; print(rule_audit.__file__)"], cwd, env,
    )
    assert where.returncode == 0, where.stderr
    assert Path(where.stdout.strip()).resolve().is_relative_to(site.resolve()), where.stdout

    run = _run([sys.executable, "-m", "rule_audit.evidence", "--case", CASE_ID], cwd, env)
    assert run.returncode != 1, f"wheel could not start the run:\n{run.stdout}\n{run.stderr}"
    envelope = json.loads(run.stdout)
    assert envelope["data"]["case"]["id"] == CASE_ID
    assert not [f for f in envelope["findings"] if f["id"].startswith("input.")]

    # Same verdict as the source checkout: only the clock and the Git SHA may differ.
    case = {c["id"]: c for c in load_cases()}[CASE_ID]
    expected = evidence.envelope_for(case["prompt"], f"calibration/cases/{CASE_ID}.json", case)
    assert run.returncode == expected["exitCode"] == envelope["exitCode"]
    for key in ("status", "inputHash", "findings"):
        assert envelope[key] == expected[key], key
    assert envelope["data"]["input"]["source"] == expected["data"]["input"]["source"]
