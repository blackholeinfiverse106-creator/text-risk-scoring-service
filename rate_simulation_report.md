# Rate Simulation Report

**Generated:** 2026-02-21 12:44:47  
**Verdict:** `PASSED`  
**Total elapsed:** 4.60s

## Simulation 1 — Burst Flood

Fires **2,000 requests** instantly (no inter-request delay).
The token bucket must actively throttle.

| Metric | Value |
|--------|-------|
| Total requests | 2,000 |
| Accepted | 102 |
| Rejected (throttled) | 1898 |
| Rejection rate | 94.9% |
| Avg accepted latency | 0.383ms |
| Wall time | 0.041s |
| **Status** | **PASS** |

## Simulation 2 — Sustained Load

Sends **80 req/s** for **3s**.
With matching refill rate, most requests should be accepted.

| Metric | Value |
|--------|-------|
| Target RPS | 80 |
| Actual RPS | 72.62 |
| Accepted | 218 |
| Rejected | 0 |
| Rejection rate | 0.0% |
| Avg latency | 0.419ms |
| **Status** | **PASS** |

## Simulation 3 — Bursty Traffic

Alternates **3 quiet -> spike cycles**.
Proves limiter recovers between bursts and throttles spikes.

| Cycle | Quiet Accepted | Spike Accepted | Spike Throttled |
|-------|---------------|---------------|-----------------|
| 1 | 5 | 51 | 149 (YES) |
| 2 | 4 | 27 | 173 (YES) |
| 3 | 4 | 26 | 174 (YES) |

| **Status** | **PASS** |

## Token Bucket Configuration

| Parameter | Burst Flood | Sustained | Bursty |
|-----------|------------|-----------|--------|
| Capacity  | 100 tokens | 100 tokens | 50 tokens |
| Refill rate | 50 tok/s | 100 tok/s | 60 tok/s |

## Conclusion

All three rate simulation scenarios passed. The token bucket correctly throttles burst floods, accepts sustained traffic within bounds, and recovers between bursty spikes.