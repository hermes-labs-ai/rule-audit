# Positioning - rule-audit

## Why now
System prompts have become production assets. They are version-controlled, code-reviewed, and deployed - but in most teams they are not linted. The eye-test misses mechanical contradictions that a probing attacker finds immediately. As LLM products ship to regulated industries and the EU AI Act's Article 15 robustness-testing obligations begin 2026-08-02, "we reviewed the prompt manually" is no longer defensible evidence. `rule-audit` gives teams a sub-second, deterministic, zero-LLM-dependency pre-deployment check that drops into the same CI they already run for code.

## ICP
An engineering lead at a series-B or later AI-native SaaS, or a DevRel / platform engineer at a prompt-management product (PromptLayer, LangSmith, Humanloop, Helicone). They manage prompts as first-class artifacts, they already have CI discipline for code, and they want the equivalent for prompts before the compliance team asks.

## Competitor delta
- **Do nothing** (no static pre-flight). The current default. Risk is invisible-until-attacker-finds-it.
- **LLM-augmented review** (feed the prompt to a judge model). More accurate but slow, non-deterministic, expensive per PR, unauditable. `rule-audit` is the gate; an LLM-augmented mode can ride on top as an optional `--with-llm` pass.
- **Ad-hoc review checklists** (internal docs, Notion pages). Drift fast, uneven across teams. `rule-audit` encodes the checklist as code with a fail-exit.

## Adjacent interests
- If you like `bandit` or `semgrep` for code security, you will like `rule-audit` for prompt structural flaws - same model applied to natural-language safety rules.
- If you use `promptfoo` for runtime prompt testing, `rule-audit` is the pre-deployment companion (static flaws before runtime measurement).
- If you are building an AI-Act Article 15 evidence trail, `rule-audit` produces the pre-deployment artifact that pairs with `jailbreak-bench` (dynamic regression) and `colony-probe` (operational probing) from the same Hermes Labs AI Audit Toolkit.
