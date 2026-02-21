"""
rate_simulation_tests/sim_bursty_traffic.py
============================================
Simulates alternating quiet periods and sudden spikes (realistic traffic).
Uses fixed-count request bursts (not time-based tight loops) for
deterministic behaviour on Windows where sleep resolution is ~15ms.
Returns a result dict for the orchestrator.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rate_simulation_tests.token_bucket import TokenBucket
from app.engine import analyze_text


QUIET_REQUESTS  = 5      # small number during quiet phase
SPIKE_REQUESTS  = 200    # guaranteed > BUCKET_CAP — always triggers throttle
CYCLES          = 3
BUCKET_CAP      = 50
BUCKET_REFILL   = 60     # tokens/sec — recovers between cycles


def run() -> dict:
    bucket = TokenBucket(capacity=BUCKET_CAP, refill_rate=BUCKET_REFILL)

    cycles_data = []
    t0 = time.perf_counter()

    for cycle in range(CYCLES):
        # ── QUIET PHASE — few requests, bucket refills ─────────
        q_accepted = q_rejected = 0
        for _ in range(QUIET_REQUESTS):
            if bucket.allow():
                analyze_text("quiet background request")
                q_accepted += 1
            else:
                q_rejected += 1
            time.sleep(0.1)   # spread quiet phase so bucket refills

        # ── SPIKE PHASE — fires SPIKE_REQUESTS all at once ────
        # SPIKE_REQUESTS >> BUCKET_CAP, so throttling is guaranteed
        s_accepted = s_rejected = 0
        for _ in range(SPIKE_REQUESTS):
            if bucket.allow():
                analyze_text("kill scam attack burst request")
                s_accepted += 1
            else:
                s_rejected += 1

        cycles_data.append({
            "cycle":          cycle + 1,
            "quiet":          {"accepted": q_accepted, "rejected": q_rejected},
            "spike":          {"accepted": s_accepted, "rejected": s_rejected},
            "spike_throttled": s_rejected > 0,
        })

    elapsed = time.perf_counter() - t0
    stats   = bucket.stats

    total_spike_rejected = sum(c["spike"]["rejected"] for c in cycles_data)
    all_spikes_throttled = all(c["spike_throttled"] for c in cycles_data)

    return {
        "sim":                  "bursty_traffic",
        "cycles":               CYCLES,
        "total_accepted":       stats["accepted"],
        "total_rejected":       stats["rejected"],
        "spike_throttled_all":  all_spikes_throttled,
        "total_spike_rejected": total_spike_rejected,
        "cycles_data":          cycles_data,
        "wall_time_s":          round(elapsed, 3),
        "passed":               all_spikes_throttled,
    }


if __name__ == "__main__":
    r = run()
    for c in r["cycles_data"]:
        print(f"  Cycle {c['cycle']}: quiet(ok={c['quiet']['accepted']}) | "
              f"spike(ok={c['spike']['accepted']} throttled={c['spike']['rejected']})")
    print(f"Bursty: spikes_throttled={r['spike_throttled_all']}  "
          f"{'PASS' if r['passed'] else 'FAIL'}")
