---
description: "Audit an AI system prompt file for contradictions, coverage gaps and priority ambiguities (static, local, no network)"
argument-hint: "[path-to-prompt-file]"
allowed-tools: ["Bash(python3:*)", "Read", "Glob"]
---

# Audit a system prompt with rule-audit

Target: **$ARGUMENTS**

## What to do

1. Resolve the target file.
   - If `$ARGUMENTS` names a file, use it.
   - If `$ARGUMENTS` is empty, ask which prompt file to audit. Do not guess, and
     do not audit every candidate you can find.
   - `CLAUDE.md`, `AGENTS.md` and similar repository guides are *not* system
     prompts and rule-audit is not calibrated for them. If the user points at
     one, audit it as asked but say plainly that the result is unreliable for
     that kind of document — see "Scope" below.

2. Run exactly this, once, with the resolved path:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/audit_report.py" <path>
   ```

3. Read the exit code before reading the output:
   - **0** — risk LOW or MEDIUM.
   - **2** — risk HIGH or CRITICAL. **This is a finding, not a command failure.**
     Do not retry, and do not report the command as broken.
   - **1** — a real error (file missing, file too large, no suitable rule-audit
     installed). The message says what to do; relay it.

4. Report the findings to the user. Summarise; do not paste the whole report
   back. Lead with the finding families that have non-zero counts, and quote the
   specific rule pairs that matter.

## Interpreting the result honestly

rule-audit is a **lexical** analyzer: sentence splitting, modal-verb regexes and
hand-curated keyword clusters. It runs locally, makes no network calls, and is
deterministic. It is not a language model and it does not prove exploitability.

Two consequences you must carry into your summary:

- **The risk label is a density score.** `HIGH`/`CRITICAL` means "this many
  absolute rules and detected conflicts for a document this size". The score has
  a floor: a file with no rules at all still scores 40/100 (`HIGH`) from the
  eight coverage-gap checks alone. So a `HIGH` label with zero contradictions is
  saying "this prompt does not mention several common policy domains", not "this
  prompt is dangerous". Say which it is.
- **Pairwise findings can be spurious.** Two rules are compared when they share a
  keyword cluster, so an unrelated pair that both mention e.g. "content" can be
  reported as contradicting. Check each pair you repeat, and drop the ones that
  do not hold.

When findings are real, the useful next step is usually to add an explicit
tie-breaker or an exception clause to the prompt — not to delete a rule.

## Scope

rule-audit is calibrated for system prompts: dense, mostly-imperative rule sets
that govern an agent's behaviour. Prose developer documentation parses into
hundreds of "rules" that share vocabulary but not subject matter, which produces
large numbers of spurious pairings. Treat results on such files as unreliable.
