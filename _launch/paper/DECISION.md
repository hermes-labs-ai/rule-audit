# Paper decision - rule-audit

## Recommendation
**blog-only**. Engineering contribution first, research contribution later if we collect a labelled corpus.

## Confidence
0.75 that blog-only is the right call for the 2026-Q2 window.

To raise confidence to 0.9 for publish-workshop: collect a consent-shared corpus of 30-50 real production system prompts with ground-truth labels (human expert flags: contradictions, gaps, priority ambiguities per rule), and report detector precision/recall against that corpus. That turns the paper from a tools description into a measurement paper.

## Reasoning
- The detector-family taxonomy (5 families, 14 clusters) has a modest theoretical contribution - it encodes a specific claim about "where prompt flaws hide" that is testable.
- But without a labelled corpus and a calibration study, the paper reads as "we shipped a linter" - accurate but below the bar for cs.CL or security venues.
- Better route: ship the tool as a blog + HN + DEV.to launch now. Collect the corpus in Q3 from early adopters. Write the measurement paper in Q4.
- Sibling `colony-probe` is the more paper-worthy artifact from the round-8 batch. Prioritize that pipeline first; rule-audit paper can wait.

## Novelty signals found
- The 14-cluster keyword taxonomy is hand-curated, not derived from the literature. That is a reasonable research contribution if we validate it.
- The modality opposition table (`_CONTRADICTORY_PAIRS` in `analyzer.py`) is an explicit claim about how deontic conflicts arise in natural-language safety rules.
- Zero-LLM-dependency design is a real operational constraint, not just an aesthetic choice - it unlocks CI-gate use cases that LLM-augmented competitors cannot match.

## Prior art contact
- Hammes & Peemöller (2024), "System Prompt Guidelines" - descriptive, not analytical.
- Prompt-engineering community posts on contradiction avoidance (various blog-level work on promptbase / cookbook repos).
- Static-analysis literature on natural-language policy (SLANG, Oasis) - adjacent field, not LLM-specific.
- No published static linter for LLM system prompts with measured detector precision.

## Action queued in ACTIONABLES.md
- Launch blog post + HN.
- Collect consenting production system prompts from early adopters (Q3 target: 30).
- Run human-rater study on 10 of them for calibration.
- Reopen decision in Q4 2026.
