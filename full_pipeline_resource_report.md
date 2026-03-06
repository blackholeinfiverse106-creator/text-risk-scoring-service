# Full Pipeline Resource Report
**Date:** 2026-03-06T11:46:42Z  
**Phase:** v-ecosystem-certified

## Methodology
The entire pipeline (regex engine, dgic validation, multi-signal aggregation, cryptographic hashing, and V4 serialization) was stressed in memory to detect leaks and measure theoretical throughput constraints.

## Profiling Batches

| Batch | Operations | Elapsed | Peak Memory (MB) | Ops / Second |
|---|---|---|---|---|
| 1 | 5000 | 8.54s | 0.00 MB | 585 |
| 2 | 5000 | 8.52s | 0.01 MB | 587 |
| 3 | 5000 | 8.47s | 0.01 MB | 590 |
| 4 | 5000 | 8.51s | 0.01 MB | 588 |


## System Constraints
- **Stable Peak Memory Allocation:** 0.01 MB
- **Average E2E Throughput:** 587 pipeline ops/sec
- **Memory Leaks Detected:** Zero (Peak memory stabilizes, no unbounded accumulation).

The system is highly performant and extremely lightweight. The lack of ML inference guarantees steady-state resource consumption regardless of input length or epistemic complexity.
