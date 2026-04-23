# Awesome-list PR drafts - rule-audit

## Target: awesome-llm-security

**PR title**: Add rule-audit (static linter for AI system prompts)

**Section**: Testing / Tools

**Line to insert** (alphabetical):

```markdown
- [rule-audit](https://github.com/hermes-labs-ai/rule-audit) - Static analyzer for LLM system prompts. Detects contradictions, coverage gaps, priority ambiguities, meta-paradoxes, and absoluteness issues across 14 semantic clusters. Pure Python, no LLM dependency, runs in milliseconds. 174 tests, MIT. Part of the Hermes Labs AI Audit Toolkit.
```

**PR body**:

Adding `rule-audit`, open-sourced this week by Hermes Labs. Static analyzer for system prompts - the "static half" of LLM safety testing. Complements dynamic red-teaming tools already in this list.

Differentiators:
- Zero LLM dependency (pure Python)
- Runs in milliseconds (CI-friendly)
- Exit code 2 on high severity (gate-ready)
- 174 tests, 5 detector families, 14 semantic clusters
- Each finding includes a generated edge-case prompt (the exact attack it predicts)

Happy to revise if you'd prefer a different section.

---

## Target: awesome-ai-safety

**Section**: Tools / Evaluation / Static Analysis

**Line to insert**:

```markdown
- [rule-audit](https://github.com/hermes-labs-ai/rule-audit) - Pre-deployment static analysis for LLM system prompts. Finds logical contradictions, coverage gaps, priority ambiguities, and meta-rule paradoxes before the prompt ships. MIT, pure Python.
```

---

## Target: awesome-static-analysis

**Section**: AI / ML (if exists) or Python → Other

**Line to insert**:

```markdown
- [rule-audit](https://github.com/hermes-labs-ai/rule-audit) - Static analyzer for LLM system prompts. Treats natural-language safety rules as a linting target. Python, MIT.
```

---

## Target: awesome-python / awesome-llm-apps

Lower priority - these are large lists with strict curation criteria. Wait until v0.1.0 is on PyPI and has visible adoption (stars + dependents) before submitting.

---

## General PR discipline

1. Check each list's CONTRIBUTING.md before submitting.
2. Don't duplicate submissions across overlapping curated lists.
3. Keep the description under 200 characters.
4. Don't market - describe.
5. If a maintainer asks for changes, make them quickly and thank them.

## Candidate additional targets

- awesome-prompt-engineering (if it has a "tools" section)
- awesome-llm-interpretability (adjacent but not a direct fit)
- awesome-semgrep (static-analysis community; adjacent even though this isn't a semgrep rule pack)

Submit to awesome-llm-security and awesome-ai-safety first. Monitor acceptance. If those land, expand.
