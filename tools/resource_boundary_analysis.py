#!/usr/bin/env python3
"""
resource_boundary_analysis.py — CPU + Memory Boundary Analysis
==============================================================
Measures real CPU time and heap memory for best/nominal/worst-case inputs.
Derives empirical bounds and a capacity planning formula.
Writes resource-boundary-model.md.

Exit code: 0 = BOUNDED (all within thresholds), 1 = EXCEEDED
"""

import sys
import os
import time
import json
import tracemalloc
import statistics
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging as _logging
_logging.getLogger("app.engine").setLevel(_logging.CRITICAL)
_logging.getLogger().setLevel(_logging.CRITICAL)

from app.engine import analyze_text, MAX_TEXT_LENGTH, RISK_KEYWORDS

# ──────────────────────────────────────────────
# THRESHOLDS
# ──────────────────────────────────────────────
CPU_THRESHOLD_MS  = 500    # max allowed wall time per call
MEM_THRESHOLD_KB  = 1024   # max allowed heap delta per call (1 MB)

REPS = 20   # repetitions per profile point

# ──────────────────────────────────────────────
# TEST CASES
# ──────────────────────────────────────────────
all_keywords = [kw for kws in RISK_KEYWORDS.values() for kw in kws]
all_kw_str   = " ".join(all_keywords)
worst_case_text = (all_kw_str * (MAX_TEXT_LENGTH // len(all_kw_str) + 1))[:MAX_TEXT_LENGTH]

PROFILES = [
    ("best_case_empty",        "",                          "Empty input — baseline floor"),
    ("best_case_no_keywords",  "Hello, how are you today?","Short, zero keywords"),
    ("nominal_1_keyword",      "scam",                     "Single keyword match"),
    ("nominal_5_keywords",     "kill scam fraud attack bomb","5 keywords across 2 categories"),
    ("nominal_10_keywords",    "kill murder attack bomb assault scam fraud hack phish fake",
                               "10 keywords, 2 categories"),
    ("medium_length_no_hit",   "x" * 2500,                 "2500 chars, no keyword"),
    ("max_length_no_hit",      "x" * MAX_TEXT_LENGTH,      "5000 chars, no keyword"),
    ("max_length_all_keywords", worst_case_text,            "5000 chars, all keywords — worst case"),
    ("over_limit",             "A" * 6000,                  "Over max length — truncation path"),
    ("invalid_type",           None,                        "None type — early return path"),
]


# ──────────────────────────────────────────────
# PROFILER
# ──────────────────────────────────────────────
def profile_case(label, text, desc):
    wall_times  = []
    cpu_times   = []
    mem_deltas  = []  # KB

    for _ in range(REPS):
        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()

        t_wall0 = time.perf_counter()
        t_cpu0  = time.process_time()

        analyze_text(text)

        t_wall1 = time.perf_counter()
        t_cpu1  = time.process_time()

        snap2   = tracemalloc.take_snapshot()
        tracemalloc.stop()

        wall_ms = (t_wall1 - t_wall0) * 1000
        cpu_ms  = (t_cpu1  - t_cpu0)  * 1000
        mem_kb  = sum(s.size_diff for s in snap2.compare_to(snap1, "lineno")) / 1024

        wall_times.append(wall_ms)
        cpu_times.append(cpu_ms)
        mem_deltas.append(mem_kb)

    return {
        "label":        label,
        "description":  desc,
        "reps":         REPS,
        "wall_ms": {
            "mean":   round(statistics.mean(wall_times), 3),
            "median": round(statistics.median(wall_times), 3),
            "max":    round(max(wall_times), 3),
        },
        "cpu_ms": {
            "mean":   round(statistics.mean(cpu_times), 3),
            "median": round(statistics.median(cpu_times), 3),
            "max":    round(max(cpu_times), 3),
        },
        "mem_kb": {
            "mean":   round(statistics.mean(mem_deltas), 3),
            "median": round(statistics.median(mem_deltas), 3),
            "max":    round(max(mem_deltas), 3),
        },
        "within_cpu_threshold": max(wall_times) < CPU_THRESHOLD_MS,
        "within_mem_threshold": max(mem_deltas) < MEM_THRESHOLD_KB,
    }


# ──────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────
def write_report(profiles, verdict):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Find worst-case row for capacity formula
    worst = max(profiles, key=lambda p: p["wall_ms"]["max"])
    p99_ms    = worst["wall_ms"]["max"]
    max_rps   = round(1000 / p99_ms, 1) if p99_ms > 0 else float("inf")

    lines = [
        "# Resource Boundary Model",
        "",
        f"**Generated:** {ts}  ",
        f"**Reps per profile:** {REPS}  ",
        f"**CPU threshold:** {CPU_THRESHOLD_MS}ms  ",
        f"**Memory threshold:** {MEM_THRESHOLD_KB}KB  ",
        f"**Verdict:** `{verdict}`",
        "",
        "## Big-O Analysis",
        "",
        "| Dimension | Complexity | Ceiling |",
        "|-----------|-----------|---------|",
        "| Time      | O(N * K)  | N=5000 chars, K~100 keywords => O(1) bounded |",
        "| Space     | O(N)      | N=5000 => at most 5KB string allocation |",
        "",
        "> Both N and K are hard-capped constants.",
        "> The engine is effectively O(1) with a fixed constant factor.",
        "",
        "## Empirical Measurements",
        "",
        "| Profile | Wall Median | Wall Max | CPU Max | Mem Max (KB) | CPU OK | Mem OK |",
        "|---------|------------|---------|---------|-------------|--------|--------|",
    ]
    for p in profiles:
        cpu_ok = "PASS" if p["within_cpu_threshold"] else "FAIL"
        mem_ok = "PASS" if p["within_mem_threshold"] else "FAIL"
        lines.append(
            f"| `{p['label']}` | {p['wall_ms']['median']}ms | {p['wall_ms']['max']}ms | "
            f"{p['cpu_ms']['max']}ms | {p['mem_kb']['max']:.1f} | **{cpu_ok}** | **{mem_ok}** |"
        )

    lines += [
        "",
        "## Capacity Planning",
        "",
        "```",
        f"Worst-case wall time (max across all profiles): {p99_ms:.2f}ms",
        f"Single-core max throughput (1000 / worst_ms):  {max_rps} req/s",
        "",
        "Multi-core formula:",
        "  max_rps_total = cores * (1000 / p99_single_thread_ms)",
        f"  Example at 4 cores: {round(4 * max_rps, 0):.0f} req/s",
        f"  Example at 8 cores: {round(8 * max_rps, 0):.0f} req/s",
        "```",
        "",
        "## Resource Guard Settings (from resource-guard.md)",
        "",
        "| Resource | Limit | Enforcement |",
        "|----------|-------|-------------|",
        "| Payload size | 5000 chars | Hard truncation in `engine.py` |",
        "| Memory per request | <1 MB delta | Empirically verified above |",
        "| Response latency P99 | <500ms | Verified by `concurrency_stress.py` |",
        "",
        "## Conclusion",
        "",
    ]
    if verdict == "BOUNDED":
        lines.append(
            f"All {len(profiles)} profile points stayed within CPU and memory thresholds. "
            f"Worst-case call: **{p99_ms:.2f}ms** wall time. "
            f"Single-core capacity: **{max_rps} req/s**."
        )
    else:
        lines.append("**EXCEEDED.** One or more profiles breached thresholds. See table above.")

    with open("resource-boundary-model.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[resource_boundary] Report -> resource-boundary-model.md")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[resource_boundary] Profiling {len(PROFILES)} cases x {REPS} reps\n")

    results = []
    for label, text, desc in PROFILES:
        p = profile_case(label, text, desc)
        ok_str = "OK" if (p["within_cpu_threshold"] and p["within_mem_threshold"]) else "WARN"
        print(f"  [{ok_str}] {label:35s}  "
              f"wall_max={p['wall_ms']['max']:7.2f}ms  "
              f"mem_max={p['mem_kb']['max']:7.1f}KB")
        results.append(p)

    all_bounded = all(
        p["within_cpu_threshold"] and p["within_mem_threshold"] for p in results
    )
    verdict = "BOUNDED" if all_bounded else "EXCEEDED"

    print(f"\n{'='*50}")
    print(f"RESOURCE BOUNDARY VERDICT: {verdict}")
    print(f"{'='*50}\n")

    with open("resource_boundary_report.json", "w", encoding="utf-8") as f:
        json.dump({"verdict": verdict, "profiles": results,
                   "run_timestamp": datetime.now().isoformat()}, f, indent=2)
    print("[resource_boundary] Ledger -> resource_boundary_report.json")

    write_report(results, verdict)
    sys.exit(0 if all_bounded else 1)
