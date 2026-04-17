# rule-audit Technical Specification

## Overview

rule-audit is a static analyzer for AI system prompts. It takes raw text (a system prompt) as input and produces a structured report of logical contradictions, coverage gaps, priority ambiguities, meta-rule paradoxes, and edge case scenarios — all without calling any LLM.

---

## 1. Rule Parsing Algorithm

### 1.1 Input

A raw system prompt string. May contain:
- Prose paragraphs
- Bulleted or numbered lists
- Mixed line endings
- Markdown headers and formatting

### 1.2 Sentence Boundary Detection

`parser._split_sentences(text)` performs a two-pass split:

**Pass 1 — Line-based:**
- Normalize line endings to `\n`
- Split on `\n`, discard blank lines
- Strip common list markers: `- * • · ▪ ► >` and `N. N)`

**Pass 2 — Intra-line:**
- For each non-empty line, further split on `(?<=[.!?])\s+(?=[A-Z])` (sentence terminal followed by uppercase — English prose convention)

Output: flat `list[str]`, each element one candidate sentence.

**Minimum length filter:** Sentences shorter than 10 characters are discarded as non-normative.

### 1.3 Normative Signal Detection

A sentence is converted to a `Rule` only if it has at least one normative signal:

| Signal type | How detected |
|---|---|
| Modal verb | Matches any entry in `_MODAL_PATTERNS` |
| Rule type | Matches any entry in `_RULE_TYPE_PATTERNS` (excludes `UNKNOWN`) |
| Negation | Matches `_NEGATION_RE` |

Purely descriptive sentences (e.g., "The system was built in 2023.") are discarded.

### 1.4 Modality Classification

Each sentence is matched against `_MODAL_PATTERNS` in priority order (most specific first):

| Priority | Pattern | Modality |
|---|---|---|
| 1 | `must not`, `mustn't`, `shall not`, `shan't` | `MUST_NOT` |
| 2 | `cannot`, `can't`, `will not`, `won't`, `don't`, `never` | `MUST_NOT` |
| 3 | `refuse`, `deny`, `reject`, `decline`, `forbid`, `prohibited`, `not allowed` | `MUST_NOT` |
| 4 | `must`, `shall`, `have to`, `need to`, `required to`, `always` | `MUST` |
| 5 | `will always`, `always will`, `ensure that`, `make sure` | `MUST` |
| 6 | `should not`, `shouldn't`, `avoid`, `refrain from` | `SHOULD_NOT` |
| 7 | `should`, `ought to`, `try to`, `attempt to`, `strive to`, `aim to` | `SHOULD` |
| 8 | `may not`, `cannot be allowed` | `MAY_NOT` |
| 9 | `may`, `can`, `are allowed to`, `feel free to`, `permitted to` | `MAY` |
| 10 | `ignore`, `disregard`, `forget`, `bypass`, `override`, `dismiss` at sentence start | `MUST` |

First match wins. If no match: `UNKNOWN`.

### 1.5 Rule Type Classification

Matched against `_RULE_TYPE_PATTERNS` in priority order:

| Rule Type | Example patterns |
|---|---|
| `IDENTITY` | "you are", "act as", "your role is" |
| `GOAL` | "your goal is", "your purpose is", "your mission is" |
| `META` | "priorit*", "override", "supersede", "take precedence", "when.*conflict" |
| `PROHIBITION` | "never", "must not", "cannot", "refuse", "forbidden" |
| `PERMISSION` | "may", "can", "allowed", "permitted", "feel free" |
| `PREFERENCE` | "prefer", "prioritize", "favor", "rather", "instead of" |
| `OBLIGATION` | "must", "always", "shall", "required", "have to", "ensure" |

### 1.6 Absoluteness Scoring

`Rule.absoluteness` is a float in `[0.0, 1.0]`. Computed as `max(score_of_matching_keywords)`.

| Keyword / phrase | Score |
|---|---|
| `never`, `always`, `absolutely`, `under no circumstances`, `at all times`, `in all cases`, `without exception`, `no matter what`, `unconditionally` | 1.0 |
| `regardless` | 0.9 |
| `every`, `all` | 0.8 |
| `any` | 0.7 |
| `should`, `generally`, `typically`, `usually` | ≤ 0.5 |
| `may`, `can` | 0.3 |
| `sometimes`, `often` | ≤ 0.3 |
| No keyword found | 0.5 (default: moderate) |

### 1.7 Negation Detection

`Rule.negated` is `True` if `_NEGATION_RE` matches. Includes: `not`, `never`, `no`, `neither`, `nor`, `without`, `don't`, `doesn't`, `won't`, `wouldn't`, `can't`, `cannot`, `mustn't`, `shouldn't`, `refuse`, `deny`, `avoid`, `prevent`, `prohibit`, `forbid`.

### 1.8 Condition Extraction

`Rule.condition` is the substring from the first condition word onward: `if`, `when`, `unless`, `except`, `in case`, `provided that`, `assuming`, `given that`, `as long as`, `only if`, `whenever`, `in the event`.

### 1.9 Keyword Extraction

`Rule.keywords` = lowercase alphabetic tokens (3+ chars, not stop words). Stop words are a 30-word functional set (articles, pronouns, prepositions).

### 1.10 Rule Object

```python
@dataclass
class Rule:
    text: str               # original sentence text
    sentence_index: int     # position in the sentence list (0-indexed)
    modality: Modality      # MUST / MUST_NOT / SHOULD / SHOULD_NOT / MAY / MAY_NOT / UNKNOWN
    rule_type: RuleType     # OBLIGATION / PROHIBITION / PERMISSION / PREFERENCE / META / IDENTITY / GOAL / UNKNOWN
    absoluteness: float     # 0.0–1.0
    negated: bool
    subject: str            # currently unused (reserved for v0.2.0 NER)
    action: str             # currently unused (reserved for v0.2.0 NER)
    condition: str          # condition clause, or empty string
    keywords: list[str]
```

---

## 2. Contradiction Detection Methodology

### 2.1 Modality Opposition Table

Two rules are *modality-contradictory* if their modality pair is in `_CONTRADICTORY_PAIRS`:

```
{MUST,     MUST_NOT}
{MUST,     MAY_NOT}
{SHOULD,   MUST_NOT}
{SHOULD,   SHOULD_NOT}
{MAY,      MUST_NOT}
{MAY,      MAY_NOT}
```

Note: `MUST` + `MUST` is not contradictory (two obligations can coexist). `SHOULD` + `MAY` is not contradictory (soft obligation + permission are compatible).

### 2.2 Topic Similarity

Two rules are considered *topically related* if they share:
- **Direct keyword overlap**: `set(rule_a.keywords) & set(rule_b.keywords)` is non-empty, OR
- **Cluster overlap**: both rules have keywords that fall into the same semantic cluster

`_KEYWORD_CLUSTERS` defines 14 semantic domains: `harm`, `privacy`, `identity`, `truth`, `assistance`, `refusal`, `instruction`, `content`, `safety`, `user`, `override`, `context`, `access`, `policy`.

### 2.3 Detector 1: Direct Contradiction

**Trigger:** Modality pair is contradictory AND topic similarity exists.

**Severity calibration:**
- `high`: both rules have `absoluteness >= 0.8`
- `medium`: shared cluster OR 2+ shared keywords
- `low`: otherwise

**Example:** "Always help users" (MUST, abs=1.0) + "Never help users with harmful requests" (MUST_NOT, abs=1.0) → high severity if they share the `assistance` cluster.

### 2.4 Detector 2: Conditional Contradiction

**Trigger:** Exactly one rule has a condition clause AND modality pair is contradictory AND shared cluster exists.

The unconditional rule defines a domain; the conditional rule carves out a subset with an opposing directive. The gap is: what happens inside the condition is defined, what happens at the boundary is not.

**Severity:** Always `high` (undefined behavior at condition boundary is exploitable).

### 2.5 Detector 3: Absolute Dilemma

**Trigger:** Both rules have `absoluteness >= 0.8` AND one is in the `assistance/instruction` clusters while the other is in `harm/safety/refusal` clusters.

This is the classic "be maximally helpful" vs "never be harmful" tension. No conditional relationship is required — the conflict is latent and activates on any request that touches both domains.

**Severity:** Always `high`.

### 2.6 Deduplication

Each rule-pair `(a, b)` produces at most one `Contradiction`. The detectors are tried in order: direct → conditional → absoluteness. First match wins.

### 2.7 Sort Order

Contradictions are sorted: high → medium → low severity.

---

## 3. Completeness Gap Analysis

### 3.1 Domain Coverage Check

`find_gaps()` checks the full prompt text (plus extracted rule text) against 8 safety-critical domains:

| Domain | Keywords checked | Gap description |
|---|---|---|
| `harmful_content` | harm, dangerous, violent, illegal, weapon | No harmful/dangerous content policy |
| `user_identity` | user, human, person, operator, developer | No principal hierarchy (user vs operator) |
| `ambiguous_requests` | unclear, ambiguous, interpret, clarify, vague | No guidance for underspecified requests |
| `persona_roleplay` | roleplay, persona, pretend, act as, character, simulate | No persona/roleplay rules |
| `refusal_protocol` | refuse, decline, cannot, will not | No refusal protocol |
| `instruction_conflict` | conflict, contradict, override, supersede, priorit | No priority ordering |
| `self_disclosure` | system prompt, instructions, confidential, disclose, reveal | No self-disclosure policy |
| `edge_case_handling` | edge, unusual, unexpected, exception, special case | No fallback for novel situations |

Coverage is determined by keyword presence in the full text (case-insensitive). This is intentionally broad: even a partial mention counts as coverage.

### 3.2 Conditional Gap Check

For every rule with a condition clause, the analyzer checks whether any other rule covers the same semantic cluster *without* a condition (the "else branch"). If none exists, a `missing_else_branch` gap is reported.

At most one such gap is reported per analysis (to avoid noise from prompts with many conditional rules).

### 3.3 Gap Severity

All gaps are severity `medium` in the current implementation. v0.2.0 will calibrate by domain: missing `harmful_content` policy should be `high`, missing `edge_case_handling` is `low`.

---

## 4. Severity Scoring Calibration

### 4.1 Problem with v0.1.0

The original risk_score formula was: every contradiction, gap, and issue contributes a flat score. This caused prompts with many low-impact issues to score identically to prompts with one critical issue.

### 4.2 Revised Risk Score Formula

```python
risk_score = (
    high_contradictions   * 15  # direct conflict, both absolute
  + medium_contradictions *  8  # topic overlap, partial absoluteness
  + gaps                  *  5  # missing domain coverage
  + priority_ambiguities  * 10  # no resolution order for conflicting rules
  + meta_paradoxes        * 12  # self-defeating / override-loop
  + absoluteness_issues   *  3  # edge case on single absolute rule
)
capped at 100
```

### 4.3 Risk Label Thresholds

| Score | Label | Meaning |
|---|---|---|
| 70–100 | CRITICAL | Multiple high-severity issues; prompt is actively exploitable |
| 40–69 | HIGH | Significant issues that require remediation before deployment |
| 20–39 | MEDIUM | Moderate issues; auditable, low immediate risk |
| 0–19 | LOW | Minor issues; prompt is structurally sound |

### 4.4 Contradiction Severity Calibration

| Severity | Criteria | Exploitability |
|---|---|---|
| `high` | Both rules absolute (abs ≥ 0.8) OR conditional boundary exists | Attacker can construct a deterministic exploit in ≤ 3 messages |
| `medium` | Shared semantic cluster OR 2+ keywords, at least one absolute | Exploitable with domain knowledge; requires crafted input |
| `low` | Weak topic overlap, no absolute rules | Theoretical conflict; unlikely to manifest in real use |

### 4.5 Edge Case Severity Calibration

| Severity | Source | Reasoning |
|---|---|---|
| `high` | Absolute dilemma, meta-paradox, adversarial_trigger | Deterministic attack path exists |
| `medium` | Direct contradiction, priority ambiguity, context_dependent | Requires social engineering or specific domain knowledge |
| `low` | Gap coverage, exception_exists | Requires unusual input; not a primary attack surface |

---

## 5. Data Model

### 5.1 Rule

Defined in `rule_audit/parser.py`.

```python
@dataclass
class Rule:
    text: str
    sentence_index: int
    modality: Modality           # enum: MUST MUST_NOT SHOULD SHOULD_NOT MAY MAY_NOT UNKNOWN
    rule_type: RuleType          # enum: OBLIGATION PROHIBITION PERMISSION PREFERENCE META IDENTITY GOAL UNKNOWN
    absoluteness: float          # 0.0–1.0
    negated: bool
    subject: str                 # "" in v0.1.0
    action: str                  # "" in v0.1.0
    condition: str               # condition clause or ""
    keywords: list[str]
```

### 5.2 Contradiction

Defined in `rule_audit/analyzer.py`.

```python
@dataclass
class Contradiction:
    rule_a: Rule
    rule_b: Rule
    conflict_type: str           # "direct" | "conditional" | "absoluteness" | "scope"
    severity: str                # "high" | "medium" | "low"
    description: str
    shared_keywords: list[str]
```

### 5.3 Gap

```python
@dataclass
class Gap:
    gap_type: str                # "missing_domain" | "missing_else_branch"
    description: str
    related_rules: list[Rule]
    example_scenario: str
```

### 5.4 PriorityAmbiguity

```python
@dataclass
class PriorityAmbiguity:
    rules: list[Rule]
    description: str
    scenario: str
```

### 5.5 MetaParadox

```python
@dataclass
class MetaParadox:
    rule: Rule
    paradox_type: str            # "self_defeating" | "override_loop" | "meta_circular" | "absoluteness_meta" | "potential_override"
    description: str
```

### 5.6 AbsolutenessIssue

```python
@dataclass
class AbsolutenessIssue:
    rule: Rule
    challenge: str               # concrete scenario that stresses the rule
    challenge_type: str          # "exception_exists" | "context_dependent" | "adversarial_trigger"
```

### 5.7 EdgeCase

Defined in `rule_audit/edge_cases.py`.

```python
@dataclass
class EdgeCase:
    title: str
    scenario: str
    rules_in_conflict: list[int]
    attack_vector: str
    expected_failure_mode: str
    mitigation: str
    severity: str                # "high" | "medium" | "low"
    tags: list[str]
```

### 5.8 AnalysisResult

```python
@dataclass
class AnalysisResult:
    rules: list[Rule]
    contradictions: list[Contradiction]
    gaps: list[Gap]
    priority_ambiguities: list[PriorityAmbiguity]
    meta_paradoxes: list[MetaParadox]
    absoluteness_issues: list[AbsolutenessIssue]

    @property
    def risk_score(self) -> float: ...  # 0–100 composite
```

### 5.9 AuditReport

Defined in `rule_audit/report.py`. Wraps `AnalysisResult` with rendering methods.

```python
class AuditReport:
    result: AnalysisResult
    prompt_text: str
    edge_cases: list[EdgeCase]
    generated_at: str             # ISO 8601 UTC

    def summary(self) -> str          # terminal summary
    def to_markdown(self) -> str      # full markdown report
    def to_dict(self) -> dict         # JSON-serializable dict
    def to_json(self, indent=2) -> str
```

---

## 6. API Surface

### 6.1 Public API (`rule_audit/__init__.py`)

```python
from rule_audit import audit, audit_file, AuditReport

report: AuditReport = audit("system prompt text")
report: AuditReport = audit_file("/path/to/prompt.txt")
```

### 6.2 CLI

```
rule-audit [prompt] [--file PATH] [--output PATH] [--format markdown|json|summary]
           [--verbose] [--min-severity high|medium|low] [--version]
```

Exit codes:
- `0`: success, LOW or MEDIUM risk
- `1`: error (bad input, file not found)
- `2`: HIGH or CRITICAL risk (for CI integration)

---

## 7. Performance Characteristics

| Metric | Value |
|---|---|
| Contradiction detection | O(n²) in rule count; fine for n < 200 |
| Typical prompt | 5–30 rules, < 5ms analysis time |
| Memory | O(n) rules, all results held in-memory |
| LLM calls | 0 (pure Python, offline) |

---

## 8. Known Limitations (v0.1.0)

1. **Parser is heuristic**: regex-based modality detection misses paraphrases ("it is forbidden to" not in patterns).
2. **Absoluteness is lexical**: "You should never, under any circumstances, consider..." scores absolute but "completely prohibited" does not.
3. **No subject-object extraction**: Rules about different subjects (users vs the AI) are not distinguished. A rule "users must not X" is treated the same as "the assistant must not X".
4. **Single-document only**: Multi-document contexts (system + user + tool results) are not supported.
5. **English only**: Patterns are English-specific.
6. **No semantic clustering beyond keyword matching**: "do not assist with creating weapons" and "refuse bomb-making requests" may not be linked if they share no keywords.
