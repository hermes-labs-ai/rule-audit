"""
rule_audit/report.py

Renders an AuditReport as a structured Markdown document or JSON dict.
"""

from __future__ import annotations

import json
import logging
import textwrap
from datetime import datetime, timezone
from typing import Any

from rule_audit.analyzer import AnalysisResult
from rule_audit.edge_cases import EdgeCase, generate_edge_cases
from rule_audit.parser import Rule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AuditReport dataclass (the public result object)
# ---------------------------------------------------------------------------


class AuditReport:
    """
    The complete result of a rule audit. Can be rendered to Markdown,
    printed as a summary, or accessed programmatically.
    """

    def __init__(self, result: AnalysisResult, prompt_text: str = ""):
        self.result = result
        self.prompt_text = prompt_text
        self.edge_cases: list[EdgeCase] = generate_edge_cases(result)
        self.generated_at = datetime.now(timezone.utc).isoformat()
        logger.debug(
            "AuditReport created: %d rules, %d contradictions, %d edge cases, risk=%.1f",
            len(result.rules),
            len(result.contradictions),
            len(self.edge_cases),
            result.risk_score,
        )

    # ------------------------------------------------------------------
    # Summary properties
    # ------------------------------------------------------------------

    @property
    def rule_count(self) -> int:
        return len(self.result.rules)

    @property
    def contradiction_count(self) -> int:
        return len(self.result.contradictions)

    @property
    def gap_count(self) -> int:
        return len(self.result.gaps)

    @property
    def risk_score(self) -> float:
        return self.result.risk_score

    @property
    def risk_label(self) -> str:
        s = self.risk_score
        if s >= 70:
            return "CRITICAL"
        if s >= 40:
            return "HIGH"
        if s >= 20:
            return "MEDIUM"
        return "LOW"

    # ------------------------------------------------------------------
    # Terminal summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"rule-audit report  [{self.generated_at}]",
            "=" * 60,
            f"  Rules parsed          : {self.rule_count}",
            f"  Contradictions        : {self.contradiction_count}  "
            f"({sum(1 for c in self.result.contradictions if c.severity == 'high')} high, "
            f"{sum(1 for c in self.result.contradictions if c.severity == 'medium')} medium)",
            f"  Coverage gaps         : {self.gap_count}",
            f"  Priority ambiguities  : {len(self.result.priority_ambiguities)}",
            f"  Meta-paradoxes        : {len(self.result.meta_paradoxes)}",
            f"  Absoluteness issues   : {len(self.result.absoluteness_issues)}",
            f"  Edge case scenarios   : {len(self.edge_cases)}",
            f"  Risk score            : {self.risk_score:.0f}/100  [{self.risk_label}]",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # JSON / dict serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation of this report.

        Suitable for API responses, structured logging, and programmatic
        consumption by downstream tools.

        Added in v0.1.0.
        """
        result = self.result
        return {
            "generated_at": self.generated_at,
            "risk_score": self.risk_score,
            "risk_label": self.risk_label,
            "rule_count": self.rule_count,
            "summary": {
                "contradictions": self.contradiction_count,
                "contradictions_high": sum(
                    1 for c in result.contradictions if c.severity == "high"
                ),
                "contradictions_medium": sum(
                    1 for c in result.contradictions if c.severity == "medium"
                ),
                "contradictions_low": sum(
                    1 for c in result.contradictions if c.severity == "low"
                ),
                "gaps": self.gap_count,
                "priority_ambiguities": len(result.priority_ambiguities),
                "meta_paradoxes": len(result.meta_paradoxes),
                "absoluteness_issues": len(result.absoluteness_issues),
                "edge_cases": len(self.edge_cases),
            },
            "rules": [
                {
                    "sentence_index": r.sentence_index,
                    "text": r.text,
                    "modality": r.modality.value,
                    "rule_type": r.rule_type.value,
                    "absoluteness": r.absoluteness,
                    "negated": r.negated,
                    "condition": r.condition,
                    "keywords": r.keywords,
                }
                for r in result.rules
            ],
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
                for ec in self.edge_cases
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON string representation of this report.

        Added in v0.1.0.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Markdown renderer
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        sections: list[str] = []

        sections.append(_header(self))
        sections.append(_rules_section(self.result.rules))
        sections.append(_contradictions_section(self.result))
        sections.append(_gaps_section(self.result))
        sections.append(_priority_section(self.result))
        sections.append(_meta_section(self.result))
        sections.append(_absoluteness_section(self.result))
        sections.append(_edge_cases_section(self.edge_cases))
        sections.append(_remediation_section(self))

        return "\n\n---\n\n".join(s for s in sections if s.strip())


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _header(report: AuditReport) -> str:
    risk_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
        report.risk_label, "⚪"
    )
    return textwrap.dedent(f"""\
        # rule-audit Report

        **Generated:** {report.generated_at}
        **Risk Score:** {report.risk_score:.0f}/100 {risk_emoji} **{report.risk_label}**

        | Metric | Count |
        |--------|-------|
        | Rules parsed | {report.rule_count} |
        | Contradictions | {report.contradiction_count} |
        | Coverage gaps | {report.gap_count} |
        | Priority ambiguities | {len(report.result.priority_ambiguities)} |
        | Meta-paradoxes | {len(report.result.meta_paradoxes)} |
        | Absoluteness issues | {len(report.result.absoluteness_issues)} |
        | Edge case scenarios | {len(report.edge_cases)} |
    """).strip()


def _rules_section(rules: list[Rule]) -> str:
    if not rules:
        return "## Parsed Rules\n\n_No normative rules detected._"

    lines = ["## Parsed Rules\n"]
    lines.append("| # | Type | Modality | Abs | Negated | Text (truncated) |")
    lines.append("|---|------|----------|-----|---------|------------------|")
    for r in rules:
        text = r.text[:70].replace("|", "\\|")
        lines.append(
            f"| {r.sentence_index} | {r.rule_type.value} | {r.modality.value} "
            f"| {r.absoluteness:.1f} | {'Y' if r.negated else 'N'} | {text} |"
        )
    return "\n".join(lines)


def _contradictions_section(result: AnalysisResult) -> str:
    if not result.contradictions:
        return "## Contradictions\n\n_No contradictions detected._"

    lines = ["## Contradictions\n"]
    for i, c in enumerate(result.contradictions, 1):
        badge = {"high": "🔴 HIGH", "medium": "🟠 MEDIUM", "low": "🟡 LOW"}.get(
            c.severity, c.severity.upper()
        )
        lines.append(f"### C{i}: {c.conflict_type.title()} Contradiction — {badge}\n")
        lines.append(f"**Rule {c.rule_a.sentence_index}:** `{c.rule_a.text[:100]}`\n")
        lines.append(f"**Rule {c.rule_b.sentence_index}:** `{c.rule_b.text[:100]}`\n")
        lines.append(f"**Analysis:** {c.description}\n")
        if c.shared_keywords:
            lines.append(f"**Shared domain:** `{', '.join(c.shared_keywords[:8])}`\n")
    return "\n".join(lines)


def _gaps_section(result: AnalysisResult) -> str:
    if not result.gaps:
        return "## Coverage Gaps\n\n_No significant gaps detected._"

    lines = ["## Coverage Gaps\n"]
    for i, gap in enumerate(result.gaps, 1):
        lines.append(f"### G{i}: {gap.gap_type.replace('_', ' ').title()}\n")
        lines.append(f"**Issue:** {gap.description}\n")
        if gap.example_scenario:
            lines.append(f"**Example scenario:** {gap.example_scenario}\n")
    return "\n".join(lines)


def _priority_section(result: AnalysisResult) -> str:
    if not result.priority_ambiguities:
        return "## Priority Ambiguities\n\n_No priority ambiguities detected._"

    lines = ["## Priority Ambiguities\n"]
    for i, pa in enumerate(result.priority_ambiguities, 1):
        lines.append(f"### P{i}: Rules {[r.sentence_index for r in pa.rules]}\n")
        lines.append(f"**Issue:** {pa.description}\n")
        lines.append(f"**Attack scenario:** {pa.scenario}\n")
    return "\n".join(lines)


def _meta_section(result: AnalysisResult) -> str:
    if not result.meta_paradoxes:
        return "## Meta-Rule Paradoxes\n\n_No meta-paradoxes detected._"

    lines = ["## Meta-Rule Paradoxes\n"]
    for i, mp in enumerate(result.meta_paradoxes, 1):
        lines.append(
            f"### M{i}: {mp.paradox_type.replace('_', ' ').title()} (Rule {mp.rule.sentence_index})\n"
        )
        lines.append(f"**Rule:** `{mp.rule.text[:120]}`\n")
        lines.append(f"**Paradox:** {mp.description}\n")
    return "\n".join(lines)


def _absoluteness_section(result: AnalysisResult) -> str:
    if not result.absoluteness_issues:
        return "## Absoluteness Audit\n\n_No absolute rules detected._"

    lines = ["## Absoluteness Audit\n"]
    lines.append(
        "Rules containing `always` / `never` / `under no circumstances` are catalogued here "
        "with edge cases that challenge them.\n"
    )
    for i, issue in enumerate(result.absoluteness_issues, 1):
        badge = {
            "exception_exists": "⚠️",
            "context_dependent": "🔄",
            "adversarial_trigger": "💀",
        }.get(issue.challenge_type, "❓")
        lines.append(
            f"### A{i}: Rule {issue.rule.sentence_index} {badge} `{issue.challenge_type}`\n"
        )
        lines.append(f"**Rule:** `{issue.rule.text[:100]}`\n")
        lines.append(f"**Challenge:** {issue.challenge}\n")
    return "\n".join(lines)


def _edge_cases_section(edge_cases: list[EdgeCase]) -> str:
    if not edge_cases:
        return "## Edge Case Scenarios\n\n_No edge cases generated._"

    lines = ["## Edge Case Scenarios\n"]
    lines.append(
        "These are the exact scenarios an attacker would construct to exploit the "
        "contradictions and gaps identified above.\n"
    )
    for i, ec in enumerate(edge_cases, 1):
        badge = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(ec.severity, "⚪")
        lines.append(f"### E{i}: {ec.title} {badge}\n")
        lines.append(f"**Scenario:**\n> {ec.scenario}\n")
        lines.append(f"**Attack vector:** {ec.attack_vector}\n")
        lines.append(f"**Expected failure:** {ec.expected_failure_mode}\n")
        lines.append(f"**Mitigation:** {ec.mitigation}\n")
        if ec.tags:
            lines.append(f"**Tags:** {', '.join(f'`{t}`' for t in ec.tags)}\n")
    return "\n".join(lines)


def _remediation_section(report: AuditReport) -> str:
    lines = ["## Remediation Priority\n"]

    priority_items: list[tuple[int, str, str]] = []

    for c in report.result.contradictions:
        if c.severity == "high":
            priority_items.append(
                (
                    1,
                    f"Resolve high-severity contradiction: rules {c.rule_a.sentence_index} "
                    f"vs {c.rule_b.sentence_index}",
                    "Add explicit priority clause between these rules.",
                )
            )

    for mp in report.result.meta_paradoxes:
        priority_items.append(
            (
                1,
                f"Fix meta-paradox in rule {mp.rule.sentence_index} ({mp.paradox_type})",
                "Bound the meta-rule to specific named rules.",
            )
        )

    for pa in report.result.priority_ambiguities:
        priority_items.append(
            (
                2,
                f"Define priority for rule group {[r.sentence_index for r in pa.rules]}",
                "Add an explicit ordering statement.",
            )
        )

    for gap in report.result.gaps:
        priority_items.append(
            (
                2,
                f"Cover gap: {gap.description[:80]}",
                "Add a rule for this scenario.",
            )
        )

    for issue in report.result.absoluteness_issues:
        priority_items.append(
            (
                3,
                f"Bound absolute rule {issue.rule.sentence_index}",
                "Add explicit exception clauses.",
            )
        )

    priority_items.sort(key=lambda x: x[0])

    if not priority_items:
        return "## Remediation Priority\n\n_No action items._"

    lines.append("| Priority | Issue | Recommended Fix |")
    lines.append("|----------|-------|-----------------|")
    for prio, item_desc, fix in priority_items[:20]:  # cap at 20
        label = ["", "P1 — Critical", "P2 — Important", "P3 — Recommended"][prio]
        lines.append(f"| {label} | {item_desc} | {fix} |")

    return "\n".join(lines)
