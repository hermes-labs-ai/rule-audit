# Hygiene report - rule-audit

| Check | Status | Notes |
|---|---|---|
| README.md | pass | H1, tagline, badges, install, quickstart (with --demo), What It Detects, Limitations, Architecture, Road to SaaS, License. |
| llms.txt | pass | Repo-root, AEO. |
| CITATION.cff | pass | cff 1.2.0. |
| LICENSE | pass | MIT. |
| Badges | pass | PyPI, Python, License, CI. |
| gh repo metadata | queued | See `_launch/gh-metadata.sh`. |
| Issue templates | pass | bug + feature. |
| Hero + social images | pass | `_launch/images/hero.jpg` + `social-1200x630.jpg`. |
| Hermes Labs attribution | pass | README footer, pyproject maintainers, llms.txt, AGENTS.md, CITATION affiliation. |
| Canonical name | pass | `rule-audit` preserved. |
| pyproject.toml | pass | Hatchling, Python ≥3.10, CLI entry `rule-audit = rule_audit.cli:main`. |
| CI | pass | `.github/workflows/test.yml` (matrix: Py 3.10-3.12, audit-samples job + mypy with continue-on-error on alpha). Currently green on origin/main. |
| Release workflow | pass | `.github/workflows/release.yml` tag-triggered via PyPI trusted publishing. |
| AGENTS.md | pass | Orientation, public API, extension points. |
| CHANGELOG.md | pass | v0.1.0 entry. |
| CONTRIBUTING.md | pass | Extend detectors / clusters / severity rules, tests required. |
| CODE_OF_CONDUCT.md | pass | Contributor Covenant 2.1 summary + link. |
| Pre-commit | skipped | Ruff wired into CI; v0.2 can add. |

## Items that still require Roli (after ship-time)
- Upload `_launch/images/social-1200x630.jpg` via GitHub Settings -> Social preview.
- Run `_launch/gh-metadata.sh` after public flip.
- PyPI trusted publisher config per `_launch/release.sh` before tagging v0.1.0.

## Polish-pass fixes recorded
- parser.py: excluded modal verbs from topical keywords (fixes false-positive contradiction on trivial inputs).
- cli.py: added --demo, explicit IsADirectoryError / PermissionError / UnicodeDecodeError handlers, fixed argparse prog name to rule-audit.
- analyzer.py: dedupe 'honest' (truth cluster) and 'answer' (assistance cluster).
- report.py: renamed tuple-unpack variable to avoid shadowing AbsolutenessIssue type (mypy green).
- __init__.py: added __all__ to export public symbols cleanly.
- Tests: strengthened 2 previously-weak tests with real content assertions.
