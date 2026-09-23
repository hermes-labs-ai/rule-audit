"""Run Rule Audit over a recursive glob and publish a concise Actions summary."""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    pattern = os.environ.get("INPUT_PATH", "")
    if not pattern:
        print("INPUT_PATH must contain a file glob", file=sys.stderr)
        return 1

    files = sorted({Path(name) for name in glob.glob(pattern, recursive=True) if Path(name).is_file()})
    if not files:
        print(f"No files matched Rule Audit path pattern: {pattern!r}", file=sys.stderr)
        return 1

    executable = shutil.which("rule-audit")
    if executable is None:
        print("rule-audit executable is not installed", file=sys.stderr)
        return 1

    high_risk = False
    summaries: list[str] = []
    for path in files:
        safe_path = json.dumps(str(path), ensure_ascii=True).replace("`", "\\u0060")
        result = subprocess.run(
            [executable, f"--file={path}", "--format", "summary"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or result.stderr).strip()
        print(f"### {safe_path}\n\n{output}\n")
        summaries.append(f"### `{safe_path}`\n\n{output or 'No summary output.'}")
        if result.returncode == 2:
            high_risk = True
        elif result.returncode != 0:
            return result.returncode

    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as stream:
            stream.write(f"files-scanned={len(files)}\n")

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as stream:
            stream.write("## Rule Audit\n\n")
            stream.write(f"Audited {len(files)} file(s) with Rule Audit 0.5.0.\n\n")
            stream.write("\n\n".join(summaries))
            stream.write("\n")

    fail_on_high_risk = os.environ.get("INPUT_FAIL_ON_HIGH_RISK", "true").lower()
    if fail_on_high_risk not in {"true", "false"}:
        print("INPUT_FAIL_ON_HIGH_RISK must be 'true' or 'false'", file=sys.stderr)
        return 1
    return 2 if high_risk and fail_on_high_risk == "true" else 0


if __name__ == "__main__":
    raise SystemExit(main())
