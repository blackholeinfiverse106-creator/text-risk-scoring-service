# Resource Boundary Model

**Generated:** 2026-02-21 12:33:53  
**Reps per profile:** 20  
**CPU threshold:** 500ms  
**Memory threshold:** 1024KB  
**Verdict:** `BOUNDED`

## Big-O Analysis

| Dimension | Complexity | Ceiling |
|-----------|-----------|---------|
| Time      | O(N * K)  | N=5000 chars, K~100 keywords => O(1) bounded |
| Space     | O(N)      | N=5000 => at most 5KB string allocation |

> Both N and K are hard-capped constants.
> The engine is effectively O(1) with a fixed constant factor.

## Empirical Measurements

| Profile | Wall Median | Wall Max | CPU Max | Mem Max (KB) | CPU OK | Mem OK |
|---------|------------|---------|---------|-------------|--------|--------|
| `best_case_empty` | 0.009ms | 0.076ms | 0.0ms | 1.1 | **PASS** | **PASS** |
| `best_case_no_keywords` | 1.317ms | 13.918ms | 15.625ms | 77.7 | **PASS** | **PASS** |
| `nominal_1_keyword` | 1.141ms | 2.226ms | 15.625ms | 0.6 | **PASS** | **PASS** |
| `nominal_5_keywords` | 1.354ms | 2.096ms | 15.625ms | 0.7 | **PASS** | **PASS** |
| `nominal_10_keywords` | 1.52ms | 2.437ms | 15.625ms | 0.7 | **PASS** | **PASS** |
| `medium_length_no_hit` | 9.443ms | 10.611ms | 15.625ms | 0.7 | **PASS** | **PASS** |
| `max_length_no_hit` | 17.528ms | 19.449ms | 31.25ms | 0.7 | **PASS** | **PASS** |
| `max_length_all_keywords` | 5.571ms | 6.39ms | 15.625ms | 0.7 | **PASS** | **PASS** |
| `over_limit` | 17.422ms | 25.045ms | 31.25ms | 0.7 | **PASS** | **PASS** |
| `invalid_type` | 0.006ms | 0.022ms | 0.0ms | 0.7 | **PASS** | **PASS** |

## Capacity Planning

```
Worst-case wall time (max across all profiles): 25.05ms
Single-core max throughput (1000 / worst_ms):  39.9 req/s

Multi-core formula:
  max_rps_total = cores * (1000 / p99_single_thread_ms)
  Example at 4 cores: 160 req/s
  Example at 8 cores: 319 req/s
```

## Resource Guard Settings (from resource-guard.md)

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| Payload size | 5000 chars | Hard truncation in `engine.py` |
| Memory per request | <1 MB delta | Empirically verified above |
| Response latency P99 | <500ms | Verified by `concurrency_stress.py` |

## Conclusion

All 10 profile points stayed within CPU and memory thresholds. Worst-case call: **25.05ms** wall time. Single-core capacity: **39.9 req/s**.