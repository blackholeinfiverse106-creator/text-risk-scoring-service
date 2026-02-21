#!/usr/bin/env python3
"""
replay_harness.py — 10,000-Run Determinism Replay Harness
==========================================================
Runs analyze_text() 10,000 times per test case.
Hashes semantic-only output fields.
Writes a replay_ledger.json ledger and replay_proof_report.md.

Exit code: 0 = PROVEN, 1 = FAILED
"""

import hashlib
import json
import sys
import os
import time
from datetime import datetime
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Suppress verbose per-keyword logs during 10k-iteration harness ──────────
# The JSON logger emits one line per keyword per call.
# At 10,000 iterations this floods stdout and serializes I/O.
# We suppress the app loggers globally for this script.
import logging as _logging
_logging.getLogger("app.engine").setLevel(_logging.CRITICAL)
_logging.getLogger("app.observability").setLevel(_logging.CRITICAL)
_logging.getLogger("app.main").setLevel(_logging.CRITICAL)
_logging.getLogger().setLevel(_logging.CRITICAL)
# ────────────────────────────────────────────────────────────────────────────

from app.engine import analyze_text

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
ITERATIONS = 10_000

TEST_CASES = [
    # (label, input)
    ("clean_text",                "This is perfectly safe content."),
    ("single_violence_keyword",   "kill"),
    ("single_fraud_keyword",      "scam"),
    ("multi_category_high",       "kill murder attack scam"),
    ("max_length_safe",           "A" * 5000),
    ("over_max_length",           "A" * 6000),
    ("empty_string",              ""),
    ("whitespace_only",           "   \t\n   "),
    ("mixed_case_normalization",  "SCAM KILL ATTACK"),
    ("unicode_content",           "café résumé naïve"),
    ("repeated_same_keyword",     "kill " * 30),
    ("special_characters",        "!@#$% ^&*() kill <script>"),
    ("none_type",                 None),
    ("integer_type",              42),
    ("newlines_in_text",          "kill\nmurder\nattack"),
]

# ──────────────────────────────────────────────
# SEMANTIC HASH  (Excludes timing + correlation)
# ──────────────────────────────────────────────
SEMANTIC_FIELDS = ["risk_score", "confidence_score", "risk_category",
                   "trigger_reasons", "processed_length"]

def get_semantic_hash(response: Dict[str, Any]) -> str:
    """
    Hash only the semantically deterministic fields.
    Error responses are hashed on their error_code, not timing.
    """
    if response.get("errors"):
        core = {
            "risk_score":        response["risk_score"],
            "risk_category":     response["risk_category"],
            "error_code":        response["errors"].get("error_code"),
        }
    else:
        core = {field: response[field] for field in SEMANTIC_FIELDS}
        # Sort list fields for stable ordering
        if isinstance(core.get("trigger_reasons"), list):
            core["trigger_reasons"] = sorted(core["trigger_reasons"])

    serialized = json.dumps(core, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# ──────────────────────────────────────────────
# HARNESS
# ──────────────────────────────────────────────
def run_harness() -> tuple[bool, list]:
    all_passed = True
    ledger_entries = []

    print(f"[replay_harness] Starting {ITERATIONS:,} iterations × {len(TEST_CASES)} cases")
    print(f"[replay_harness] Run started at {datetime.now().isoformat()}\n")

    for label, test_input in TEST_CASES:
        print(f"  Testing [{label}] ...", end=" ", flush=True)

        # Establish baseline
        baseline = analyze_text(test_input)
        baseline_hash = get_semantic_hash(baseline)

        divergences = 0
        first_divergence_iter = None
        t_start = time.time()

        for i in range(ITERATIONS):
            current = analyze_text(test_input)
            current_hash = get_semantic_hash(current)
            if current_hash != baseline_hash:
                divergences += 1
                if first_divergence_iter is None:
                    first_divergence_iter = i
                # No break — count ALL divergences for full visibility

        elapsed = time.time() - t_start
        passed = divergences == 0

        if not passed:
            all_passed = False

        status = "PASS" if passed else "FAIL"
        print(f"{status}  ({ITERATIONS:,} iters, {elapsed:.2f}s, divergences={divergences})")

        ledger_entries.append({
            "label":                  label,
            "input_repr":             repr(test_input)[:80],
            "status":                 status,
            "iterations":             ITERATIONS,
            "divergences":            divergences,
            "first_divergence_iter":  first_divergence_iter,
            "baseline_hash":          baseline_hash,
            "elapsed_seconds":        round(elapsed, 4),
        })

    return all_passed, ledger_entries


# ──────────────────────────────────────────────
# LEDGER OUTPUT
# ──────────────────────────────────────────────
def write_ledger(ledger: list, verdict: str):
    path = "replay_ledger.json"
    payload = {
        "run_timestamp":     datetime.now().isoformat(),
        "iterations_per_case": ITERATIONS,
        "total_cases":       len(ledger),
        "verdict":           verdict,
        "entries":           ledger,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n[replay_harness] Ledger written → {path}")


# ──────────────────────────────────────────────
# MARKDOWN REPORT
# ──────────────────────────────────────────────
def write_report(ledger: list, verdict: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Replay Proof Report",
        "",
        f"**Generated:** {ts}",
        f"**Iterations per case:** {ITERATIONS:,}",
        f"**Verdict:** `{verdict}`",
        "",
        "## Results",
        "",
        "| Case | Status | Iterations | Divergences | Baseline Hash |",
        "|------|--------|-----------|-------------|---------------|",
    ]

    for e in ledger:
        truncated_hash = e["baseline_hash"][:16] + "..."
        lines.append(
            f"| `{e['label']}` | **{e['status']}** | "
            f"{e['iterations']:,} | {e['divergences']} | `{truncated_hash}` |"
        )

    passed  = sum(1 for e in ledger if e["status"] == "PASS")
    failed  = sum(1 for e in ledger if e["status"] == "FAIL")
    total   = sum(e["iterations"] for e in ledger)
    elapsed = sum(e["elapsed_seconds"] for e in ledger)

    lines += [
        "",
        "## Summary",
        "",
        f"- **Cases Passed:** {passed}/{len(ledger)}",
        f"- **Cases Failed:** {failed}/{len(ledger)}",
        f"- **Total Executions:** {total:,}",
        f"- **Total Elapsed:** {elapsed:.2f}s",
        "",
        "## Hash Contract",
        "",
        "The semantic hash covers exactly: `risk_score`, `confidence_score`,",
        "`risk_category`, `trigger_reasons` (sorted), `processed_length`.",
        "Excluded: `correlation_id`, log timestamps, `errors.message` (free-text).",
        "",
        "## Conclusion",
        "",
    ]

    if verdict == "PROVEN":
        lines.append(
            f"Zero divergence detected across **{total:,} total executions**. "
            "The engine is deterministic under all tested input conditions."
        )
    else:
        lines.append(
            f"**DIVERGENCE DETECTED.** {failed} case(s) showed non-deterministic output. "
            "Review `replay_ledger.json` for details."
        )

    path = "replay_proof_report.md"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"[replay_harness] Report written  → {path}")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    passed, ledger = run_harness()
    verdict = "PROVEN" if passed else "FAILED"

    print(f"\n{'='*50}")
    print(f"FINAL VERDICT: {verdict}")
    print(f"{'='*50}\n")

    write_ledger(ledger, verdict)
    write_report(ledger, verdict)

    sys.exit(0 if passed else 1)
