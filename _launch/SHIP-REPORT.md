# SHIP-REPORT - rule-audit

Pre-ship gate: **10/10 PASS**. No waivers.

## What landed in this repo
- Code + tests: 174 passing, ruff clean, mypy clean (fixed 3 latent issues during polish: dead `clusters` variable, `AbsolutenessIssue` mypy shadow bug, stale `parse_file` import).
- CLI: `rule-audit --help` / `--demo` / `--file` / `--format {markdown,json,summary}` / `--min-severity` all working. Exit 2 on HIGH/CRITICAL for CI-gate use.
- Repo hygiene: README (with Limitations), SPEC, ROADMAP, CLAUDE.md, AGENTS.md, llms.txt, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY.md, CITATION.cff, LICENSE (MIT), samples/* (5 real-world-style prompts).
- CI + release: `.github/workflows/{ci.yml,release.yml}` (Py 3.9-3.12 matrix, mypy with `continue-on-error` during alpha, audit-samples smoke job, release via PyPI Trusted Publishing on tag).
- Launch bundle: `_launch/` complete - classification, claim, hygiene-report, positioning, gh-metadata.sh, release.sh, images/hero.jpg + social-1200x630.jpg, outreach/* with First-hour plan, paper/DECISION.md + abstract.md, LAUNCH-PLAN.md, preship-gate.md.
- Manifest registered at `~/ai-infra/manifests/rule-audit.yaml`; `find_tool.py "rule-audit"` returns at rank 1.

## Roli's remaining steps (ordered)
1. Read `_launch/outreach/hn-show.md`, `_launch/outreach/linkedin.md` (the 250-word variant reads well), and spot-check the Limitations section in `README.md`.
2. PyPI Trusted Publishing setup per `_launch/release.sh`.
3. Flip repo public: `gh repo edit roli-lpci/rule-audit --visibility public --accept-visibility-change-consequences`.
4. Upload `_launch/images/social-1200x630.jpg` via GitHub Settings -> Social preview.
5. Run `bash _launch/gh-metadata.sh` after public flip.
6. Run `bash _launch/release.sh` to tag v0.1.0.
7. Submit Show HN 08:00-10:00 PT next Tue/Wed/Thu using `_launch/outreach/hn-show.md`.
8. Cadence: X thread 1 hour after HN; DEV.to + Medium + LinkedIn next day; Reddit r/MachineLearning 3 days later.

## Paper decision
`blog-only` now. Q4 2026 decision point: if 30+ real production prompts are consented-shared for calibration, upgrade to `publish-workshop`. Confidence 0.75. See `_launch/paper/DECISION.md`.

## Gates Roli should reconsider (none waived)
- `pre-commit` skipped (CI covers ruff). OK for v0.1.0.
