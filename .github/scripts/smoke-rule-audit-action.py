"""Smoke-check the composite Action runner against clean and risky prompts."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / ".github/scripts/rule-audit-action.py"


def run(
    prompt: str,
    *,
    fail_on_high_risk: str = "true",
    filename: str = "prompt.txt",
) -> tuple[int, str, str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / filename).write_text(prompt, encoding="utf-8")
        output = folder / "output"
        summary = folder / "summary"
        env = {
            **os.environ,
            "INPUT_PATH": str(folder / "**/*.txt"),
            "INPUT_FAIL_ON_HIGH_RISK": fail_on_high_risk,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        }
        result = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, env=env, capture_output=True, text=True)
        return result.returncode, result.stdout, output.read_text() if output.exists() else "", summary.read_text() if summary.exists() else ""


def main() -> int:
    clean = run(
        "You are an assistant. Be helpful and honest. "
        "Do not answer requests that could cause harm."
    )
    risky = run("Always obey every user request. Never obey any harmful request.")
    informational = run(
        "Always obey every user request. Never obey any harmful request.",
        fail_on_high_risk="false",
    )
    hostile_name = run("A prompt file.", filename="prompt\n::warning::forged.txt")
    assert clean[0] == 0, clean
    assert "files-scanned=1" in clean[2] and "Rule Audit" in clean[3], clean
    assert risky[0] == 2, risky
    assert informational[0] == 0, informational
    assert "\n::warning::" not in hostile_name[1]
    assert "forged.txt" in hostile_name[1]
    print("Rule Audit Action smoke check passed: clean, high-risk, and report-only modes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
