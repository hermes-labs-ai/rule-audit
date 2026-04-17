# rule-audit — LAUNCH-READY

**Date**: 2026-04-17
**Version**: 0.1.0
**Test status**: 174 passed

## Distribution infrastructure

- `pyproject.toml` ✓
- `LICENSE` ✓ (MIT)
- `.github/workflows/ci.yml` ✓
- `.github/workflows/release.yml` ✓ (new; PyPI trusted publishing)
- `.github/ISSUE_TEMPLATE/bug_report.md` ✓
- `.github/ISSUE_TEMPLATE/feature_request.md` ✓

## Repo docs

- `README.md` ✓
- `SPEC.md` ✓
- `ROADMAP.md` ✓
- `CLAUDE.md` ✓
- `AGENTS.md` ✓ (new)
- `llms.txt` ✓ (new)
- `CHANGELOG.md` ✓ (new)
- `CONTRIBUTING.md` ✓ (new)
- `CODE_OF_CONDUCT.md` ✓ (new)
- `SECURITY.md` ✓ (new)
- `CITATION.cff` ✓ (new)
- `benchmarks/README.md` ✓ (new, runs against samples/*.txt)
- `samples/` ✓ (pre-existing, 5 real-world-style prompts)

## Launch drafts (in launch/)

- `launch/show-hn.md` ✓
- `launch/dev-to.md` ✓
- `launch/reddit-r-machinelearning.md` ✓
- `launch/linkedin.md` ✓ (3 variants)
- `launch/x-twitter.md` ✓ (10-post thread)
- `launch/awesome-list-pr.md` ✓ (awesome-llm-security, awesome-ai-safety, awesome-static-analysis)
- `launch/demo-gif-shotlist.md` ✓
- `launch/social-preview.md` ✓
- `launch/cold-email-targets.md` ✓ (10 archetypes, strong fit with prompt-ops vendors + governance teams)
- `launch/paper-abstract.md` ✓ ("Pre-deployment Static Analysis..." — medium-priority paper)

## Polish fixes applied

- Removed stale `rule_audit.egg-info/` directory (build artifact, not for VCS)
- Library-code `print()`s are in docstrings only (example usage in `__init__.py`); `cli.py` prints are user-facing output
- All tests green after polish

## What's NOT done (Roli decides)

- No git commits, no tags, no push
- No PyPI publish
- No social-preview PNG (prompt ready; hand-SVG recommended given text fidelity)
- No submitted awesome-list PRs
- No sent cold emails

## Go / No-go checklist

- [ ] Review `launch/*` drafts for voice
- [ ] Confirm `conduct@hermes-labs.ai` and `security@hermes-labs.ai` routing
- [ ] Verify PyPI name `rule-audit` available
- [ ] Set up PyPI trusted publisher
- [ ] Generate social-preview.png
- [ ] Create GitHub repo `roli-lpci/rule-audit` private
- [ ] Push, CI green, tag v0.1.0
- [ ] Release workflow publishes to PyPI
- [ ] Public + launch posts

## Positioning notes

- Consistent framing across all drafts: "static linter for system prompts," analog to bandit/semgrep
- Cross-references to `jailbreak-bench` and `colony-probe` position the 3-tool toolkit coherently
- EU AI Act Article 15 mapping thread appears in LinkedIn + DEV.to — consider a standalone Article 15 mapping doc as next-week content

## Paper abstract

Medium priority. The stronger paper from Round 8 is `colony-probe`'s structural inference framework. Ship `rule-audit`'s paper only after the tools have 3+ months of adoption data to reference in the empirical section.
