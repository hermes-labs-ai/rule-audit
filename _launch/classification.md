# Classification - rule-audit

## Prior-art signal
- `find_tool.py "rule-audit"`: indexed in the Hermes Labs tool registry under static-analysis / prompt-audit category.
- Memory grep hits: `project_round8_21_products.md`, `project_modelbreak_hackathon.md` - both confirm 174 tests, 5-detector taxonomy, zero-LLM-dependency design.
- Classification consistent with prior-art signal.

## Category
**library** (primary) + **cli-tool** (secondary). Installable Python package, exposes `rule-audit` CLI and `audit` / `audit_file` / `AuditReport` programmatic API.

## Audience
Developers and governance teams who maintain system prompts as product assets and want a pre-deployment linter in their pull-request flow. Think `bandit` or `semgrep` but for natural-language safety rules.

## Normalized repo root
`/Users/rbr_lpci/Documents/projects/hermes-labs-hackathon/round-8-modelbreak/agent-07/rule-audit`
Remote: `https://github.com/roli-lpci/rule-audit.git`
Head: `db15061 fix: address maintainer review findings for v0.1.0` (local; not yet pushed because push authorization is pending).
