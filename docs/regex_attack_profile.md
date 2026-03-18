# Regex Attack Profile

**Generated:** 2026-02-21 12:33:37  
**Threshold:** 200ms per call  
**Reps per pattern:** 10  
**Verdict:** `SAFE`

## Pattern Timing Results

| Pattern | Median (ms) | Max (ms) | Risk Score | Safe? |
|---------|------------|---------|------------|-------|
| `max_length_all_keywords` | 3.904 | 9.12 | 1.0 | **SAFE** |
| `max_length_zero_match` | 18.927 | 21.556 | 0.0 | **SAFE** |
| `padded_keywords` | 15.825 | 17.282 | 0.0 | **SAFE** |
| `alternating_case` | 20.564 | 22.187 | 0.6 | **SAFE** |
| `near_miss_keywords` | 21.883 | 23.039 | 0.0 | **SAFE** |
| `redos_bait_string` | 18.158 | 21.517 | 0.0 | **SAFE** |
| `boundary_stress` | 19.595 | 26.209 | 0.2 | **SAFE** |
| `unicode_keyword_mix` | 21.83 | 54.615 | 0.6 | **SAFE** |
| `empty` | 0.003 | 0.036 | 0.0 | **SAFE** |
| `single_short_keyword` | 0.262 | 0.584 | 0.2 | **SAFE** |

## Regex Pattern Introspection

Analysed **181 regex patterns** (one per keyword) across all categories.

| Check | Result |
|-------|--------|
| Patterns with nested quantifiers | 0 |
| Patterns with lookarounds | 0 |
| All patterns safe | YES |

All patterns use the form `\bLITERAL\b` — `re.escape()` prevents
any special character injection. Word boundaries are O(1). No backtracking risk.

## ReDoS Immunity Explanation

The engine uses `re.search(r'\b' + re.escape(keyword) + r'\b', text)`.

- `re.escape()` neutralises all regex metacharacters in keywords.
- No nested quantifiers (`(a+)+`, `(a*)*`) — immune to exponential backtrack.
- No alternation of overlapping patterns in a single `re.search` call.
- Each keyword is searched independently — worst case is linear `O(N * K)`
  where N=5000 (capped) and K ~100 keywords.

## Conclusion

All 10 adversarial patterns completed within 200ms. No ReDoS vulnerability detected.