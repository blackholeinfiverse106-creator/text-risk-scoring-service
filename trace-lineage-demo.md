# Trace Lineage Demo

**Generated:** 2026-02-21 13:02:53  
**Verdict:** `TRACE LINEAGE PROVEN`

## Method

Three requests with distinct correlation IDs were run against the live engine.
All JSON log entries were captured and parsed. For each request, we verified:

1. Every log entry carries the correct `correlation_id`
2. The expected event sequence is present (`analysis_start → analysis_complete`)
3. Score can be fully reconstructed from the log stream alone
4. No correlation IDs bleed across requests

## Per-Request Trace

| Correlation ID | Log Entries | Category | Replayed Score | Status |
|---|---|---|---|---|
| `TRACE-001` | 3 | LOW | 0 | **PROVEN** |
| `TRACE-002` | 11 | HIGH | 1.0 | **PROVEN** |
| `TRACE-003` | 8 | MEDIUM | 0.6 | **PROVEN** |

## Event Sequences

### `TRACE-001`
`analysis_start → input_received → analysis_complete`

### `TRACE-002`
`analysis_start → input_received → keyword_detected → keyword_detected → keyword_detected → keyword_detected → keyword_detected → keyword_detected → category_capped → keyword_detected → analysis_complete`

### `TRACE-003`
`analysis_start → input_received → keyword_detected → keyword_detected → keyword_detected → keyword_detected → category_capped → analysis_complete`

## Cross-Contamination Result

No unexpected correlation IDs appeared in the log stream.

## Conclusion

**TRACE LINEAGE PROVEN** — every log entry is correctly tagged with its originating
`correlation_id`. The log stream is a complete, replayable audit trail for each
request independently. No cross-request contamination detected.