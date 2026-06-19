"""
RAJYA — Final Authority Validation Engine
==========================================

Extracts and consolidates all pre-execution authority validation
that was previously embedded inside Core (layer4_core.py).

RAJYA validates everything BEFORE Core executes.
No intelligence. No governance. No orchestration. Pure validation gate.

Authority Boundary (IMMUTABLE):
  - Validates ONLY: enforcement verdict structure and authority decisions
  - Returns ONLY: EXECUTION_APPROVED or REJECT with reason
  - NEVER executes actions (Core's domain)
  - NEVER computes risk (Intelligence + Sarathi's domain)

  - NEVER writes to Bucket (Siddhesh's domain)
  - NEVER interprets epistemic state (DGIC's domain)

Integration:
  Aakanksha Parab — Sarathi — provides final decision authority
  Pritesh Patra — DGIC — provides deterministic reasoning output
  Raj Prajapati — Core — executes actions (depends on RAJYA approval)

Validation Rules (STRICT — no additions allowed):
  1. Missing authority (sarathi or enforcement is None) → REJECT
  2. execution_id mismatch → REJECT
  3. Sarathi decision != ALLOW → REJECT
  4. Enforcement decision != ALLOW → REJECT
  Else → EXECUTION_APPROVED
"""

from __future__ import annotations

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================
# Validation Result
# ============================================================

class RajyaValidationResult(str, Enum):
    """The only two outcomes RAJYA can produce."""
    EXECUTION_APPROVED = "EXECUTION_APPROVED"
    REJECT = "REJECT"


# ============================================================
# Rejection Detail
# ============================================================

@dataclass(frozen=True)
class RajyaRejection:
    """Structured rejection reason from RAJYA validation."""
    code: str
    reason: str


# ============================================================
# validate_execution_request — The Pure Validation Gate
# ============================================================

def validate_execution_request(
    payload: Dict[str, Any],
) -> tuple[RajyaValidationResult, Optional[RajyaRejection]]:
    """
    Final authority validation before Core execution.

    Payload shape:
        {
            "execution_id": str,                # Pipeline canonical ID
            "sarathi_decision": str | None,     # From SarathiEvaluateResponse
            "sarathi_execution_id": str | None, # From SarathiEvaluateResponse
            "enforcement_verdict": dict | None, # From enforce() return value
        }

    Returns:
        (EXECUTION_APPROVED, None) — Core may proceed
        (REJECT, RajyaRejection) — Core must NOT proceed

    Rules (STRICT):
        1. Missing authority → REJECT
        2. execution_id mismatch → REJECT
        3. Sarathi != ALLOW → REJECT
        4. Enforcement != ALLOW → REJECT
        Else → EXECUTION_APPROVED
    """

    execution_id = payload.get("execution_id", "UNKNOWN")

    # ── RULE 1: Missing authority — sarathi decision ──
    sarathi_decision = payload.get("sarathi_decision")
    if sarathi_decision is None:
        rejection = RajyaRejection(
            code="RAJYA_SARATHI_AUTHORITY_MISSING",
            reason="Sarathi decision is missing. Cannot approve execution without governance authority.",
        )
        logger.error(
            f"RAJYA REJECT: {rejection.code} | execution_id={execution_id}",
            extra={"event_type": "rajya_reject", "code": rejection.code, "execution_id": execution_id},
        )
        return RajyaValidationResult.REJECT, rejection

    # ── RULE 1 (cont.): Missing authority — enforcement verdict ──
    enforcement_verdict = payload.get("enforcement_verdict")
    if enforcement_verdict is None or not isinstance(enforcement_verdict, dict):
        rejection = RajyaRejection(
            code="RAJYA_ENFORCEMENT_AUTHORITY_MISSING",
            reason="Enforcement verdict is missing or invalid. Cannot approve execution without enforcement authority.",
        )
        logger.error(
            f"RAJYA REJECT: {rejection.code} | execution_id={execution_id}",
            extra={"event_type": "rajya_reject", "code": rejection.code, "execution_id": execution_id},
        )
        return RajyaValidationResult.REJECT, rejection

    # ── RULE 2: execution_id mismatch ──
    sarathi_execution_id = payload.get("sarathi_execution_id")
    if sarathi_execution_id is None or sarathi_execution_id != execution_id:
        rejection = RajyaRejection(
            code="RAJYA_EXECUTION_ID_MISMATCH",
            reason=f"Execution ID mismatch: pipeline='{execution_id}', sarathi='{sarathi_execution_id}'. Identity integrity violated.",
        )
        logger.error(
            f"RAJYA REJECT: {rejection.code} | execution_id={execution_id}",
            extra={"event_type": "rajya_reject", "code": rejection.code, "execution_id": execution_id},
        )
        return RajyaValidationResult.REJECT, rejection

    # ── RULE 3: Sarathi != ALLOW → REJECT ──
    if sarathi_decision != "ALLOW":
        rejection = RajyaRejection(
            code="RAJYA_SARATHI_NOT_ALLOW",
            reason=f"Sarathi decision is '{sarathi_decision}', not ALLOW. Execution not authorized.",
        )
        logger.info(
            f"RAJYA REJECT: {rejection.code} | execution_id={execution_id}",
            extra={"event_type": "rajya_reject", "code": rejection.code, "execution_id": execution_id},
        )
        return RajyaValidationResult.REJECT, rejection

    # ── RULE 4: Enforcement != ALLOW → REJECT ──
    enforcement_decision = enforcement_verdict.get("enforcement_decision")
    if enforcement_decision != "ALLOW":
        rejection = RajyaRejection(
            code="RAJYA_ENFORCEMENT_NOT_ALLOW",
            reason=f"Enforcement decision is '{enforcement_decision}', not ALLOW. Execution not authorized.",
        )
        logger.info(
            f"RAJYA REJECT: {rejection.code} | execution_id={execution_id}",
            extra={"event_type": "rajya_reject", "code": rejection.code, "execution_id": execution_id},
        )
        return RajyaValidationResult.REJECT, rejection

    # ── ALL RULES PASSED → EXECUTION_APPROVED ──
    logger.info(
        f"RAJYA APPROVED | execution_id={execution_id}",
        extra={"event_type": "rajya_approved", "execution_id": execution_id},
    )
    return RajyaValidationResult.EXECUTION_APPROVED, None
