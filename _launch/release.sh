#!/usr/bin/env bash
# rule-audit v0.1.0 release commands. DO NOT auto-execute.
set -euo pipefail

# 0. PyPI Trusted Publishing setup (one-time, manual):
#      PyPI project 'rule-audit' -> Settings -> Publishing -> Add trusted publisher
#        repo:        roli-lpci/rule-audit
#        workflow:    release.yml
#        environment: pypi
#    GitHub: Settings -> Environments -> New environment 'pypi'.

# 1. CI + static checks green
pytest -q
python -m ruff check rule_audit/ tests/
python -m mypy rule_audit/ --ignore-missing-imports

# 2. Local build + twine check
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*

# 3. Tag + push -> release.yml fires
git tag -a v0.1.0 -m "rule-audit v0.1.0: initial public release"
git push origin v0.1.0

# 4. Watch workflow
gh run watch --repo roli-lpci/rule-audit

# 5. After PyPI lands:
#    - Verify https://pypi.org/project/rule-audit/
#    - Fresh-venv install test: pip install rule-audit && rule-audit --demo
#    - gh release create v0.1.0 --generate-notes
