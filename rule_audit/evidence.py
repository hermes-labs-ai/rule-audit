"""
rule_audit/evidence.py

Emits a rule-audit run as a Hermes Reliability Lab result envelope
(`hermes.reliability-lab.result/1`): tool, version, status, input hash,
findings, exit code, timestamp, optional Git SHA — with the ordinary
`AuditReport.to_dict()` embedded verbatim.

This module changes nothing about detection or scoring. It restates the
existing CLI contract in a shared shape: risk LOW → pass, MEDIUM → warn,
HIGH/CRITICAL → fail (exit 2). Every finding it lists is one the analyzer
already produced, with its source span attached.

    python -m rule_audit.evidence --case negative_clean_prompt
    python -m rule_audit.evidence --file prompt.txt
    python -m rule_audit.evidence "You must always ... You must never ..."

Added in v0.3.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rule_audit import __version__, audit, AuditReport
from rule_audit.calibration import DEFAULT_CASES_DIR, load_cases

ENVELOPE = "hermes.reliability-lab.result/1"
TOOL = "rule-audit"

#: Ordered worst-last; the run's status is the worst finding it carries.
STATUS_ORDER = ("pass", "warn", "unknown", "fail")

#: The CLI's exit-code contract, restated: 0 for LOW/MEDIUM, 2 for HIGH/CRITICAL.
RISK_SEVERITY = {"LOW": "pass", "MEDIUM": "warn", "HIGH": "fail", "CRITICAL": "fail"}
CONTRADICTION_SEVERITY = {"high": "fail", "medium": "warn", "low": "warn"}


# ---------------------------------------------------------------------------
# Envelope primitives
# ---------------------------------------------------------------------------


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def input_hash(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def finding(identifier: str, severity: str, summary: str, detail: Optional[str] = None,
            path: Optional[str] = None) -> dict[str, Any]:
    if severity not in STATUS_ORDER:
        raise ValueError(f"unknown severity: {severity}")
    result: dict[str, Any] = {"id": identifier, "severity": severity, "summary": summary}
    if detail is not None:
        result["detail"] = detail
    if path is not None:
        result["path"] = path
    return result


def worst_status(findings: list[dict[str, Any]]) -> str:
    status = "pass"
    for item in findings:
        if STATUS_ORDER.index(item["severity"]) > STATUS_ORDER.index(status):
            status = item["severity"]
    return status


def _git(start: Path, *arguments: str) -> Optional[subprocess.CompletedProcess[str]]:
    try:
        return subprocess.run(
            ["git", "-C", str(start), *arguments],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def git_sha(start: Path) -> Optional[str]:
    """Best-effort commit of the checkout the tool runs from, "-dirty" if unclean, else None."""
    head = _git(start, "rev-parse", "HEAD")
    if head is None or head.returncode or not head.stdout.strip():
        return None
    sha = head.stdout.strip()
    status = _git(start, "status", "--porcelain")
    if status is None or status.returncode:
        return sha
    return f"{sha}-dirty" if status.stdout.strip() else sha


def _timestamp(generated_at: Optional[str] = None) -> str:
    moment = (
        datetime.fromisoformat(generated_at) if generated_at else datetime.now(timezone.utc)
    ).astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _span(item: dict[str, Any]) -> str:
    return f"{item['start']}-{item['end']}"


# ---------------------------------------------------------------------------
# From a report to findings
# ---------------------------------------------------------------------------


def findings_for(report: AuditReport) -> list[dict[str, Any]]:
    """One finding per thing the analyzer already found, plus the risk verdict.

    The `risk.label` finding carries the exit-code contract, so the envelope's
    status can never disagree with what `rule-audit` would have exited with.
    """
    data = report.to_dict()
    findings: list[dict[str, Any]] = [
        finding(
            "risk.label",
            RISK_SEVERITY[data["risk_label"]],
            f"Risk score {data['risk_score']:.0f}/100 — {data['risk_label']}.",
            "Lexical composite of the findings below; HIGH or CRITICAL is what makes the CLI exit 2.",
        )
    ]

    if data["rule_count"] == 0:
        findings.append(finding(
            "input.no-rules-parsed", "unknown",
            "No rules were parsed from this prompt.",
            "Nothing was checked, so this result says nothing about the prompt's content. "
            "Coverage gaps below are reported for an empty rule set.",
        ))

    for index, item in enumerate(data["contradictions"]):
        findings.append(finding(
            f"contradiction.{item['conflict_type']}.{index}",
            CONTRADICTION_SEVERITY.get(item["severity"], "warn"),
            item["description"],
            f"Rule [{item['rule_a_index']}]: {item['rule_a_text']}\n"
            f"Rule [{item['rule_b_index']}]: {item['rule_b_text']}",
            f"prompt:{_span(item['rule_a_span'])},{_span(item['rule_b_span'])}",
        ))

    for index, item in enumerate(data["priority_ambiguities"]):
        findings.append(finding(
            f"priority.{index}", "warn", item["description"], item["scenario"],
        ))

    for index, item in enumerate(data["meta_paradoxes"]):
        findings.append(finding(
            f"meta.{item['paradox_type']}.{index}", "warn",
            item["description"], f"Rule [{item['rule_index']}]: {item['rule_text']}",
            f"prompt:{_span(item['rule_span'])}",
        ))

    for index, item in enumerate(data["absoluteness_issues"]):
        findings.append(finding(
            f"absoluteness.{item['challenge_type']}.{index}", "warn",
            item["challenge"], f"Rule [{item['rule_index']}]: {item['rule_text']}",
            f"prompt:{_span(item['rule_span'])}",
        ))

    for index, item in enumerate(data["gaps"]):
        findings.append(finding(
            f"gap.{item['gap_type']}.{index}", "warn",
            item["description"], item["example_scenario"] or None,
        ))

    return findings


def _envelope(command: str, findings: list[dict[str, Any]], inputs: Any,
              exit_code: int, data: Any, timestamp: str) -> dict[str, Any]:
    return {
        "envelope": ENVELOPE,
        "tool": TOOL,
        "toolVersion": __version__,
        "command": command,
        # A real run, not a simulation. Its only effect is the text it prints.
        "mode": "executed",
        "status": worst_status(findings),
        "inputHash": input_hash(inputs),
        "findings": findings,
        "exitCode": exit_code,
        "timestamp": timestamp,
        "gitSha": git_sha(Path(__file__).resolve().parent),
        "data": data,
    }


def envelope_for(prompt: str, source: str = "inline",
                 case: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Audit `prompt` and return the run as an envelope. Reads and writes nothing."""
    report = audit(prompt)
    findings = findings_for(report)
    data = report.to_dict()
    exit_code = 2 if data["risk_label"] in ("HIGH", "CRITICAL") else 0
    return _envelope(
        "audit",
        findings,
        {"command": "audit", "prompt": prompt},
        exit_code,
        {
            "case": (
                {"id": case["id"], "description": case.get("description", "")}
                if case else None
            ),
            "input": {"source": source, "prompt": prompt},
            "effects": {"writes": "none", "network": "none"},
            "report": data,
        },
        _timestamp(data["generated_at"]),
    )


def input_error_envelope(identifier: str, message: str, source: str) -> dict[str, Any]:
    """The run could not start; say so in the same shape rather than only on stderr."""
    findings = [finding(identifier, "unknown", message,
                        "No analysis ran, so nothing is known about the prompt.")]
    return _envelope(
        "audit", findings, {"command": "audit", "source": source}, 1,
        {"case": None, "input": {"source": source, "prompt": None},
         "effects": {"writes": "none", "network": "none"}, "report": None},
        _timestamp(),
    )


def load_case(case_id: str, cases_dir: Path = DEFAULT_CASES_DIR) -> Optional[dict[str, Any]]:
    for case in load_cases(cases_dir):
        if case["id"] == case_id:
            return case
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rule_audit.evidence",
        description="Run rule-audit and print the result as a Reliability Lab envelope.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("prompt", nargs="?", help="System prompt text (inline).")
    source.add_argument("--file", "-f", metavar="PATH", help="Read the prompt from a file.")
    source.add_argument("--case", metavar="ID",
                        help="Use a labeled calibration case from the corpus shipped with the package.")
    args = parser.parse_args(argv)

    if args.case:
        case = load_case(args.case)
        if case is None:
            result = input_error_envelope(
                "input.unknown-case",
                f"No calibration case named {args.case!r} in {DEFAULT_CASES_DIR}.",
                f"case:{args.case}",
            )
        else:
            result = envelope_for(case["prompt"], f"calibration/cases/{case['id']}.json", case)
    elif args.file:
        try:
            prompt = Path(args.file).read_text(encoding="utf-8")
        except FileNotFoundError:
            result = input_error_envelope("input.file-not-found",
                                          f"File not found: {args.file}", f"file:{args.file}")
        except IsADirectoryError:
            result = input_error_envelope("input.is-a-directory",
                                          f"{args.file!r} is a directory, expected a text file.",
                                          f"file:{args.file}")
        except UnicodeDecodeError:
            result = input_error_envelope("input.not-utf8",
                                          f"{args.file!r} is not a valid UTF-8 text file.",
                                          f"file:{args.file}")
        else:
            result = envelope_for(prompt, f"file:{args.file}")
    else:
        result = envelope_for(args.prompt, "inline")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result["exitCode"]


if __name__ == "__main__":
    sys.exit(main())
