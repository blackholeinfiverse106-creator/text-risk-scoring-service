#!/usr/bin/env python3
"""
rate_simulation_tests/run_all_sims.py — Rate Simulation Orchestrator
======================================================================
Runs all three rate simulations and merges results into:
  - rate_simulation_log.json
  - rate_simulation_report.md

Exit code: 0 = all passed, 1 = any failed
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging as _logging
_logging.getLogger("app.engine").setLevel(_logging.CRITICAL)
_logging.getLogger().setLevel(_logging.CRITICAL)

from rate_simulation_tests import sim_burst_flood, sim_sustained_load, sim_bursty_traffic


def run_all():
    print("[rate_sims] Running Burst Flood simulation...")
    t0 = time.perf_counter()
    burst = sim_burst_flood.run()
    print(f"  accepted={burst['accepted']}  rejected={burst['rejected']}  "
          f"rate={burst['rejection_rate']:.1%}  {'PASS' if burst['passed'] else 'FAIL'}")

    print("[rate_sims] Running Sustained Load simulation...")
    sustained = sim_sustained_load.run()
    print(f"  target={sustained['target_rps']} actual={sustained['actual_rps']} rps  "
          f"rejected={sustained['rejected']}  {'PASS' if sustained['passed'] else 'FAIL'}")

    print("[rate_sims] Running Bursty Traffic simulation...")
    bursty = sim_bursty_traffic.run()
    for c in bursty["cycles_data"]:
        print(f"    Cycle {c['cycle']}: quiet_ok={c['quiet']['accepted']}  "
              f"spike_throttled={c['spike']['rejected']}")
    print(f"  all_spikes_throttled={bursty['spike_throttled_all']}  "
          f"{'PASS' if bursty['passed'] else 'FAIL'}")

    total_elapsed = time.perf_counter() - t0
    all_passed    = burst["passed"] and sustained["passed"] and bursty["passed"]
    verdict       = "PASSED" if all_passed else "FAILED"

    print(f"\n{'='*50}")
    print(f"RATE SIMULATION VERDICT: {verdict}  ({total_elapsed:.2f}s)")
    print(f"{'='*50}\n")

    # JSON ledger
    log = {
        "run_timestamp":  datetime.now().isoformat(),
        "verdict":        verdict,
        "wall_time_s":    round(total_elapsed, 3),
        "simulations":    [burst, sustained, bursty],
    }
    with open("rate_simulation_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print("[rate_sims] Ledger -> rate_simulation_log.json")

    # Markdown report
    write_report(burst, sustained, bursty, verdict, total_elapsed)
    return all_passed


def write_report(burst, sustained, bursty, verdict, elapsed):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Rate Simulation Report",
        "",
        f"**Generated:** {ts}  ",
        f"**Verdict:** `{verdict}`  ",
        f"**Total elapsed:** {elapsed:.2f}s",
        "",
        "## Simulation 1 — Burst Flood",
        "",
        f"Fires **{burst['total_requests']:,} requests** instantly (no inter-request delay).",
        "The token bucket must actively throttle.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total requests | {burst['total_requests']:,} |",
        f"| Accepted | {burst['accepted']} |",
        f"| Rejected (throttled) | {burst['rejected']} |",
        f"| Rejection rate | {burst['rejection_rate']:.1%} |",
        f"| Avg accepted latency | {burst['avg_latency_ms']}ms |",
        f"| Wall time | {burst['wall_time_s']}s |",
        f"| **Status** | **{'PASS' if burst['passed'] else 'FAIL'}** |",
        "",
        "## Simulation 2 — Sustained Load",
        "",
        f"Sends **{sustained['target_rps']} req/s** for **{sustained['duration_s']}s**.",
        "With matching refill rate, most requests should be accepted.",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Target RPS | {sustained['target_rps']} |",
        f"| Actual RPS | {sustained['actual_rps']} |",
        f"| Accepted | {sustained['accepted']} |",
        f"| Rejected | {sustained['rejected']} |",
        f"| Rejection rate | {sustained['rejection_rate']:.1%} |",
        f"| Avg latency | {sustained['avg_latency_ms']}ms |",
        f"| **Status** | **{'PASS' if sustained['passed'] else 'FAIL'}** |",
        "",
        "## Simulation 3 — Bursty Traffic",
        "",
        f"Alternates **{bursty['cycles']} quiet -> spike cycles**.",
        "Proves limiter recovers between bursts and throttles spikes.",
        "",
        "| Cycle | Quiet Accepted | Spike Accepted | Spike Throttled |",
        "|-------|---------------|---------------|-----------------|",
    ]
    for c in bursty["cycles_data"]:
        lines.append(
            f"| {c['cycle']} | {c['quiet']['accepted']} | {c['spike']['accepted']} "
            f"| {c['spike']['rejected']} ({'YES' if c['spike_throttled'] else 'NO'}) |"
        )
    lines += [
        "",
        f"| **Status** | **{'PASS' if bursty['passed'] else 'FAIL'}** |",
        "",
        "## Token Bucket Configuration",
        "",
        "| Parameter | Burst Flood | Sustained | Bursty |",
        "|-----------|------------|-----------|--------|",
        "| Capacity  | 100 tokens | 100 tokens | 50 tokens |",
        "| Refill rate | 50 tok/s | 100 tok/s | 60 tok/s |",
        "",
        "## Conclusion",
        "",
    ]
    if verdict == "PASSED":
        lines.append(
            "All three rate simulation scenarios passed. "
            "The token bucket correctly throttles burst floods, "
            "accepts sustained traffic within bounds, "
            "and recovers between bursty spikes."
        )
    else:
        lines.append("**FAILED.** See simulation details above.")

    with open("rate_simulation_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[rate_sims] Report -> rate_simulation_report.md")


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
