# Launch plan - rule-audit

Same cadence as jailbreak-bench. T-0 = public flip + Show HN.

## T-3 days
- Gate: hygiene pass, voice-lint clean, 174 tests green, ruff + mypy clean.
- Actions: confirm `pip install rule-audit --pre` is not already indexed; reserve PyPI name; fresh-venv install test.

## T-2 days
- Gate: Show HN and LinkedIn drafts reviewed.
- Actions: decide whether to publish `rule-audit --demo` as the hero GIF (likely yes, one-line install + one-command demo is cleaner than jailbreak-bench here).

## T-1 day
- Gate: GitHub repo ready to flip; gh-metadata.sh ready.
- Actions: stage the first-hour replies.

## T+0
- 08:00-10:00 PT Tue/Wed/Thu. Ordered:
  1. Flip public via `gh repo edit`.
  2. Upload social preview via web UI.
  3. Run `_launch/gh-metadata.sh`.
  4. Tag v0.1.0, push; release workflow publishes to PyPI via Trusted Publishing.
  5. Submit Show HN.
  6. First-hour engagement plan.

## T+1 hour
- X thread.

## T+1 day
- DEV.to (`published: true`), Medium mirror, LinkedIn 250-word variant.

## T+3 days
- Reddit: r/MachineLearning with `[P]` flair. Use `_launch/outreach/reddit/r-MachineLearning.md`.

## T+7 days
- Cold-email wave 1: prompt-management vendors (PromptLayer, LangSmith, Humanloop), AI governance leads.

## T+14 days
- Awesome-list PRs (awesome-llm-security, awesome-ai-safety, awesome-static-analysis).
- Write a "here's what early users found" blog follow-up if there's material.

## Pair-launch note
All three tools (jailbreak-bench, rule-audit, colony-probe) land the same week. Stagger the Show HN posts by at least 24 hours each to avoid karma dilution and to let each tool carry its own HN conversation.
