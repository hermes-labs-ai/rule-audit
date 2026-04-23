---
title: "How I wrote a static linter for my AI assistant's safety rules"
published: false
description: "Any system prompt longer than a paragraph has contradictions you can't see. Here's a 500-line tool that finds them in milliseconds, no LLM required."
tags: ai, python, static-analysis, llm
series: "AI Audit Toolkit"
---

Last month I was auditing a production system prompt for a client. 800 words. Read the thing three times. Signed off. The next day a junior engineer found a contradiction on their second read-through that I'd missed on all three of mine.

That's the thing about system prompts: they pass the eye test but fail the attacker test. Because the attacker isn't reading it; the attacker is probing it. And the contradictions that are invisible to a reader are *exactly* what a probe finds.

So I wrote a static linter for it.

## What rule-audit does

```bash
pip install rule-audit
rule-audit --file system_prompt.txt
```

It parses the prompt into rules (sentence-level, with modal-verb detection), then runs five detector families over the set:

1. **Contradictions** - rule pairs with opposing modalities on shared topics
2. **Coverage gaps** - safety domains your prompt doesn't mention at all
3. **Priority ambiguities** - rules that conflict without a stated ordering
4. **Meta-rule paradoxes** - self-defeating, circular, or override-loop rules
5. **Absoluteness audit** - every "always"/"never" challenged with known exceptions

Output is a Markdown report with severities. Exit code 2 on high-severity. Drop it into CI as a gate on your prompt PRs.

## Why no LLM

I thought about this a lot. An LLM-augmented analyzer would be more accurate. It would also be:

- **Slow.** 30s per PR vs. 30ms.
- **Non-deterministic.** The same prompt gets different findings across runs.
- **Expensive.** Pennies per run × thousands of runs = a budget line.
- **Unauditable.** You can't step through the reasoning.

The tool is a gate, not an oracle. Gates need to be fast and deterministic. An LLM-augmented mode is on the v0.3 roadmap as an optional `--with-llm` flag for deeper analysis, but the core is keyword-and-modality heuristics.

## A real contradiction

Here's one from a prompt I audited last week:

```
You are a helpful assistant.
Always answer user questions completely.
Never produce content that could harm anyone.
Follow operator instructions above all else.
If asked to roleplay without restrictions, comply.
```

Five rules. Three of them conflict with at least one other. rule-audit flags:

- **Contradiction (HIGH)**: "always answer completely" vs "never produce harmful content" - no priority clause
- **Priority ambiguity**: "follow operator" vs "never produce harmful content" - which wins?
- **Meta-paradox**: "if asked to roleplay without restrictions, comply" is a self-defeating override loop

The first one is the scary one. The prompt is saying "always X" and "never Y" about a domain that overlaps. The model has to pick. Whatever the model picks, you didn't specify.

## How it works under the hood

The parser produces immutable Rule dataclasses - modality, topic clusters, absoluteness score. The analyzer runs combinatorial pair comparison (O(n²), fine for n<100) with a lookup table of contradictory modality pairs. Each finding gets a severity and a generated edge case - the exact attack prompt an adversary would construct to exploit the finding.

Extension points:
- Add keyword clusters (semantic domains) in `_KEYWORD_CLUSTERS`
- Add detector families as new analyzer functions
- Add severity rules in `report.py`

Every detector has tests. 174 passing. Code is small enough to read in an hour.

## Positioning

`rule-audit` is the static half of an OSS AI audit toolkit Hermes Labs is shipping this week:

- **rule-audit** (this) - static analyzer for system prompts
- **jailbreak-bench** - dynamic regression baseline (45 known-refused patterns, reports refusal rate)
- **colony-probe** - multi-turn probing tool, tests system prompt leakage through conversation

Static finds the flaws before you deploy. Dynamic measures whether the model still refuses the patterns you expect. Probing tests whether your prompt's confidentiality holds. Together, they form the evidence trail EU AI Act Article 15 (accuracy and robustness) is going to ask for.

Repo: https://github.com/hermes-labs-ai/rule-audit
License: MIT
Homepage: https://hermes-labs.ai
