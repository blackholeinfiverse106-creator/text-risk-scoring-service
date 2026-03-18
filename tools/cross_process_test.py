#!/usr/bin/env python3
"""
cross_process_test.py — Cross-Process Determinism Proof
=========================================================
Spawns N independent OS-level worker processes via multiprocessing.
Each process calls analyze_text() independently.
All outputs are compared by semantic hash.

Proves: identical input → identical output, regardless of process boundary.
Exit code: 0 = CROSS-PROCESS PROVEN, 1 = FAILED
"""

import hashlib
import json
import sys
import os
import time
from multiprocessing import Pool, cpu_count
from datetime import datetime
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
NUM_PROCESSES = max(4, cpu_count())   # At least 4 workers
RUNS_PER_PROCESS = 50                  # Each worker runs this many times

TEST_CASES = [
    ("clean",        "This content is perfectly safe."),
    ("high_risk",    "kill murder attack scam fraud"),
    ("empty",        ""),
    ("max_length",   "A" * 5000),
    ("over_length",  "A" * 6000),
    ("case_mixed",   "SCAM Kill Attack"),
    ("none_input",   None),
    ("int_input",    42),
    ("unicode",      "café résumé naïve scam"),
    ("repeat_kw",    "kill " * 20),
]

SEMANTIC_FIELDS = ["risk_score", "confidence_score", "risk_category",
                   "trigger_reasons", "processed_length"]

# ──────────────────────────────────────────────
# SEMANTIC HASH  (must be importable in worker)
# ──────────────────────────────────────────────
def get_semantic_hash(response: Dict[str, Any]) -> str:
    if response.get("errors"):
        core = {
            "risk_score":    response["risk_score"],
            "risk_category": response["risk_category"],
            "error_code":    response["errors"].get("error_code"),
        }
    else:
        core = {field: response[field] for field in SEMANTIC_FIELDS}
        core["trigger_reasons"] = sorted(core["trigger_reasons"])
    serialized = json.dumps(core, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ──────────────────────────────────────────────
# WORKER FUNCTION (runs in subprocess)
# ──────────────────────────────────────────────
def worker_task(args: Tuple) -> Dict:
    """
    Executed in a separate OS process.
    Returns a dict with pid, label, runs, and list of hashes.
    """
    label, test_input, runs = args

    # Must re-import inside worker (each process has its own Python interpreter)
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.engine import analyze_text

    hashes = []
    for _ in range(runs):
        result = analyze_text(test_input)
        hashes.append(get_semantic_hash(result))

    return {
        "pid":        os.getpid(),
        "label":      label,
        "input_repr": repr(test_input)[:80],
        "runs":       runs,
        "hashes":     hashes,
    }


# ──────────────────────────────────────────────
# CROSS-PROCESS COMPARISON
# ──────────────────────────────────────────────
def verify_cross_process(all_results: List[Dict]) -> Tuple[bool, List[Dict]]:
    """
    Groups results by (label). For each label:
    - All hashes from all processes must be identical.
    """
    from collections import defaultdict
    by_label = defaultdict(list)
    for r in all_results:
        by_label[r["label"]].extend(r["hashes"])

    summary = []
    all_passed = True

    for label, hashes in sorted(by_label.items()):
        unique = set(hashes)
        passed = len(unique) == 1
        if not passed:
            all_passed = False

        summary.append({
            "label":          label,
            "total_runs":     len(hashes),
            "unique_hashes":  len(unique),
            "baseline_hash":  next(iter(unique)),
            "status":         "PASS" if passed else "FAIL",
        })

    return all_passed, summary


# ──────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────
def write_report(summary: List[Dict], verdict: str, num_processes: int,
                 elapsed: float):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_runs = sum(s["total_runs"] for s in summary)

    lines = [
        "# Cross-Process Determinism Report",
        "",
        f"**Generated:** {ts}",
        f"**Processes spawned:** {num_processes}",
        f"**Runs per process:** {RUNS_PER_PROCESS}",
        f"**Total executions:** {total_runs:,}",
        f"**Elapsed:** {elapsed:.2f}s",
        f"**Verdict:** `{verdict}`",
        "",
        "## Results",
        "",
        "| Case | Total Runs | Unique Hashes | Status |",
        "|------|-----------|---------------|--------|",
    ]
    for s in summary:
        lines.append(
            f"| `{s['label']}` | {s['total_runs']:,} | "
            f"{s['unique_hashes']} | **{s['status']}** |"
        )

    lines += [
        "",
        "## Conclusion",
        "",
    ]
    if verdict == "CROSS-PROCESS PROVEN":
        lines.append(
            f"All {total_runs:,} executions across {num_processes} independent OS processes "
            "produced identical semantic hashes. The engine is process-boundary-safe."
        )
    else:
        lines.append("**FAILURE:** Hash divergence detected across processes.")

    path = "cross_process_report.md"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"[cross_process] Report written → {path}")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[cross_process] Spawning {NUM_PROCESSES} worker processes")
    print(f"[cross_process] Runs per process: {RUNS_PER_PROCESS}")
    print(f"[cross_process] Test cases: {len(TEST_CASES)}\n")

    # Build task list: each (label, input) goes to every process
    tasks = []
    for label, test_input in TEST_CASES:
        for _ in range(NUM_PROCESSES):
            tasks.append((label, test_input, RUNS_PER_PROCESS))

    t_start = time.time()
    with Pool(processes=NUM_PROCESSES) as pool:
        all_results = pool.map(worker_task, tasks)
    elapsed = time.time() - t_start

    all_passed, summary = verify_cross_process(all_results)
    verdict = "CROSS-PROCESS PROVEN" if all_passed else "CROSS-PROCESS FAILED"

    # Print summary
    print(f"\n{'─'*60}")
    for s in summary:
        icon = "✓" if s["status"] == "PASS" else "✗"
        print(f"  {icon} [{s['label']}]  "
              f"{s['total_runs']} runs | {s['unique_hashes']} unique hash(es)")
    print(f"{'─'*60}")
    print(f"\nFINAL VERDICT: {verdict}  ({elapsed:.2f}s)\n")

    write_report(summary, verdict, NUM_PROCESSES, elapsed)

    sys.exit(0 if all_passed else 1)
