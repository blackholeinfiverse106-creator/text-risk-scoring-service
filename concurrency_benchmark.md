# Concurrency Benchmark Report

**Generated:** 2026-02-21 12:33:49  
**Concurrency:** 500 simultaneous threads  
**Total Requests:** 500  
**Verdict:** `PASSED`

## Latency Percentiles

| Metric | Value |
|--------|-------|
| Mean   | 2.42 ms |
| StdDev | 5.70 ms |
| Min    | 0.00 ms |
| P50    | 0.37 ms |
| P95    | 16.39 ms |
| P99    | 17.23 ms |
| Max    | 35.76 ms |

## Throughput

- **Requests/sec:** 416.0
- **Wall time:** 1.20s for 500 requests
- **Failures:** 0

## Pass Criteria

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Zero failures | 0 | 0 | PASS |
| P99 latency   | <500ms | 17.2ms | PASS |

## Conclusion

The engine handled **500 simultaneous requests** with zero failures and P99 latency of **17.2ms** — well within the 500ms safety threshold.