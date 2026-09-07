# rule-audit benchmarks

Deterministic finding counts per sample prompt. Regression gate for detector changes.

## Run

```bash
pip install -e ".[dev]"

# One file
python -m rule_audit --file samples/basic_assistant.txt --format summary

# All samples
for f in samples/*.txt; do
  echo "=== $f ==="
  python -m rule_audit --file "$f" --format summary
  echo ""
done

# As JSON for scripting
python -m rule_audit --file samples/enterprise_rag.txt --format json > report.json
jq '.summary' report.json
```

## Expected finding counts (v0.3.1)

These are **exact** deterministic outputs. Any drift should be investigated before merging detector changes.

| Sample | Rules | Contradictions (H / M) | Gaps | Priority ambig. | Meta-paradoxes | Absoluteness issues | Edge cases | Risk |
|---|---|---|---|---|---|---|---|---|
| `basic_assistant.txt` | 17 | 18 (17 / 0) | 2 | 3 | 0 | 18 | 83 | 100 / CRITICAL |
| `code_assistant.txt` | 23 | 59 (43 / 16) | 6 | 4 | 0 | 17 | 146 | 100 / CRITICAL |
| `content_moderator.txt` | 26 | 98 (86 / 12) | 2 | 0 | 0 | 25 | 197 | 100 / CRITICAL |
| `customer_support.txt` | 19 | 39 (38 / 1) | 5 | 4 | 0 | 15 | 114 | 100 / CRITICAL |
| `enterprise_rag.txt` | 24 | 73 (56 / 12) | 3 | 7 | 0 | 26 | 165 | 100 / CRITICAL |

Note: all five canned samples intentionally score CRITICAL — they reproduce the contradiction classes real production prompts ship with.

### Why the total is not high + medium

Contradictions carry one of **three** severities, not two. `_is_direct_contradiction` in `rule_audit/analyzer.py` assigns `low` when the pair is not both absolute (absoluteness ≥ 0.8 on each side) and shares no keyword cluster and at most one keyword; the other detectors emit only `high` or `medium`. The `(H / M)` column mirrors `--format summary`, which prints only the high and medium counts. So `total − H − M` is the low-severity count, not an accounting error. `--format json` exposes it as `summary.contradictions_low`, and `tests/test_benchmark.py` pins it:

| Sample | Low-severity contradictions |
|---|---|
| `basic_assistant.txt` | 1 |
| `enterprise_rag.txt` | 5 |
| all others | 0 |

### History of this table

The counts shipped with v0.1.0 (21 / 65 / 101 / 49 / 85 contradictions) did not match the analyzer at any committed revision: the v0.1.0 tree itself already produced the totals above, and the only pinned assertions were `>=` thresholds, so nothing caught it. The high / medium split then moved in 0.2.0 (PR #9), which reordered the detectors in `find_contradictions` so `_is_conditional_contradiction` runs before `_is_direct_contradiction`; the first detector to match a pair wins, and the conditional detector always reports `high`, so some pairs moved from `medium` to `high` without changing totals. The table was reconciled against 0.3.1 and every column is now asserted exactly.

## Performance

Measured on an M-series Mac, Python 3.12, single process:

| Metric | Value |
|---|---|
| Parse + analyze + edge-case generation per prompt | < 50 ms |
| Full audit of all 5 samples | < 250 ms |
| LLM calls | 0 |
| Network calls | 0 |

Reproduce:

```bash
python3 -c "
import time
from rule_audit import audit_file
for f in ['basic_assistant','code_assistant','content_moderator','customer_support','enterprise_rag']:
    t=time.perf_counter()
    r=audit_file(f'samples/{f}.txt')
    dt=(time.perf_counter()-t)*1000
    print(f'{f:<22s} {dt:6.1f} ms  risk={r.risk_score:.0f}')
"
```

## Regression gate

The test suite in `tests/test_benchmark.py` asserts these counts against the sample corpus. Running:

```bash
pytest tests/test_benchmark.py -v
```

…must pass on every PR. If a detector change legitimately shifts counts, update both this table and the benchmark asserts in the same PR.
