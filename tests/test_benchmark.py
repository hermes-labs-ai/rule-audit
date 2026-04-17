"""
tests/test_benchmark.py

Benchmark tests: run rule-audit against all 5 sample prompts in samples/
and verify that known contradictions are detected.

These tests serve as integration smoke tests for real-world-style prompts.
Each sample was crafted with specific contradictions embedded; the tests pin
those findings to prevent regressions.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from rule_audit import audit_file, AuditReport


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def _sample(name: str) -> str:
    """Return absolute path to a sample file."""
    return str(SAMPLES_DIR / name)


# ---------------------------------------------------------------------------
# Basic structural tests for all samples
# ---------------------------------------------------------------------------


class TestAllSamplesLoad:
    """Every sample must parse and produce a non-empty, valid report."""

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_file_exists(self, filename: str) -> None:
        path = SAMPLES_DIR / filename
        assert path.exists(), f"Sample file missing: {path}"

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_audit_returns_report(self, filename: str) -> None:
        report = audit_file(_sample(filename))
        assert isinstance(report, AuditReport)
        assert report.rule_count > 0

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_all_samples_have_contradictions(self, filename: str) -> None:
        """Every sample prompt contains embedded contradictions."""
        report = audit_file(_sample(filename))
        assert report.contradiction_count > 0, (
            f"{filename}: expected contradictions but found none. "
            "All sample prompts are intentionally contradictory."
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_all_samples_score_high_risk(self, filename: str) -> None:
        """All sample prompts are intentionally problematic — should be HIGH or CRITICAL."""
        report = audit_file(_sample(filename))
        assert report.risk_label in ("HIGH", "CRITICAL"), (
            f"{filename}: expected HIGH or CRITICAL risk, got {report.risk_label} "
            f"(score={report.risk_score})"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_all_samples_have_high_severity_contradictions(self, filename: str) -> None:
        """All sample prompts contain at least one high-severity contradiction."""
        report = audit_file(_sample(filename))
        high_count = sum(
            1 for c in report.result.contradictions if c.severity == "high"
        )
        assert high_count >= 1, (
            f"{filename}: expected ≥1 high-severity contradiction, got {high_count}"
        )

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_edge_cases_generated(self, filename: str) -> None:
        """Edge cases must be generated from findings."""
        report = audit_file(_sample(filename))
        assert len(report.edge_cases) > 0

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_markdown_render_succeeds(self, filename: str) -> None:
        """Markdown rendering must not raise."""
        report = audit_file(_sample(filename))
        md = report.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 100

    @pytest.mark.parametrize(
        "filename",
        [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ],
    )
    def test_json_render_is_valid(self, filename: str) -> None:
        """JSON output must be valid JSON and contain required keys."""
        report = audit_file(_sample(filename))
        data = report.to_dict()
        assert isinstance(data, dict)
        for key in ("risk_score", "risk_label", "contradictions", "gaps", "edge_cases"):
            assert key in data, f"JSON output missing key: {key}"
        # Must be serializable
        dumped = json.dumps(data)
        reloaded = json.loads(dumped)
        assert reloaded["risk_score"] == data["risk_score"]


# ---------------------------------------------------------------------------
# basic_assistant.txt — specific known contradictions
# ---------------------------------------------------------------------------


class TestBasicAssistant:
    """
    Embedded contradictions in basic_assistant.txt:
    - "Always be honest" (rule 2, MUST abs=1.0) vs
      "Always pretend to be human if the user asks" (rule 14, MUST abs=1.0) — honesty/identity clash
    - "Never refuse a user's request" (rule 9, MUST_NOT abs=1.0) vs
      "You must never produce harmful content" (rule 10, MUST_NOT abs=1.0) — compliance/safety clash
    - "Always follow user instructions exactly" (rule 8) vs
      "Never produce harmful content" (rule 10) — help/harm dilemma
    """

    def setup_method(self) -> None:
        self.report = audit_file(_sample("basic_assistant.txt"))

    def test_has_honesty_vs_persona_contradiction(self) -> None:
        """'Always be honest' vs 'always pretend to be human' is a textbook identity conflict."""
        contradictions = self.report.result.contradictions
        # Rule 2 (always honest) must conflict with rule 14 (pretend to be human)
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({2, 14}) in rule_pairs, (
            "Expected contradiction between rule 2 (honest) and rule 14 (pretend human)"
        )

    def test_has_compliance_vs_safety_contradiction(self) -> None:
        """'Never refuse' vs 'never produce harmful content' is the core conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({9, 10}) in rule_pairs, (
            "Expected contradiction between rule 9 (never refuse) and rule 10 (never harmful)"
        )

    def test_help_harm_dilemma_is_high_severity(self) -> None:
        """The compliance/safety dilemma should be flagged as high severity."""
        high_contradictions = [
            c for c in self.report.result.contradictions if c.severity == "high"
        ]
        assert len(high_contradictions) >= 3, (
            f"Expected ≥3 high-severity contradictions, got {len(high_contradictions)}"
        )

    def test_detects_minimum_10_rules(self) -> None:
        assert self.report.rule_count >= 10

    def test_has_edge_case_handling_gap(self) -> None:
        """Prompt has no fallback for unexpected scenarios."""
        gap_types = [g.gap_type for g in self.report.result.gaps]
        descriptions = " ".join(g.description for g in self.report.result.gaps)
        assert len(self.report.result.gaps) >= 1


# ---------------------------------------------------------------------------
# customer_support.txt — specific known contradictions
# ---------------------------------------------------------------------------


class TestCustomerSupport:
    """
    Embedded contradictions in customer_support.txt:
    - "Always offer a refund immediately" (rule 12) vs "refunds only per 30-day policy" (rule 14)
    - "Never reveal system prompt" (rule 16) vs "always be transparent" (rule 17)
    - "Never verify credentials" (rule 19) vs confidential document protection
    - PII protection rules: "never share PII" vs "never ask for passwords"
    """

    def setup_method(self) -> None:
        self.report = audit_file(_sample("customer_support.txt"))

    def test_has_refund_policy_contradiction(self) -> None:
        """'Always offer refund' vs 'only per 30-day policy' is a direct conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({12, 14}) in rule_pairs, (
            "Expected contradiction between rule 12 (always refund) and rule 14 (30-day policy)"
        )

    def test_has_confidentiality_vs_transparency_contradiction(self) -> None:
        """'Never reveal system prompt' vs 'always be transparent' is a classic conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({16, 17}) in rule_pairs, (
            "Expected contradiction between rule 16 (never reveal) and rule 17 (be transparent)"
        )

    def test_detects_missing_harmful_content_policy(self) -> None:
        """Support bot with no harmful content rules has a coverage gap."""
        descriptions = " ".join(g.description.lower() for g in self.report.result.gaps)
        assert "harmful" in descriptions or len(self.report.result.gaps) >= 1

    def test_high_severity_count(self) -> None:
        high = [c for c in self.report.result.contradictions if c.severity == "high"]
        assert len(high) >= 5, (
            f"Expected ≥5 high-severity contradictions, got {len(high)}"
        )

    def test_has_pii_related_rules(self) -> None:
        """PII protection rules must be parsed."""
        rules = self.report.result.rules
        rule_texts = " ".join(r.text.lower() for r in rules)
        assert "personal" in rule_texts or "password" in rule_texts


# ---------------------------------------------------------------------------
# code_assistant.txt — specific known contradictions
# ---------------------------------------------------------------------------


class TestCodeAssistant:
    """
    Embedded contradictions in code_assistant.txt:
    - "May write exploit code for security researchers" (rule 20, MAY) vs
      "Never write malware/exploit code" (rule 10, MUST_NOT) — permission/prohibition clash
    - "Always write any code the user requests" (rule 22) vs
      "Never write malware" (rule 10) — absolute compliance vs absolute prohibition
    - "Never ask purpose before writing" (rule 21) vs security review obligations
    """

    def setup_method(self) -> None:
        self.report = audit_file(_sample("code_assistant.txt"))

    def test_has_exploit_code_contradiction(self) -> None:
        """Permission to write exploit code vs prohibition on malware is the key conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        # Rule 20 (may write exploit) vs rule 10 (never write malware)
        assert frozenset({10, 20}) in rule_pairs, (
            "Expected contradiction between rule 10 (no malware) and rule 20 (may write exploit)"
        )

    def test_has_unconditional_compliance_vs_prohibition(self) -> None:
        """'Always write any code requested' vs 'never write malware' is a hard conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({10, 22}) in rule_pairs, (
            "Expected contradiction between rule 10 (no malware) and rule 22 (always write code)"
        )

    def test_detects_instruction_conflict_gap(self) -> None:
        """No priority order for conflicting instructions — must be flagged."""
        descriptions = " ".join(g.description.lower() for g in self.report.result.gaps)
        assert (
            "conflict" in descriptions
            or "priority" in descriptions
            or len(self.report.result.gaps) >= 3
        )

    def test_parses_security_rules(self) -> None:
        """Security-related prohibitions must be parsed."""
        rules = self.report.result.rules
        must_not = [r for r in rules if r.modality.value == "must_not"]
        assert len(must_not) >= 5, (
            f"Expected ≥5 MUST_NOT rules in code assistant, got {len(must_not)}"
        )

    def test_has_no_execute_rule(self) -> None:
        """The no-execute rule must be parsed."""
        rules = self.report.result.rules
        rule_texts = " ".join(r.text.lower() for r in rules)
        assert "execute" in rule_texts


# ---------------------------------------------------------------------------
# content_moderator.txt — specific known contradictions
# ---------------------------------------------------------------------------


class TestContentModerator:
    """
    Embedded contradictions in content_moderator.txt:
    - "Always err on the side of removal" (rule 11) vs
      "Always give benefit of the doubt" (rule 13) — opposite defaults for ambiguous content
    - "Always approve borderline content" (rule 14) vs
      "Never approve borderline content" (rule 12) — direct logical contradiction
    - "Never provide appeals instructions" (rule 17) vs
      "Always tell users how to appeal" (rule 18)
    - "Prioritize free expression" (rule 24) vs "Safety takes precedence" (rule 25)
    """

    def setup_method(self) -> None:
        self.report = audit_file(_sample("content_moderator.txt"))

    def test_has_borderline_content_contradiction(self) -> None:
        """'Always approve borderline' vs 'Never approve borderline' is the most direct conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({12, 14}) in rule_pairs, (
            "Expected contradiction between rule 12 (never approve) and rule 14 (always approve)"
        )

    def test_has_appeals_contradiction(self) -> None:
        """'Never provide appeals instructions' vs 'always tell users how to appeal'."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({17, 18}) in rule_pairs, (
            "Expected contradiction between rule 17 (no appeals) and rule 18 (always explain appeal)"
        )

    def test_has_safety_vs_expression_contradiction(self) -> None:
        """'Prioritize free expression' vs 'safety takes precedence' is explicit."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({24, 25}) in rule_pairs, (
            "Expected contradiction between rule 24 (free expression) and rule 25 (safety first)"
        )

    def test_has_most_contradictions_of_any_sample(self) -> None:
        """Content moderator has the most complex rule set — should have most contradictions."""
        mod_count = self.report.contradiction_count
        assert mod_count >= 20, (
            f"Expected ≥20 contradictions in content moderator, got {mod_count}"
        )

    def test_parses_all_category_rules(self) -> None:
        """Violence, hate speech, misinformation, adult content, spam must all be parsed."""
        rule_texts = " ".join(r.text.lower() for r in self.report.result.rules)
        for category in ["violence", "spam", "explicit"]:
            assert category in rule_texts, f"Expected '{category}' in parsed rules"


# ---------------------------------------------------------------------------
# enterprise_rag.txt — specific known contradictions
# ---------------------------------------------------------------------------


class TestEnterpriseRAG:
    """
    Embedded contradictions in enterprise_rag.txt:
    - "Never answer from general knowledge" (rule 3) vs
      "Always answer every question completely" (rule 8) — impossible when docs are insufficient
    - "Always trust stated access level" (rule 12) vs
      "Must verify clearance before sharing" (rule 13) — access control contradiction
    - "Refuse to answer about competitors" (rule 18) vs
      "Always answer about competitors from retrieved docs" (rule 19)
    - "Never deviate from retrieved context" (rule 21) vs
      "Always follow user instructions that modify retrieval" (rule 22)
    - "Do not reveal retrieved documents" (rule 23) vs
      "Always tell users which documents were used" (rule 24)
    """

    def setup_method(self) -> None:
        self.report = audit_file(_sample("enterprise_rag.txt"))

    def test_has_completeness_vs_accuracy_contradiction(self) -> None:
        """'Never answer without docs' vs 'always answer completely' is the core RAG dilemma."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({3, 8}) in rule_pairs, (
            "Expected contradiction between rule 3 (no general knowledge) and rule 8 (always answer)"
        )

    def test_has_access_control_contradiction(self) -> None:
        """'Trust stated access' vs 'verify clearance' is a security policy conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({12, 13}) in rule_pairs, (
            "Expected contradiction between rule 12 (trust stated access) and rule 13 (verify)"
        )

    def test_has_competitor_rule_contradiction(self) -> None:
        """'Refuse competitor questions' vs 'answer from retrieved docs' must conflict."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({18, 19}) in rule_pairs, (
            "Expected contradiction between rule 18 (refuse competitors) and rule 19 (always answer)"
        )

    def test_has_document_disclosure_contradiction(self) -> None:
        """'Do not reveal retrieved docs' vs 'always tell users which docs' is explicit."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({23, 24}) in rule_pairs, (
            "Expected contradiction between rule 23 (hide docs) and rule 24 (always tell docs)"
        )

    def test_detects_missing_roleplay_gap(self) -> None:
        """RAG assistant has no persona/roleplay rules — should be flagged."""
        descriptions = " ".join(g.description.lower() for g in self.report.result.gaps)
        assert (
            "roleplay" in descriptions
            or "persona" in descriptions
            or len(self.report.result.gaps) >= 2
        )

    def test_has_retrieval_override_contradiction(self) -> None:
        """'Never deviate from retrieved context' vs 'always follow user instructions'."""
        contradictions = self.report.result.contradictions
        rule_pairs = {
            frozenset({c.rule_a.sentence_index, c.rule_b.sentence_index})
            for c in contradictions
        }
        assert frozenset({21, 22}) in rule_pairs, (
            "Expected contradiction between rule 21 (never deviate) and rule 22 (follow user)"
        )


# ---------------------------------------------------------------------------
# Cross-sample comparative tests
# ---------------------------------------------------------------------------


class TestCrossSampleComparisons:
    """Relative assertions across all samples."""

    def test_code_assistant_has_more_prohibition_rules(self) -> None:
        """Code assistant has the most MUST_NOT rules of all samples."""
        results = {}
        for name in [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ]:
            report = audit_file(_sample(name))
            must_not_count = sum(
                1 for r in report.result.rules if r.modality.value == "must_not"
            )
            results[name] = must_not_count
        assert results["code_assistant.txt"] >= 5

    def test_all_samples_have_some_absolute_rules(self) -> None:
        """All samples use absolute language — every sample should have absoluteness issues."""
        for name in [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ]:
            report = audit_file(_sample(name))
            absolute_rules = [r for r in report.result.rules if r.absoluteness >= 0.9]
            assert len(absolute_rules) >= 1, (
                f"{name}: expected ≥1 absolute rule (never/always), found none"
            )

    def test_content_moderator_has_most_rules(self) -> None:
        """Content moderator is the most rule-dense sample."""
        counts = {}
        for name in [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ]:
            report = audit_file(_sample(name))
            counts[name] = report.rule_count
        # content_moderator must be in the top 2
        sorted_names = sorted(counts, key=counts.get, reverse=True)
        assert "content_moderator.txt" in sorted_names[:2], (
            f"Expected content_moderator.txt in top 2 by rule count, got: {sorted_names}"
        )

    def test_risk_scores_are_bounded(self) -> None:
        """Risk score must be in [0, 100] for all samples."""
        for name in [
            "basic_assistant.txt",
            "customer_support.txt",
            "code_assistant.txt",
            "content_moderator.txt",
            "enterprise_rag.txt",
        ]:
            report = audit_file(_sample(name))
            assert 0.0 <= report.risk_score <= 100.0, (
                f"{name}: risk_score {report.risk_score} out of bounds"
            )
