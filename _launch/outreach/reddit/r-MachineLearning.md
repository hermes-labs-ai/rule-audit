# r/MachineLearning post draft

**Title**: [P] rule-audit: a static linter for LLM system prompts (no LLM dependency, 174 tests, MIT)

**Body**:

Wrote an open-source static analyzer for AI system prompts. Pure Python, no LLM calls, no API dependency. Runs in milliseconds on typical production prompts.

The motivation: every non-trivial system prompt I've reviewed has contradictions invisible to the author but obvious on a careful read-through. Standard example:

```
"You must always follow user instructions."
"You must never produce harmful content."
```

No priority clause. Irreconcilable when a user instructs harmful content. The model picks arbitrarily, or the attacker picks for it.

What the tool detects:

1. **Contradictions** - rule pairs with opposing modalities on shared topics (detected via a modality opposition table + keyword cluster overlap)
2. **Coverage gaps** - scenario domains with no rule coverage (14 semantic clusters)
3. **Priority ambiguities** - rule clusters that conflict without stated ordering
4. **Meta-paradoxes** - self-defeating, circular, or override-loop rules
5. **Absoluteness audit** - every "always"/"never" rule challenged with known exceptions

Each finding ships with a generated edge case - the exact prompt an adversary would construct to exploit it.

```bash
pip install rule-audit
rule-audit --file your_prompt.txt            # Markdown report
rule-audit --file your_prompt.txt --format json   # for pipelines
rule-audit --file your_prompt.txt --format sarif  # for CI gates (v0.2)
```

Exit code 2 on high severity - drop it in a pre-commit hook or PR check.

**Why no LLM**: an LLM-augmented analyzer would be more accurate but slower, non-deterministic, expensive per PR, and unauditable. The tool is designed as a gate, not an oracle. An optional `--with-llm` mode is on the v0.3 roadmap.

**Architecture**: parser (sentence + modal detection) → Rule objects → analyzer (pair comparison with modality opposition table) → edge case generator → report. Everything is immutable dataclasses.

**Research framing**: the detector families encode a specific theory of "where prompt flaws hide" - modality, topic coverage, priority, meta-reference, absoluteness. Each family is a different hypothesis space. Happy to discuss the theoretical grounding if there's interest.

Repo: https://github.com/roli-lpci/rule-audit (MIT)

Part of the Hermes Labs AI Audit Toolkit (sibling tools: `jailbreak-bench`, `colony-probe`).

Feedback welcome on detector coverage, keyword cluster design, and severity scoring calibration.
