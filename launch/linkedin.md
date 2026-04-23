# LinkedIn drafts — Roli Bosch

## Variant A — 100 words

Shipped `rule-audit` today: a static linter for AI system prompts.

No LLM dependency. Runs in milliseconds. Finds contradictions, coverage gaps, priority ambiguities, and meta-rule paradoxes.

Think bandit/semgrep, but for your system prompt.

```bash
pip install rule-audit
rule-audit --file system_prompt.txt
```

174 tests. MIT license. Exit code 2 on high severity, so it slots into CI as a gate.

The static half of the Hermes Labs AI Audit Toolkit — sibling tools ship alongside for dynamic regression and extraction testing.

→ hermes-labs.ai

---

## Variant B — 250 words

Every AI product ships with a system prompt. Most of those prompts have contradictions invisible to the author but obvious to an attacker.

```
"Always follow user instructions."
"Never produce harmful content."
```

No priority clause. The model picks when they conflict — or the attacker does.

Today I'm open-sourcing `rule-audit`, a static linter for system prompts. Think bandit/semgrep but for AI safety rules. Pure Python, zero LLM calls, runs in milliseconds.

Five detector families:
- Contradictions (rule pairs with opposing modalities on shared topics)
- Coverage gaps (14 semantic clusters)
- Priority ambiguities
- Meta-rule paradoxes (self-defeating, circular, override loops)
- Absoluteness issues (every "always"/"never" challenged with known exceptions)

Each finding comes with a generated edge-case prompt — the exact construction an adversary would use to exploit the flaw. So you don't just see *what's* broken; you see *how* it breaks.

```bash
pip install rule-audit
rule-audit --file system_prompt.txt --format sarif  # for CI integration
```

Exit code 2 on high severity. 174 tests. MIT license.

For EU AI Act operators: this maps to Article 15 (accuracy and robustness) as the pre-deployment static artifact — evidence that your system prompt passed a mechanical review before shipping. Pairs with continuous post-deployment measurement (we ship that one too — `jailbreak-bench`, same week).

github.com/hermes-labs-ai/rule-audit
hermes-labs.ai

---

## Variant C — 500 words

Here's a thing about system prompts I've learned the hard way: every non-trivial one has contradictions the author can't see.

Not because the author is careless. Because the eye test is the wrong test. The eye is reading for intent. The attacker is probing for exploits. The contradictions hiding in a paragraph-long safety section are obvious to the probing mode and invisible to the intent-reading mode. So the author signs off, ships, and finds out there's a problem only when someone breaks it.

That is a very fixable class of problem. It's a mechanical problem. You can write a program that finds it. I wrote that program. It's called `rule-audit`, it's open-source, and it ships today.

```bash
pip install rule-audit
rule-audit --file system_prompt.txt
```

What it does:
- Parses the prompt into Rule objects (sentence-level, with modal-verb detection)
- Runs five detector families over the set
- Generates an edge-case prompt for each finding (the exact attack an adversary would construct)
- Scores severity, produces a Markdown or JSON or SARIF report, exits 2 on high severity

Detector families:

1. **Contradictions** — rule pairs with opposing modalities on shared topics, detected via a modality opposition table and keyword cluster overlap. Catches the `always X / never Y` pattern where X and Y can co-occur.

2. **Coverage gaps** — scenario domains your prompt doesn't mention at all. Runs against 14 semantic clusters (harm handling, principal hierarchy, persona rules, refusal protocol, instruction conflict, self-disclosure, edge cases, ...).

3. **Priority ambiguities** — rule clusters that conflict without a stated ordering. Names the clusters so you know where to add a priority clause.

4. **Meta-paradoxes** — rules that reference rules. Self-defeating ("ignore all instructions" voids itself), override loops ("these instructions supersede all others" is exploitable via injection), circular references.

5. **Absoluteness audit** — every "always"/"never"/"under no circumstances" rule is challenged with known exceptions and adversarial triggers.

Zero LLM dependency is deliberate. An LLM-augmented analyzer would be more accurate but 1000× slower, non-deterministic, expensive per PR, and unauditable. The tool is designed as a gate, not an oracle. Gates should be deterministic. An optional LLM-augmented mode is on the v0.3 roadmap as `--with-llm`.

Positioning: `rule-audit` is the static half of the Hermes Labs AI Audit Toolkit. Sibling tools:
- `jailbreak-bench` — dynamic regression baseline (45 known-refused patterns, reports refusal rate, same week)
- `colony-probe` — multi-turn probing tool, tests system prompt leakage through conversation

Static finds flaws before deploy. Dynamic measures whether behavior holds across model updates. Probing tests whether prompt confidentiality holds. Three artifacts, one evidence trail.

For EU AI Act Article 15 (accuracy and robustness) operators: the three tools together produce pre-deployment, post-deployment, and operational-probe evidence. We'll publish a notified-body mapping doc this week.

174 tests, MIT license, pip install rule-audit.

github.com/hermes-labs-ai/rule-audit · hermes-labs.ai

Feedback welcome on detector coverage, keyword cluster design, and how the SARIF output should schema for the code-scanning use case.
