from __future__ import annotations
"""
Sovereign Layer File: app/layer4_enforcement.py

Pure Enforcement Gate — Sovereign-Compliant
============================================

This module is the FINAL enforcement gate in the BHIV pipeline.
It does NOT think. It does NOT decide beyond enforcement.
It does NOT own execution. It does NOT write to Bucket.

Authority Boundary (IMMUTABLE):
  - Accepts ONLY: Sarathi-approved decision + DGIC snapshot
  - Returns ONLY: ALLOW / DENY / ABSTAIN + reasoning
  - HARD FAILS if Sarathi decision is missing
  - HARD FAILS if DGIC snapshot is missing
  - NEVER writes to Bucket (Siddhesh's domain)
  - NEVER maps execution outcomes (no 'executed' flag)
  - NEVER calls Sarathi (Aakanksha's domain)
  - NEVER computes risk (Sarathi + DGIC's domain)

Integration:
  Aakanksha Parab — Sarathi — provides FINAL decision
  Pritesh Patra — DGIC — provides epistemic reasoning (no execution)
  Raj Prajapati — Core — executes approved actions ONLY (not here)
  Siddhesh Narkar — Bucket — immutable storage via API (not here)
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================
# Enforcement Errors — Hard Failures
# ============================================================

class EnforcementHardFailure(Exception):
    """
    Raised when the enforcement gate cannot proceed due to
    missing or invalid sovereign inputs (Sarathi decision or DGIC snapshot).
    This is a HARD FAIL — no fallback, no default, no interpretation.
    """
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"ENFORCEMENT HARD FAIL [{code}]: {message}")


# ============================================================
# Valid enforcement verdicts
# ============================================================

_VALID_VERDICTS = {"ALLOW", "DENY", "ABSTAIN"}


# ============================================================
# enforce() — The Pure Enforcement Gate
# ============================================================

def enforce(
    original_execution_id: str,
    sarathi_decision: Optional[str],
    sarathi_execution_id: Optional[str],
    sarathi_confidence: Optional[float],
    dgic_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    The pure enforcement gate.

    Accepts ONLY:
      - Sarathi-approved decision (ALLOW / DENY / ABSTAIN)
      - Sarathi execution_id (for propagation)
      - Sarathi confidence (for metadata trace)
      - DGIC snapshot dict (epistemic context — read-only, not interpreted)

    Returns ONLY:
      {
        "execution_id": "...",
        "enforcement_decision": "ALLOW | DENY | ABSTAIN",
        "confidence": 0.0
      }

    HARD FAILS if:
      - Sarathi decision is missing or None
      - Sarathi decision is not a valid verdict
      - Sarathi execution_id is missing
      - Original execution_id does not exactly match Sarathi execution_id
      - DGIC snapshot is missing or None

    This function NEVER:
      - Writes to Bucket
      - Maps execution outcomes
      - Calls Sarathi
      - Computes risk
      - Interprets or modifies the Sarathi decision
    """

    # ── HARD FAIL: Sarathi decision missing ──
    if sarathi_decision is None:
        logger.error(
            "ENFORCEMENT HARD FAIL: Sarathi decision is None",
            extra={"event_type": "enforcement_hard_fail", "code": "SARATHI_DECISION_MISSING"},
        )
        raise EnforcementHardFailure(
            "SARATHI_DECISION_MISSING",
            "Sarathi decision is required. Enforcement cannot proceed without governance approval.",
        )

    # ── HARD FAIL: Sarathi decision not valid ──
    if sarathi_decision not in _VALID_VERDICTS:
        logger.error(
            f"ENFORCEMENT HARD FAIL: Invalid Sarathi decision '{sarathi_decision}'",
            extra={"event_type": "enforcement_hard_fail", "code": "SARATHI_DECISION_INVALID"},
        )
        raise EnforcementHardFailure(
            "SARATHI_DECISION_INVALID",
            f"Sarathi decision must be one of {_VALID_VERDICTS}, got '{sarathi_decision}'.",
        )

    # ── HARD FAIL: Sarathi execution_id missing ──
    if not sarathi_execution_id:
        logger.error(
            "ENFORCEMENT HARD FAIL: Sarathi execution_id is missing",
            extra={"event_type": "enforcement_hard_fail", "code": "EXECUTION_ID_MISSING"},
        )
        raise EnforcementHardFailure(
            "EXECUTION_ID_MISSING",
            "Sarathi execution_id is required for enforcement traceability.",
        )

    # ── HARD FAIL: execution_id mismatch ──
    if original_execution_id != sarathi_execution_id:
        logger.error(
            f"ENFORCEMENT HARD FAIL: Execution ID mismatch. "
            f"Expected {original_execution_id}, got {sarathi_execution_id}.",
            extra={"event_type": "enforcement_hard_fail", "code": "EXECUTION_ID_MISMATCH"},
        )
        raise EnforcementHardFailure(
            "EXECUTION_ID_MISMATCH",
            f"Sarathi execution_id ({sarathi_execution_id}) does not match original request ({original_execution_id}). Potential identifier leakage.",
        )

    # ── HARD FAIL: DGIC snapshot missing ──
    if dgic_snapshot is None:
        logger.error(
            "ENFORCEMENT HARD FAIL: DGIC snapshot is None",
            extra={"event_type": "enforcement_hard_fail", "code": "DGIC_SNAPSHOT_MISSING"},
        )
        raise EnforcementHardFailure(
            "DGIC_SNAPSHOT_MISSING",
            "DGIC epistemic snapshot is required. Enforcement cannot proceed without epistemic context.",
        )

    # ── Pure pass-through: NO interpretation ──
    verdict = sarathi_decision

    logger.info(
        f"Enforcement verdict: {verdict}",
        extra={
            "event_type": "enforcement_verdict",
            "execution_id": sarathi_execution_id,
            "verdict": verdict,
        },
    )

    return {
        "execution_id": sarathi_execution_id,
        "enforcement_decision": verdict,
        "confidence": float(sarathi_confidence or 0.0),
    }
