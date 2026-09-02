"""Pre-commit filename runner for rule-audit."""

from __future__ import annotations

import sys

from rule_audit import audit_file


def _audit_path(path: str) -> int:
    """Audit one prompt file and return the stable CLI-style exit status."""
    try:
        report = audit_file(path)
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1
    except IsADirectoryError:
        print(f"error: {path!r} is a directory, expected a text file.", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"error: permission denied reading {path}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print(f"error: {path!r} is not a valid UTF-8 text file.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error during analysis of {path}: {exc}", file=sys.stderr)
        return 1

    print(f"==> {path}")
    print(report.summary())
    if report.risk_label in ("CRITICAL", "HIGH"):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    """Audit every filename supplied by pre-commit."""
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print("error: no prompt files provided", file=sys.stderr)
        return 1

    status = 0
    for path in paths:
        path_status = _audit_path(path)
        if path_status == 1:
            status = 1
        elif path_status == 2 and status == 0:
            status = 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
