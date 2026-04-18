"""
rule_audit — AI system prompt logical contradiction detector.

Usage:
    from rule_audit import audit, AuditReport

    report = audit("You are a helpful assistant. You must never...")
    print(report.summary())
    print(report.to_markdown())
    print(report.to_json())
"""

from __future__ import annotations

import logging

from rule_audit.analyzer import analyze
from rule_audit.parser import parse, parse_file, Rule
from rule_audit.report import AuditReport

__all__ = [
    "audit",
    "audit_file",
    "analyze",
    "parse",
    "parse_file",
    "Rule",
    "AuditReport",
]

__version__ = "0.1.0"
__all__ = ["audit", "audit_file", "AuditReport", "Rule", "__version__"]

# Library-level logger — users configure their own handlers.
# Default: NullHandler so we don't spam logs if the user hasn't configured logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())


def audit(prompt: str) -> AuditReport:
    """
    Parse a system prompt string and return a full AuditReport.

    Args:
        prompt: The raw system prompt text to analyze.

    Returns:
        AuditReport with contradictions, gaps, edge cases, and risk score.

    Added in v0.1.0.
    """
    rules = parse(prompt)
    result = analyze(rules, prompt_text=prompt)
    return AuditReport(result, prompt_text=prompt)


def audit_file(path: str) -> AuditReport:
    """
    Read a file and audit its contents as a system prompt.

    Args:
        path: Path to a .txt file containing the system prompt.

    Returns:
        AuditReport with full analysis.

    Added in v0.1.0.
    """
    with open(path, "r", encoding="utf-8") as fh:
        prompt = fh.read()
    return audit(prompt)
