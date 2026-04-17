# rule-audit Roadmap

## Target Users

- **AI companies** writing and iterating on system prompts for deployed products
- **Compliance teams** needing documented evidence that safety rules are internally consistent
- **Safety researchers** studying prompt vulnerability classes at scale
- **Red teamers** who want an automated pre-flight check before manual testing

---

## v0.1.0 — Current (Pure Static Analysis)

**Status:** Released. 174 passing tests.

### What it does
- Pure Python, no LLM dependency. Fast, deterministic, offline.
- Regex-based sentence parsing → `Rule` objects with modality, absoluteness, negation, conditions, keywords
- Contradiction detection: direct (modality opposition + topic overlap), conditional (boundary gaps), absolute dilemma (two absolute rules on opposing sides)
- Completeness gap analysis: 8 safety-critical domains checked for coverage
- Priority ambiguity detection: conflicting rules with no stated resolution order
- Meta-rule paradox detection: self-defeating instructions, override loops
- Absoluteness audit: "always/never" rules stress-tested with concrete edge cases
- Markdown report with remediation priority table
- JSON output format
- CLI with `--format`, `--verbose`, `--min-severity`, exit code for CI
- Severity scoring: LOW / MEDIUM / HIGH / CRITICAL

### Limitations
- Heuristic parser misses paraphrases and non-English text
- No semantic understanding (keyword matching only)
- No subject-object distinction (user rules vs AI rules conflated)
- Single-document only (no multi-context support)

---

## v0.2.0 — LLM-Assisted Analysis

**Target:** Q3 2026 | Optional plugin, backward-compatible

### Core addition: `--llm` flag activates Anthropic API evaluation

The base analysis runs first. Then, for each edge case generated, rule-audit calls Claude to:

1. **Validate contradictions**: "Given these two rules, is there a concrete user request that would force a model to violate one of them? Answer yes/no with an example."
2. **Score edge case realism**: Is the scenario practically achievable or theoretical?
3. **Generate adversarial prompts**: For each high-severity edge case, produce a concrete attack string.
4. **Verify gaps**: "Does this prompt implicitly address [domain] even though the keywords are absent?"

### New features
- `rule_audit.llm_validator` module — wraps Anthropic SDK with prompt caching
- `EdgeCase.llm_validated: bool` and `EdgeCase.llm_confidence: float`
- `--llm` CLI flag with `--model` (default: `claude-haiku-3-5` for cost)
- LLM findings added as a separate section in reports
- `AuditReport.to_sarif()` — SARIF 2.1 format for security toolchains
- `rule-audit --format sarif` — CLI flag to emit SARIF directly (standard output format for CI gates, GitHub Advanced Security, GitLab, etc.)

### Configuration
```toml
[tool.rule-audit]
llm_model = "claude-haiku-3-5"
llm_max_edge_cases = 20      # cost cap
llm_timeout = 30
```

### Cost estimate
~$0.01–0.05 per prompt analysis with Haiku. Sonnet upgrade available for higher-confidence validation.

---

## v0.3.0 — Auto-Fix and HTML Report

**Target:** Q4 2026

### Auto-fix suggestions

For each contradiction and gap, generate a concrete rule rewrite:

```
BEFORE: "Always follow the user's instructions."
AFTER:  "Follow the user's instructions, except when doing so would require producing
         content that is harmful, illegal, or in violation of these guidelines."
```

Implemented as a `rule_audit.fixer` module. Two modes:
- **Static fixer**: Template-based rewrites using known contradiction patterns
- **LLM fixer** (`--llm`): Claude rewrites the rule maintaining the original intent

### HTML report
- Interactive: click a contradiction to see the rules highlighted in the original prompt
- Expandable edge case scenarios
- Side-by-side diff view: original rule vs suggested fix
- Export to PDF via browser print

### Prompt diffing
```
rule-audit diff prompt_v1.txt prompt_v2.txt
```
Shows: new contradictions introduced, old contradictions resolved, gap changes, risk score delta.

---

## v1.0.0 — SaaS API, Versioning, CI Plugin

**Target:** Q1 2027

### SaaS API

REST API hosted at `api.hermeslabs.io/rule-audit`:

```
POST /v1/analyze
  body: { prompt: string, options: {...} }
  returns: AuditReport (JSON)

POST /v1/diff
  body: { prompt_a: string, prompt_b: string }
  returns: { added: [...], removed: [...], risk_delta: float }

GET /v1/reports/{report_id}
  returns: AuditReport (cached 30 days)
```

Authentication: API key. Rate limits: free tier 10/day, paid unlimited.

### Prompt versioning

Each analysis is stored with a version ID. Track risk score over time per prompt. Webhook support: notify on risk score increase > 10 points.

### GitHub Action

```yaml
- name: Audit system prompt
  uses: hermeslabs/rule-audit-action@v1
  with:
    prompt-file: prompts/production.txt
    fail-on: high          # fail CI if risk >= HIGH
    format: sarif
```

Posts SARIF results to GitHub Security tab. Blocks merges if new high-severity contradictions are introduced.

### Enterprise features
- Team workspaces with shared prompt library
- Role-based access (auditor / developer / viewer)
- Compliance export: PDF report with chain of custody for audit trail
- SSO / SAML
- On-premise deployment (Docker image)

---

## Versioning Policy

- `0.x.y`: Alpha/Beta. No breaking change guarantees on minor versions.
- `1.x.y`: Stable. Breaking changes require a major version bump. Public API frozen.
- All public API functions are annotated with `# Added in vX.Y.Z`.
