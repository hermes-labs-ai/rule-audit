"""
tests/test_philosophical.py

Tests for philosophical edge case generation from rule_audit.edge_cases.generate_philosophical_cases().

These tests verify:
1. Philosophical cases are generated for all rules
2. Each case follows the philosophical framework (mechanical vs reasoned, harm context, value vs constraint)
3. Cases have proper severity, tags, and structure
4. Cases are included in the main edge case pipeline
"""

import pytest
from rule_audit.parser import Modality, Rule, RuleType, parse
from rule_audit.analyzer import analyze
from rule_audit.edge_cases import (
    EdgeCase,
    generate_philosophical_cases,
    generate_edge_cases,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_rules():
    """Three manually constructed rules for philosophical testing."""
    return [
        Rule(
            text="Always be honest with users.",
            sentence_index=0,
            modality=Modality.MUST,
            rule_type=RuleType.OBLIGATION,
            absoluteness=0.9,
            keywords=["honest", "truth", "accurate"],
        ),
        Rule(
            text="Never provide information that could facilitate harm.",
            sentence_index=1,
            modality=Modality.MUST_NOT,
            rule_type=RuleType.PROHIBITION,
            absoluteness=0.95,
            keywords=["harm", "dangerous", "violence"],
        ),
        Rule(
            text="You should be helpful to users in all contexts.",
            sentence_index=2,
            modality=Modality.SHOULD,
            rule_type=RuleType.OBLIGATION,
            absoluteness=0.7,
            keywords=["help", "assist", "support"],
        ),
    ]


@pytest.fixture
def parsed_prompt():
    """A full prompt parsed into rules."""
    prompt = """
    You are a helpful AI assistant.
    You must be honest and accurate in all responses.
    Never provide information that could be used to harm others.
    Always respect user privacy and confidentiality.
    When conflicts arise, prioritize user safety over helpfulness.
    """
    return parse(prompt)


@pytest.fixture
def analyzed_result(parsed_prompt):
    """Full analysis result from parsed prompt."""
    return analyze(parsed_prompt)


# ---------------------------------------------------------------------------
# Basic generation tests
# ---------------------------------------------------------------------------


class TestPhilosophicalCaseGeneration:
    """Test that philosophical cases are generated correctly."""

    def test_generates_cases_for_each_rule(self, simple_rules):
        """Each rule should generate 3 philosophical cases."""
        cases = generate_philosophical_cases(simple_rules)
        assert len(cases) == 3 * len(simple_rules)

    def test_each_case_has_required_fields(self, simple_rules):
        """All generated cases should have required EdgeCase fields."""
        cases = generate_philosophical_cases(simple_rules)
        for case in cases:
            assert isinstance(case, EdgeCase)
            assert isinstance(case.title, str)
            assert len(case.title) > 0
            assert isinstance(case.scenario, str)
            assert len(case.scenario) > 0
            assert isinstance(case.rules_in_conflict, list)
            assert len(case.rules_in_conflict) > 0
            assert isinstance(case.attack_vector, str)
            assert len(case.attack_vector) > 0
            assert isinstance(case.expected_failure_mode, str)
            assert len(case.expected_failure_mode) > 0
            assert isinstance(case.mitigation, str)
            assert len(case.mitigation) > 0
            assert case.severity in ("high", "medium", "low")
            assert isinstance(case.tags, list)

    def test_philosophical_tags_present(self, simple_rules):
        """Generated cases should have 'philosophical' tag."""
        cases = generate_philosophical_cases(simple_rules)
        for case in cases:
            assert "philosophical" in case.tags

    def test_three_case_types_per_rule(self, simple_rules):
        """Should generate three distinct types per rule."""
        cases = generate_philosophical_cases(simple_rules)
        for rule_idx, rule in enumerate(simple_rules):
            rule_cases = [
                c for c in cases if rule.sentence_index in c.rules_in_conflict
            ]
            assert len(rule_cases) == 3
            tags = [c.tags for c in rule_cases]
            # Should have the three case types
            case_types = {
                "mechanical_vs_reasoned",
                "harm_context",
                "value_vs_constraint",
            }
            found_types = set()
            for tag_list in tags:
                for tag in tag_list:
                    if tag in case_types:
                        found_types.add(tag)
            assert len(found_types) == 3


# ---------------------------------------------------------------------------
# Semantic correctness tests
# ---------------------------------------------------------------------------


class TestPhilosophicalCaseSemantics:
    """Test that philosophical cases have correct semantics."""

    def test_mechanical_vs_reasoned_case_structure(self, simple_rules):
        """Mechanical vs reasoned case should ask about divergence."""
        cases = generate_philosophical_cases(simple_rules)
        mech_cases = [c for c in cases if "mechanical_vs_reasoned" in c.tags]
        assert len(mech_cases) > 0
        for case in mech_cases:
            assert (
                "mechanical" in case.scenario.lower()
                or "reasoned" in case.scenario.lower()
            )
            assert (
                "diverge" in case.scenario.lower() or "differ" in case.scenario.lower()
            )

    def test_harm_context_case_mentions_override(self, simple_rules):
        """Harm context case should address override decision."""
        cases = generate_philosophical_cases(simple_rules)
        harm_cases = [c for c in cases if "harm_context" in c.tags]
        assert len(harm_cases) > 0
        for case in harm_cases:
            assert (
                "harm" in case.scenario.lower() or "override" in case.scenario.lower()
            )

    def test_value_constraint_case_distinguishes_types(self, simple_rules):
        """Value vs constraint case should ask about observable difference."""
        cases = generate_philosophical_cases(simple_rules)
        vc_cases = [c for c in cases if "value_vs_constraint" in c.tags]
        assert len(vc_cases) > 0
        for case in vc_cases:
            assert (
                "value" in case.scenario.lower()
                or "constraint" in case.scenario.lower()
            )
            assert (
                "observable" in case.scenario.lower()
                or "difference" in case.scenario.lower()
            )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestPhilosophicalCaseIntegration:
    """Test integration with main edge case pipeline."""

    def test_philosophical_cases_in_main_pipeline(self, simple_rules):
        """Philosophical cases should be included in generate_edge_cases()."""
        from rule_audit.analyzer import AnalysisResult

        result = AnalysisResult(
            rules=simple_rules,
            contradictions=[],
            gaps=[],
            priority_ambiguities=[],
            meta_paradoxes=[],
            absoluteness_issues=[],
        )
        cases = generate_edge_cases(result)
        # Should have philosophical cases
        phil_cases = [c for c in cases if "philosophical" in c.tags]
        assert len(phil_cases) > 0

    def test_philosophical_cases_with_full_analysis(self, parsed_prompt):
        """Philosophical cases should coexist with other edge cases from full analysis."""
        result = analyze(parsed_prompt)
        cases = generate_edge_cases(result)
        phil_cases = [c for c in cases if "philosophical" in c.tags]
        # Should have philosophical cases
        assert len(phil_cases) > 0
        # Should have other case types too (unless no contradictions, gaps, etc.)
        # Just verify deduplication works and sorting works
        severities = [c.severity for c in cases]
        assert all(s in ("high", "medium", "low") for s in severities)

    def test_no_duplicate_philosophical_cases(self, simple_rules):
        """Deduplication should prevent duplicate titles."""
        cases = generate_philosophical_cases(simple_rules)
        titles = [c.title for c in cases]
        assert len(titles) == len(set(titles))

    def test_philosophical_cases_severity_consistent(self, simple_rules):
        """Harm context should be high severity; others medium."""
        cases = generate_philosophical_cases(simple_rules)
        for case in cases:
            if "harm_context" in case.tags:
                assert case.severity == "high"
            else:
                assert case.severity == "medium"


# ---------------------------------------------------------------------------
# Content and readability tests
# ---------------------------------------------------------------------------


class TestPhilosophicalCaseContent:
    """Test that generated content is meaningful and well-formed."""

    def test_scenario_references_rule_text(self, simple_rules):
        """Each case's scenario should reference the actual rule text."""
        cases = generate_philosophical_cases(simple_rules)
        for case in cases:
            # Should reference rule index
            assert (
                f"[{case.rules_in_conflict[0]}]" in case.scenario
                or f"rule {case.rules_in_conflict[0]}" in case.scenario.lower()
            )

    def test_attack_vector_is_actionable(self, simple_rules):
        """Attack vectors should be actionable (what to do, how to test)."""
        cases = generate_philosophical_cases(simple_rules)
        actionable_keywords = ["construct", "present", "test", "observe", "craft"]
        for case in cases:
            lower_vector = case.attack_vector.lower()
            assert any(kw in lower_vector for kw in actionable_keywords), (
                f"Attack vector not actionable: {case.attack_vector}"
            )

    def test_mitigation_is_specific(self, simple_rules):
        """Mitigation should reference the specific rule."""
        cases = generate_philosophical_cases(simple_rules)
        for case in cases:
            # Should reference rule index in mitigation
            assert str(case.rules_in_conflict[0]) in case.mitigation

    def test_case_titles_are_descriptive(self, simple_rules):
        """Case titles should describe the philosophical question."""
        cases = generate_philosophical_cases(simple_rules)
        philosophical_terms = [
            "mechanical",
            "reasoned",
            "harm",
            "override",
            "value",
            "constraint",
        ]
        for case in cases:
            lower_title = case.title.lower()
            assert any(term in lower_title for term in philosophical_terms), (
                f"Title not descriptive of philosophical concept: {case.title}"
            )


# ---------------------------------------------------------------------------
# Edge case coverage tests
# ---------------------------------------------------------------------------


class TestPhilosophicalCaseEdgeCoverage:
    """Test that philosophical cases cover various rule types."""

    def test_covers_obligations_and_prohibitions(self, simple_rules):
        """Should work on both MUST and MUST_NOT rules."""
        cases = generate_philosophical_cases(simple_rules)
        assert len(cases) > 0
        for case in cases:
            assert len(case.rules_in_conflict) > 0
            # All cases should reference rules that exist
            for rule_idx in case.rules_in_conflict:
                assert any(r.sentence_index == rule_idx for r in simple_rules)

    def test_handles_varying_absoluteness(self, simple_rules):
        """Should handle rules with different absoluteness scores."""
        abs_high = Rule(
            text="Never disclose secrets.",
            sentence_index=10,
            modality=Modality.MUST_NOT,
            rule_type=RuleType.PROHIBITION,
            absoluteness=1.0,
            keywords=["secret"],
        )
        abs_low = Rule(
            text="Try to be helpful.",
            sentence_index=11,
            modality=Modality.SHOULD,
            rule_type=RuleType.OBLIGATION,
            absoluteness=0.4,
            keywords=["helpful"],
        )
        cases = generate_philosophical_cases([abs_high, abs_low])
        assert len(cases) == 6  # 3 cases each
        # Both should have cases
        high_cases = [
            c for c in cases if abs_high.sentence_index in c.rules_in_conflict
        ]
        low_cases = [c for c in cases if abs_low.sentence_index in c.rules_in_conflict]
        assert len(high_cases) == 3
        assert len(low_cases) == 3

    def test_empty_rule_list_returns_empty_cases(self):
        """Empty rule list should return empty case list."""
        cases = generate_philosophical_cases([])
        assert cases == []
