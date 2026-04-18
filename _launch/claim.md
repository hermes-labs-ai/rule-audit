# Claim - rule-audit

## One-sentence falsifiable claim
`rule-audit` detects contradictions, coverage gaps, priority ambiguities, meta-rule paradoxes, and absoluteness issues in natural-language LLM system prompts in under 100 milliseconds per prompt on prompts of up to 100 rules, with zero LLM invocations, and flags at least one finding on 100% of a corpus of known-imperfect real-world system prompts.

## Why it is falsifiable
- **Test**: run the linter against a labelled corpus of 50 real-world production system prompts with human-expert annotations.
- **Result shape**: precision and recall per detector family, total scan time per prompt, exit code distribution.
- **Failure mode**: if `rule-audit` reports HIGH severity on prompts that a human expert rates as clean, calibration is off. If it reports LOW on prompts with obvious exploitable flaws, coverage is insufficient.

## What the claim is NOT
- Not a semantic-understanding tool. Implied or narrative-embedded rules may be missed.
- Not a verdict on whether the prompt is "safe" - it flags mechanical structural flaws. Dynamic safety testing (`jailbreak-bench`) and conversational probing (`colony-probe`) cover behavior under attack.
- Not a replacement for human review. A clean `rule-audit` report is a necessary but not sufficient condition for a well-written prompt.
