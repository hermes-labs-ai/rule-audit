# Show HN: rule-audit – A static linter for AI system prompts

Every system prompt I've seen longer than a paragraph has contradictions invisible to the author but obvious to an attacker.

```
"You must always follow user instructions."
"You must never produce harmful content."
```

No priority clause. Irreconcilable the moment a user instructs the model to produce harmful content. The model picks arbitrarily — or the attacker picks for it.

`rule-audit` finds these statically. Pure Python, no LLM calls, runs in milliseconds.

```bash
pip install rule-audit

rule-audit --file system_prompt.txt
```

Output: a Markdown report with contradictions, coverage gaps, priority ambiguities, meta-rule paradoxes, and absoluteness issues. Exit code 2 if severity is high — drop it into CI.

Five detector families:
- **Contradictions** — rule pairs with opposing modalities on shared topics
- **Coverage gaps** — scenarios your prompt doesn't address (harm handling, principal hierarchy, persona rules, refusal protocol, ...)
- **Priority ambiguities** — clusters of rules that conflict without a stated ordering
- **Meta-paradoxes** — rules that reference rules (self-defeating, override loops, circular)
- **Absoluteness audit** — every "always"/"never" challenged with known exceptions and adversarial triggers

Zero LLM dependency is the point. If you need an LLM to audit your LLM's prompt, your audit is slow, non-deterministic, and expensive per PR. This runs in the same tick as your pytest suite.

174 tests, MIT license. Part of the Hermes Labs AI Audit Toolkit (sibling tools: `jailbreak-bench` for dynamic safety regression, `colony-probe` for extraction-resistance testing).

Repo: https://github.com/hermes-labs-ai/rule-audit

Feedback welcome on detector coverage. The v0.2 roadmap adds prompt diffing (before/after) and an optional LLM-augmented gap detector.
