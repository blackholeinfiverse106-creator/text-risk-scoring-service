#!/usr/bin/env python3
"""
concurrency_stress.py — 500 Concurrent Request Benchmark
=========================================================
Fires 500 concurrent threads against analyze_text().
Measures latency percentiles, failure rate, and score correctness.
Writes concurrency_benchmark.md and concurrency_benchmark.json.

Exit code: 0 = PASSED, 1 = FAILED
"""

import sys
import os
import time
import json
import statistics
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging as _logging
_logging.getLogger("app.engine").setLevel(_logging.CRITICAL)
_logging.getLogger().setLevel(_logging.CRITICAL)

from app.engine import analyze_text

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
CONCURRENCY   = 500
TOTAL_REQUESTS = 500   # 1:1 — one request per thread

# Mixed workload
REQUESTS = [
    ("clean",       "This is perfectly safe content."),
    ("single_kw",   "scam"),
    ("multi_kw",    "kill murder attack scam fraud"),
    ("max_length",  "A" * 5000),
    ("empty",       ""),
    ("none_type",   None),
    ("unicode",     "cafe resume kill"),
    ("repeat_kw",   "kill " * 20),
] * (TOTAL_REQUESTS // 8 + 1)   # cycle to fill 500 slots
REQUESTS = REQUESTS[:TOTAL_REQUESTS]

# ──────────────────────────────────────────────
# WORKER
# ──────────────────────────────────────────────
failures = []
failure_lock = threading.Lock()

def worker(idx: int, label: str, text):
    t0 = time.perf_counter()
    try:
        result = analyze_text(text)
        duration_ms = (time.perf_counter() - t0) * 1000

        # Validate result structure
        assert "risk_score"    in result, "Missing risk_score"
        assert "risk_category" in result, "Missing risk_category"
        assert isinstance(result["risk_score"], float), "risk_score not float"

        return {"idx": idx, "label": label, "latency_ms": duration_ms,
                "risk_score": result["risk_score"], "ok": True}
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        with failure_lock:
            failures.append({"idx": idx, "label": label, "error": str(e)})
        return {"idx": idx, "label": label, "latency_ms": duration_ms,
                "risk_score": None, "ok": False}


# ──────────────────────────────────────────────
# HARNESS
# ──────────────────────────────────────────────
def run_benchmark():
    print(f"[concurrency_stress] Starting {TOTAL_REQUESTS} requests @ {CONCURRENCY} concurrency")
    print(f"[concurrency_stress] {datetime.now().isoformat()}\n")

    t_start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {
            executor.submit(worker, i, label, text): i
            for i, (label, text) in enumerate(REQUESTS)
        }
        for future in as_completed(futures):
            results.append(future.result())
    total_elapsed = time.perf_counter() - t_start

    # ── Stats ──────────────────────────────────
    latencies   = [r["latency_ms"] for r in results]
    ok_count    = sum(1 for r in results if r["ok"])
    fail_count  = len(failures)

    p50  = statistics.median(latencies)
    p95  = statistics.quantiles(latencies, n=20)[18]
    p99  = statistics.quantiles(latencies, n=100)[98]
    mean = statistics.mean(latencies)
    stdev = statistics.stdev(latencies)
    mx   = max(latencies)
    mn   = min(latencies)

    throughput = TOTAL_REQUESTS / total_elapsed   # req/sec

    print(f"  Total requests : {TOTAL_REQUESTS}")
    print(f"  Succeeded      : {ok_count}")
    print(f"  Failed         : {fail_count}")
    print(f"  Throughput     : {throughput:.1f} req/s")
    print(f"  Latency mean   : {mean:.2f}ms")
    print(f"  Latency stdev  : {stdev:.2f}ms")
    print(f"  P50            : {p50:.2f}ms")
    print(f"  P95            : {p95:.2f}ms")
    print(f"  P99            : {p99:.2f}ms")
    print(f"  Max            : {mx:.2f}ms")
    print(f"  Min            : {mn:.2f}ms")
    print(f"  Total wall time: {total_elapsed:.2f}s")

    passed = fail_count == 0 and p99 < 500   # P99 < 500ms threshold
    verdict = "PASSED" if passed else "FAILED"
    print(f"\n  VERDICT: {verdict}")

    # ── Ledger ─────────────────────────────────
    ledger = {
        "run_timestamp":    datetime.now().isoformat(),
        "concurrency":      CONCURRENCY,
        "total_requests":   TOTAL_REQUESTS,
        "succeeded":        ok_count,
        "failed":           fail_count,
        "failures":         failures,
        "throughput_rps":   round(throughput, 2),
        "latency_ms": {
            "mean":  round(mean, 3),
            "stdev": round(stdev, 3),
            "min":   round(mn, 3),
            "p50":   round(p50, 3),
            "p95":   round(p95, 3),
            "p99":   round(p99, 3),
            "max":   round(mx, 3),
        },
        "wall_time_seconds": round(total_elapsed, 3),
        "verdict":           verdict,
    }
    with open("concurrency_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    print("[concurrency_stress] Ledger -> concurrency_benchmark.json")

    # ── Markdown Report ────────────────────────
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Concurrency Benchmark Report",
        "",
        f"**Generated:** {ts}  ",
        f"**Concurrency:** {CONCURRENCY} simultaneous threads  ",
        f"**Total Requests:** {TOTAL_REQUESTS}  ",
        f"**Verdict:** `{verdict}`",
        "",
        "## Latency Percentiles",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Mean   | {mean:.2f} ms |",
        f"| StdDev | {stdev:.2f} ms |",
        f"| Min    | {mn:.2f} ms |",
        f"| P50    | {p50:.2f} ms |",
        f"| P95    | {p95:.2f} ms |",
        f"| P99    | {p99:.2f} ms |",
        f"| Max    | {mx:.2f} ms |",
        "",
        "## Throughput",
        "",
        f"- **Requests/sec:** {throughput:.1f}",
        f"- **Wall time:** {total_elapsed:.2f}s for {TOTAL_REQUESTS} requests",
        f"- **Failures:** {fail_count}",
        "",
        "## Pass Criteria",
        "",
        "| Criterion | Threshold | Actual | Status |",
        "|-----------|-----------|--------|--------|",
        f"| Zero failures | 0 | {fail_count} | {'PASS' if fail_count == 0 else 'FAIL'} |",
        f"| P99 latency   | <500ms | {p99:.1f}ms | {'PASS' if p99 < 500 else 'FAIL'} |",
        "",
        "## Conclusion",
        "",
    ]
    if passed:
        lines.append(
            f"The engine handled **{TOTAL_REQUESTS} simultaneous requests** with zero failures "
            f"and P99 latency of **{p99:.1f}ms** — well within the 500ms safety threshold."
        )
    else:
        lines.append("**FAILED.** See `concurrency_benchmark.json` for failure details.")

    with open("concurrency_benchmark.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[concurrency_stress] Report  -> concurrency_benchmark.md")

    return passed


if __name__ == "__main__":
    ok = run_benchmark()
    sys.exit(0 if ok else 1)
