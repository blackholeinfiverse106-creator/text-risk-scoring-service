"""
rate_simulation_tests/sim_burst_flood.py
=========================================
Simulates a 2000-request burst flood in negligible wall time.
Returns a result dict for the orchestrator.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rate_simulation_tests.token_bucket import TokenBucket
from app.engine import analyze_text


BURST_SIZE    = 2000
BUCKET_CAP    = 100
BUCKET_REFILL = 50   # tokens/sec — deliberate limiting


def run(text: str = "test flood request") -> dict:
    bucket = TokenBucket(capacity=BUCKET_CAP, refill_rate=BUCKET_REFILL)

    latencies = []
    t0 = time.perf_counter()

    for _ in range(BURST_SIZE):
        if bucket.allow():
            t_req = time.perf_counter()
            analyze_text(text)
            latencies.append((time.perf_counter() - t_req) * 1000)

    elapsed = time.perf_counter() - t0
    stats   = bucket.stats

    return {
        "sim":           "burst_flood",
        "total_requests": BURST_SIZE,
        "accepted":      stats["accepted"],
        "rejected":      stats["rejected"],
        "rejection_rate": stats["rejection_rate"],
        "protection_active": stats["rejected"] > 0,
        "wall_time_s":   round(elapsed, 3),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 3),
        "passed":        stats["rejected"] > 0,   # must actually throttle
    }


if __name__ == "__main__":
    r = run()
    print(f"Burst flood: accepted={r['accepted']} rejected={r['rejected']} "
          f"rate={r['rejection_rate']:.1%}  wall={r['wall_time_s']}s  "
          f"{'PASS' if r['passed'] else 'FAIL'}")
