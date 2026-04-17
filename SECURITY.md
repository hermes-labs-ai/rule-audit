# Security Policy

## Scope

`rule-audit` is a static analyzer — it reads text and produces a report. It does not execute any code from the input, does not call any LLM, and does not phone home. The attack surface is minimal.

If you find a security issue in `rule-audit` itself (e.g., crashes on crafted input, path traversal via file handling, dependency vulnerability), report it at **security@hermes-labs.ai**.

## Not in scope

- Findings that `rule-audit` itself generates — those are the product. If you disagree with how a contradiction is classified, open an issue on the main tracker, not a security report.
- Detections you think should exist but don't — feature request, not vulnerability.
- Performance concerns on very large prompts — open an issue with a reproduction.

## Response

- Acknowledgement within 72 hours
- Coordinated disclosure within 90 days
- Public thanks in CHANGELOG.md for reported and fixed issues (opt-in)

## Supported versions

Security fixes land on the latest minor release. Older minors receive no security backports.

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
