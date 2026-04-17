# Paper abstract — rule-audit

## Title
**Pre-deployment Static Analysis for LLM System Prompts: Contradiction, Gap, and Priority-Ambiguity Detection Without LLM Invocation**

## Authors
Rolando Bosch, Hermes Labs

## Category
cs.CL (primary), cs.SE (secondary)

## Abstract (250 words)

System prompts for LLM-backed products function as natural-language policy specifications, yet they receive far less formal scrutiny than the code surrounding them. We observe that non-trivial system prompts (>100 words) routinely contain logical contradictions, coverage gaps, and priority ambiguities that are invisible to intent-reading review but are structurally detectable. We present `rule-audit`, a static analyzer that treats system prompts as a linting target and reports five families of findings without invoking any LLM:

1. **Modality contradictions** — rule pairs with opposing deontic modalities on overlapping topic clusters, detected via a modality opposition table and cluster membership.
2. **Coverage gaps** — absence of rules addressing canonical safety domains (14 semantic clusters: harm handling, principal hierarchy, persona, refusal protocol, etc.).
3. **Priority ambiguities** — conflicting rule clusters with no stated ordering clause.
4. **Meta-paradoxes** — rules that reference rules in self-defeating, circular, or override-loop configurations.
5. **Absoluteness issues** — absolute modifiers ("always"/"never") paired with known exception cases or adversarial triggers.

Each finding is accompanied by an automatically-generated adversarial edge case that demonstrates how an attacker could exploit the flaw. Analysis completes in milliseconds on typical production prompts (<100 rules), making it suitable as a CI gate.

We argue that static prompt analysis is a necessary complement to dynamic safety evaluation: static analysis catches classes of flaw that deterministic reasoning can identify before deployment, while dynamic testing measures behavioral outcomes after deployment. A reference implementation is available as an open-source Python package under MIT license. We report the detector family design, keyword cluster construction, and severity scoring calibration against a corpus of real-world production-style system prompts.

## Priority in the Hermes Labs paper stack

**Medium priority.** The engineering contribution is clear; the novel-research contribution is moderate (the taxonomy of prompt-flaw classes is the most research-worthy piece). Better fit for an ML-tools workshop or software-engineering venue than arxiv cs.CL proper.

## Candidate venues

- NeurIPS ML Safety Workshop
- ICML ML4Systems workshop
- EMNLP Industry Track
- ICSE SE4ML workshop

## Timeline

- **Now**: Draft abstract saved. No rush.
- **Q3 2026**: Collect a labelled corpus of production system prompts (with consent) for calibration evaluation.
- **Q4 2026**: Submit to the earliest CfP after the calibration section is complete.

## Related higher-priority papers

The `colony-probe` structural-inference paper is the higher-priority submission in the Hermes Labs stack (see `colony-probe/launch/paper-abstract.md`). If only one paper ships this quarter, that's the one.
