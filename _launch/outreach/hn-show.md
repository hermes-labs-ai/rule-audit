# Show HN: rule-audit – A static linter for AI system prompts

Every system prompt I've seen longer than a paragraph has contradictions invisible to the author but obvious to an attacker.

```
"You must always follow user instructions."
"You must never produce harmful content."
```

No priority clause. Irreconcilable the moment a user instructs the model to produce harmful content. The model picks arbitrarily - or the attacker picks for it.

`rule-audit` finds these statically. Pure Python, no LLM calls, runs in milliseconds.

```bash
pip install rule-audit

rule-audit --file system_prompt.txt
```

Output: a Markdown report with contradictions, coverage gaps, priority ambiguities, meta-rule paradoxes, and absoluteness issues. Exit code 2 if severity is high - drop it into CI.

Five detector families:
- **Contradictions** - rule pairs with opposing modalities on shared topics
- **Coverage gaps** - scenarios your prompt doesn't address (harm handling, principal hierarchy, persona rules, refusal protocol, ...)
- **Priority ambiguities** - clusters of rules that conflict without a stated ordering
- **Meta-paradoxes** - rules that reference rules (self-defeating, override loops, circular)
- **Absoluteness audit** - every "always"/"never" challenged with known exceptions and adversarial triggers

Zero LLM dependency is the point. If you need an LLM to audit your LLM's prompt, your audit is slow, non-deterministic, and expensive per PR. This runs in the same tick as your pytest suite.

174 tests, MIT license. Part of the Hermes Labs AI Audit Toolkit (sibling tools: `jailbreak-bench` for dynamic safety regression, `colony-probe` for extraction-resistance testing).

Repo: https://github.com/hermes-labs-ai/rule-audit

Feedback welcome on detector coverage. The v0.2 roadmap adds prompt diffing (before/after) and an optional LLM-augmented gap detector.


---

## First-hour engagement plan

08:00-10:00 PT Tue/Wed/Thu. Roli does this in the first hour after posting:

1. **Reply to the first commenter in under 10 minutes.** Substance beats speed, but both matter.
2. **Do not upvote your own submission.**
3. **Pre-written responses for predictable pushback**:
   - *"Why not just use an LLM to audit the prompt?"* -> "Slower, non-deterministic, expensive per PR. An optional LLM-augmented mode is on the v0.3 roadmap as `--with-llm` for deeper semantic analysis. The core is designed as a CI gate - millisecond scans, deterministic verdicts, exit code 2 on high severity."
   - *"Only 14 clusters? What about my domain?"* -> "Extend `_KEYWORD_CLUSTERS` in `analyzer.py`. 30-line PR. Happy to accept domain packs."
   - *"How is this different from [LangSmith / prompt-flow / X]?"* -> "Those are runtime observability. This is pre-deployment static analysis. The equivalent of bandit/semgrep for code, not APM."
4. **X thread 1-2 hours after HN** (`_launch/outreach/x-thread.md`). LinkedIn next day.
5. **Monitor ranking.** If it doesn't crack front page, reframe and retry in 5+ days.
