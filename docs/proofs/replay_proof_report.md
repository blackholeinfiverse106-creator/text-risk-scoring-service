# Replay Proof Report

**Generated:** 2026-02-21 11:22:26
**Iterations per case:** 10,000
**Verdict:** `PROVEN`

## Results

| Case | Status | Iterations | Divergences | Baseline Hash |
|------|--------|-----------|-------------|---------------|
| `clean_text` | **PASS** | 10,000 | 0 | `36bebb5401a61212...` |
| `single_violence_keyword` | **PASS** | 10,000 | 0 | `15e1ca8c4cc9e11f...` |
| `single_fraud_keyword` | **PASS** | 10,000 | 0 | `56bca6407c0fa45c...` |
| `multi_category_high` | **PASS** | 10,000 | 0 | `18f9030a2db9e46b...` |
| `max_length_safe` | **PASS** | 10,000 | 0 | `26086afb87b96849...` |
| `over_max_length` | **PASS** | 10,000 | 0 | `d49de985f70345db...` |
| `empty_string` | **PASS** | 10,000 | 0 | `feb091fb4a0b0267...` |
| `whitespace_only` | **PASS** | 10,000 | 0 | `feb091fb4a0b0267...` |
| `mixed_case_normalization` | **PASS** | 10,000 | 0 | `c2af2311fea46594...` |
| `unicode_content` | **PASS** | 10,000 | 0 | `f9dcf9d5fc37cb74...` |
| `repeated_same_keyword` | **PASS** | 10,000 | 0 | `6a8a4de6a7c3e53f...` |
| `special_characters` | **PASS** | 10,000 | 0 | `a4f1ac05e7f363f3...` |
| `none_type` | **PASS** | 10,000 | 0 | `7d15ebeaa44c2781...` |
| `integer_type` | **PASS** | 10,000 | 0 | `7d15ebeaa44c2781...` |
| `newlines_in_text` | **PASS** | 10,000 | 0 | `59ec7f3280f54040...` |

## Summary

- **Cases Passed:** 15/15
- **Cases Failed:** 0/15
- **Total Executions:** 150,000
- **Total Elapsed:** 415.86s

## Hash Contract

The semantic hash covers exactly: `risk_score`, `confidence_score`,
`risk_category`, `trigger_reasons` (sorted), `processed_length`.
Excluded: `correlation_id`, log timestamps, `errors.message` (free-text).

## Conclusion

Zero divergence detected across **150,000 total executions**. The engine is deterministic under all tested input conditions.