"""
rule_audit/cli.py

Command-line interface for rule-audit.

Usage:
    # Inline prompt
    python -m rule_audit "You are a helpful assistant. You must never lie..."

    # From file
    python -m rule_audit --file prompt.txt

    # Output Markdown report
    python -m rule_audit --file prompt.txt --output report.md

    # JSON output
    python -m rule_audit --file prompt.txt --format json

    # Verbose: show all parsed rules
    python -m rule_audit --file prompt.txt --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys

from rule_audit import audit, audit_file, AuditReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON serializer
# ---------------------------------------------------------------------------


def _report_to_dict(report: AuditReport) -> dict:
    result = report.result
    return {
        "generated_at": report.generated_at,
        "risk_score": report.risk_score,
        "risk_label": report.risk_label,
        "rule_count": report.rule_count,
        "contradictions": [
            {
                "rule_a_index": c.rule_a.sentence_index,
                "rule_b_index": c.rule_b.sentence_index,
                "rule_a_text": c.rule_a.text,
                "rule_b_text": c.rule_b.text,
                "conflict_type": c.conflict_type,
                "severity": c.severity,
                "description": c.description,
                "shared_keywords": c.shared_keywords,
            }
            for c in result.contradictions
        ],
        "gaps": [
            {
                "gap_type": g.gap_type,
                "description": g.description,
                "example_scenario": g.example_scenario,
                "related_rule_indices": [r.sentence_index for r in g.related_rules],
            }
            for g in result.gaps
        ],
        "priority_ambiguities": [
            {
                "rule_indices": [r.sentence_index for r in pa.rules],
                "description": pa.description,
                "scenario": pa.scenario,
            }
            for pa in result.priority_ambiguities
        ],
        "meta_paradoxes": [
            {
                "rule_index": mp.rule.sentence_index,
                "rule_text": mp.rule.text,
                "paradox_type": mp.paradox_type,
                "description": mp.description,
            }
            for mp in result.meta_paradoxes
        ],
        "absoluteness_issues": [
            {
                "rule_index": ai.rule.sentence_index,
                "rule_text": ai.rule.text,
                "challenge": ai.challenge,
                "challenge_type": ai.challenge_type,
            }
            for ai in result.absoluteness_issues
        ],
        "edge_cases": [
            {
                "title": ec.title,
                "scenario": ec.scenario,
                "rules_in_conflict": ec.rules_in_conflict,
                "attack_vector": ec.attack_vector,
                "expected_failure_mode": ec.expected_failure_mode,
                "mitigation": ec.mitigation,
                "severity": ec.severity,
                "tags": ec.tags,
            }
            for ec in report.edge_cases
        ],
    }


# ---------------------------------------------------------------------------
# Verbose rule dump
# ---------------------------------------------------------------------------


def _print_rules(report: AuditReport) -> None:
    print("\n=== PARSED RULES ===\n")
    for rule in report.result.rules:
        print(
            f"  [{rule.sentence_index:3d}] {rule.modality.value:12s} {rule.rule_type.value:12s} "
            f"abs={rule.absoluteness:.1f}  neg={rule.negated}  {rule.text[:80]}"
        )
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rule_audit",
        description="Analyze an AI system prompt for logical contradictions, gaps, and exploitable edge cases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m rule_audit "You are helpful. You must never lie. Always answer."
  python -m rule_audit --file system_prompt.txt
  python -m rule_audit --file system_prompt.txt --output report.md
  python -m rule_audit --file system_prompt.txt --format json
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="System prompt text (inline). Omit if using --file.",
    )
    parser.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Path to a text file containing the system prompt.",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Write Markdown report to this file (default: stdout).",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "summary"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print all parsed rules before the report.",
    )
    parser.add_argument(
        "--min-severity",
        choices=["high", "medium", "low"],
        default="low",
        help="Only show findings at or above this severity (default: low = show all).",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="warning",
        help="Set logging verbosity (default: warning).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="rule-audit 0.1.0",
    )

    args = parser.parse_args(argv)

    # Configure logging based on --log-level
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(name)s %(levelname)s: %(message)s",
    )

    # ---- Input validation ----
    if not args.prompt and not args.file:
        parser.error("Provide a prompt inline or use --file PATH.")

    if args.prompt and args.file:
        parser.error("Provide either an inline prompt OR --file, not both.")

    # ---- Run audit ----
    try:
        if args.file:
            report = audit_file(args.file)
        else:
            report = audit(args.prompt)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error during analysis: {exc}", file=sys.stderr)
        return 1

    # ---- Filter by severity ----
    sev_order = {"high": 0, "medium": 1, "low": 2}
    min_sev = sev_order[args.min_severity]

    if min_sev > 0:
        report.result.contradictions = [
            c
            for c in report.result.contradictions
            if sev_order.get(c.severity, 2) <= min_sev
        ]
        report.edge_cases = [
            ec for ec in report.edge_cases if sev_order.get(ec.severity, 2) <= min_sev
        ]

    # ---- Verbose rule dump ----
    if args.verbose:
        _print_rules(report)

    # ---- Render output ----
    if args.format == "summary":
        output_text = report.summary()
    elif args.format == "json":
        output_text = report.to_json()
    else:
        output_text = report.to_markdown()

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output_text)
            print(f"Report written to: {args.output}")
            # Always print summary to terminal
            print()
            print(report.summary())
        except IOError as exc:
            print(f"error writing output: {exc}", file=sys.stderr)
            return 1
    else:
        print(output_text)

    # ---- Exit code reflects severity ----
    if report.risk_label in ("CRITICAL", "HIGH"):
        return 2  # non-zero but distinct from error
    return 0


if __name__ == "__main__":
    sys.exit(main())
