"""
rate_simulation_tests/sim_sustained_load.py
============================================
Simulates sustained traffic at a target RPS for a configured duration.
Measures acceptance rate without overwhelming the limiter.
Returns a result dict for the orchestrator.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rate_simulation_tests.token_bucket import TokenBucket
from app.engine import analyze_text


DURATION_SECONDS = 3       # Short wall-clock window for CI friendliness
TARGET_RPS       = 80      # Requests per second attempted
BUCKET_CAP       = 100
BUCKET_REFILL    = 100     # Same as target — should accept ~all


def run() -> dict:
    bucket    = TokenBucket(capacity=BUCKET_CAP, refill_rate=BUCKET_REFILL)
    interval  = 1.0 / TARGET_RPS   # seconds between requests

    attempts  = 0
    latencies = []
    t_end     = time.monotonic() + DURATION_SECONDS
    t0        = time.perf_counter()

    while time.monotonic() < t_end:
        attempts += 1
        if bucket.allow():
            t_req = time.perf_counter()
            analyze_text("sustained load test content")
            latencies.append((time.perf_counter() - t_req) * 1000)
        # throttle dispatcher to ~TARGET_RPS
        time.sleep(interval)

    elapsed = time.perf_counter() - t0
    stats   = bucket.stats
    actual_rps = attempts / elapsed

    return {
        "sim":            "sustained_load",
        "target_rps":     TARGET_RPS,
        "actual_rps":     round(actual_rps, 2),
        "duration_s":     DURATION_SECONDS,
        "attempts":       attempts,
        "accepted":       stats["accepted"],
        "rejected":       stats["rejected"],
        "rejection_rate": stats["rejection_rate"],
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 3),
        "wall_time_s":    round(elapsed, 3),
        # At ~TARGET_RPS with matching refill, rejection rate should be low
        "passed":         stats["rejection_rate"] < 0.15,
    }


if __name__ == "__main__":
    r = run()
    print(f"Sustained load: target={r['target_rps']} actual={r['actual_rps']} rps  "
          f"accepted={r['accepted']} rejected={r['rejected']}  "
          f"{'PASS' if r['passed'] else 'FAIL'}")
