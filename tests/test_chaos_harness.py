"""
pytest wrapper for chaos_harness.py
All four parts exposed as discrete pytest tests.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chaos_harness import (
    run_part_a, run_part_b, run_part_c, run_part_d,
    emit_part_a_report, emit_part_b_report,
    emit_part_c_report, emit_part_d_report,
    MALFORMED_CASES, ENTROPY_CASES,
)


def test_part_a_malformed_signal_survival():
    """Part A: All malformed inputs are rejected or produce safe error responses."""
    data = run_part_a()
    emit_part_a_report(data)
    assert data["passed"] == data["total"], (
        f"Part A: {data['total'] - data['passed']} cases FAILED out of {data['total']}.\n"
        + "\n".join(
            f"  FAIL [{c['label']}]: {c['note']}"
            for c in data["cases"] if c["status"] == "FAIL"
        )
    )


def test_part_b_entropy_corruption():
    """Part B: All entropy boundary/corruption values handled correctly."""
    data = run_part_b()
    emit_part_b_report(data)
    assert data["passed"] == data["total"], (
        f"Part B: {data['total'] - data['passed']} entropy cases FAILED.\n"
        + "\n".join(
            f"  FAIL [{c['label']}] entropy={c['entropy_value']}: {c['note']}"
            for c in data["cases"] if c["status"] == "FAIL"
        )
    )


def test_part_c_concurrent_chaos_500_threads():
    """Part C: 500 concurrent threads — zero invariant violations, zero exceptions."""
    data = run_part_c()
    emit_part_c_report(data)
    assert data["invariant_violations"] == 0, (
        f"Part C: {data['invariant_violations']} invariant violations under 500 threads.\n"
        + "\n".join(data["violation_details"])
    )
    assert data["exceptions"] == 0, (
        f"Part C: {data['exceptions']} unhandled exceptions under concurrent chaos."
    )
    assert data["completed"] == data["threads"], (
        f"Part C: only {data['completed']}/{data['threads']} threads completed."
    )


def test_part_d_ledger_tamper_detection():
    """Part D: SHA-256 ledger detects 100% of tamper attempts."""
    data = run_part_d()
    emit_part_d_report(data)
    assert data["undetected"] == 0, (
        f"Part D: {data['undetected']} tamper attempts went UNDETECTED "
        f"(detection rate: {data['detected']}/{data['total_tampers']})."
    )
    assert data["detected"] == data["total_tampers"], (
        f"Part D: tamper detection incomplete ({data['detected']}/{data['total_tampers']})."
    )
