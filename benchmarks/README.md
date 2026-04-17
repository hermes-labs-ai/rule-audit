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

## Expected finding counts (v0.1.0)

These are **exact** deterministic outputs. Any drift should be investigated before merging detector changes.

| Sample | Rules | Contradictions (H / M) | Gaps | Priority ambig. | Meta-paradoxes | Absoluteness issues | Edge cases | Risk |
|---|---|---|---|---|---|---|---|---|
| `basic_assistant.txt` | 17 | 21 (17 / 3) | 2 | 3 | 0 | 18 | 85 | 100 / CRITICAL |
| `code_assistant.txt` | 23 | 65 (45 / 20) | 6 | 4 | 0 | 17 | 151 | 100 / CRITICAL |
| `content_moderator.txt` | 26 | 101 (83 / 17) | 2 | 0 | 0 | 25 | 200 | 100 / CRITICAL |
| `customer_support.txt` | 19 | 49 (45 / 3) | 5 | 4 | 0 | 15 | 122 | 100 / CRITICAL |
| `enterprise_rag.txt` | 24 | 85 (59 / 18) | 3 | 7 | 0 | 26 | 175 | 100 / CRITICAL |

Note: all five canned samples intentionally score CRITICAL — they reproduce the contradiction classes real production prompts ship with.

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
