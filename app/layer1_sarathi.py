"""
Sarathi — Pure Enforcement Token + Gate Layer
==============================================

Sarathi does NOT decide.
Sarathi does NOT validate.
Sarathi does NOT compute ALLOW / DENY / ESCALATE.
Sarathi ONLY enforces using RAJYA approval.

Role:
  - Receives RAJYA's EXECUTION_APPROVED verdict
  - Mints a deterministic SarathiEnforcementToken
  - Token is the sole gate for Core execution

Authority Boundary (IMMUTABLE):
  - Sarathi NEVER computes risk scores
  - Sarathi NEVER performs text analysis
  - Sarathi NEVER applies DGIC modifiers
  - Sarathi NEVER produces governance decisions
  - Sarathi ONLY mints enforcement tokens after RAJYA approval

Integration:
  Pritesh Patra — DGIC — provides reasoning output
  RAJYA (previous build) — validates and approves execution
  Raj Prajapati — Core — executes only when enforcement token is valid

Token Rules:
  - Only generated if RAJYA = EXECUTION_APPROVED
  - Deterministic format
  - No randomness
"""

from __future__ import annotations

import logging
import hashlib
import json
from typing import Optional
from dataclasses import dataclass

from app.enforcement_schemas import (
    EvaluateActionRequest,
)

logger = logging.getLogger(__name__)


# ============================================================
# Trace Hash — Deterministic Identity (NOT decision logic)
# ============================================================

def compute_trace_hash(request: EvaluateActionRequest) -> str:
    """
    Compute a deterministic SHA-256 hash of the request payload.
    This is a pure identity function — no decision logic.
    """
    context_signals_canonical = [
        {
            "signal_id": s.signal_id,
            "signal_type": s.signal_type,
            "value": s.value,
            "source": s.source,
        }
        for s in sorted(request.context_signals, key=lambda s: s.signal_id)
    ]

    canonical = {
        "execution_id": request.execution_id,
        "actor": request.actor,
        "proposed_action": request.proposed_action,
        "context_signals": context_signals_canonical,
        "dgic_epistemic_state": {
            "epistemic_state": request.dgic_epistemic_state.epistemic_state,
            "entropy_score": request.dgic_epistemic_state.entropy_score,
            "contradiction_flag": request.dgic_epistemic_state.contradiction_flag,
            "lineage_hash": request.dgic_epistemic_state.lineage_hash,
            "envelope_hash": request.dgic_epistemic_state.envelope_hash,
        },
        "source_system": request.source_system.value,
    }

    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Enforcement Token — The ONLY output Sarathi produces
# ============================================================

@dataclass(frozen=True)
class SarathiEnforcementToken:
    """
    Deterministic enforcement token minted ONLY after RAJYA approval.
    This is the sole gate for Core execution.

    Fields:
      execution_id    — Pipeline canonical ID
      rajya_verdict   — Must be "EXECUTION_APPROVED"
      token_status    — "VALID" (invalid tokens are never created)
      timestamp       — ISO-8601 deterministic timestamp
      signature_hash  — SHA-256(execution_id|rajya_verdict|timestamp)
    """
    execution_id: str
    rajya_verdict: str
    token_status: str
    timestamp: str
    signature_hash: str


# ============================================================
# Token Mint Error
# ============================================================

class SarathiTokenMintError(Exception):
    """Raised when token minting is attempted without RAJYA approval."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"SARATHI TOKEN MINT ERROR [{code}]: {message}")


# ============================================================
# mint_enforcement_token — ONLY if RAJYA = EXECUTION_APPROVED
# ============================================================

def mint_enforcement_token(
    execution_id: str,
    rajya_verdict: str,
    timestamp: str,
) -> SarathiEnforcementToken:
    """
    Mint a deterministic enforcement token.

    Rules:
      - Only generated if rajya_verdict == "EXECUTION_APPROVED"
      - signature_hash = SHA-256(execution_id|rajya_verdict|timestamp)
      - No randomness — fully deterministic
      - token_status is always "VALID" on mint

    Raises:
      SarathiTokenMintError if rajya_verdict != "EXECUTION_APPROVED"
    """
    if rajya_verdict != "EXECUTION_APPROVED":
        logger.error(
            f"SARATHI TOKEN MINT DENIED | execution_id={execution_id} | rajya_verdict={rajya_verdict}",
            extra={
                "event_type": "sarathi_token_mint_denied",
                "execution_id": execution_id,
                "rajya_verdict": rajya_verdict,
            },
        )
        raise SarathiTokenMintError(
            code="RAJYA_NOT_APPROVED",
            message=f"Cannot mint enforcement token: RAJYA verdict is '{rajya_verdict}', not EXECUTION_APPROVED.",
        )

    signature_hash = hashlib.sha256(
        f"{execution_id}|{rajya_verdict}|{timestamp}".encode("utf-8")
    ).hexdigest()

    token = SarathiEnforcementToken(
        execution_id=execution_id,
        rajya_verdict=rajya_verdict,
        token_status="VALID",
        timestamp=timestamp,
        signature_hash=signature_hash,
    )

    logger.info(
        f"SARATHI TOKEN MINTED | execution_id={execution_id} | signature={signature_hash[:16]}...",
        extra={
            "event_type": "sarathi_token_minted",
            "execution_id": execution_id,
            "rajya_verdict": rajya_verdict,
            "token_status": "VALID",
            "timestamp": timestamp,
            "signature_hash": signature_hash,
        },
    )

    return token


# ============================================================
# Hard Block Error — Token gate violation
# ============================================================

class SarathiHardBlockError(Exception):
    """
    Raised when Sarathi token validation fails.
    This is a HARD BLOCK — no fallback, no default, no bypass.
    """
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"SARATHI HARD BLOCK [{code}]: {message}")


# ============================================================
# validate_enforcement_token — Phase 3: Token Validation Engine
# ============================================================

def validate_enforcement_token(
    token: SarathiEnforcementToken,
    pipeline_execution_id: Optional[str] = None,
) -> bool:
    """
    Verify that an enforcement token is structurally valid and untampered.

    Phase 3 Validation Checks (STRICT):
      1. execution_id matches pipeline execution_id (if provided)
      2. rajya_verdict == "EXECUTION_APPROVED"
      3. token_status == "VALID"
      4. signature_hash matches recomputed SHA-256(execution_id|rajya_verdict|timestamp)

    If invalid → HARD BLOCK (returns False, caller must block).

    Returns True if all checks pass, False otherwise.
    """
    # ── CHECK 1: execution_id matches pipeline ──
    if pipeline_execution_id is not None and token.execution_id != pipeline_execution_id:
        logger.error(
            f"SARATHI HARD BLOCK | execution_id mismatch | token={token.execution_id} | pipeline={pipeline_execution_id}",
            extra={
                "event_type": "sarathi_token_hard_block",
                "code": "EXECUTION_ID_MISMATCH",
                "token_execution_id": token.execution_id,
                "pipeline_execution_id": pipeline_execution_id,
            },
        )
        return False

    # ── CHECK 2: RAJYA verdict is APPROVED ──
    if token.rajya_verdict != "EXECUTION_APPROVED":
        logger.error(
            f"SARATHI HARD BLOCK | execution_id={token.execution_id} | reason=rajya_verdict_not_approved | verdict={token.rajya_verdict}",
            extra={
                "event_type": "sarathi_token_hard_block",
                "code": "RAJYA_VERDICT_NOT_APPROVED",
                "execution_id": token.execution_id,
                "rajya_verdict": token.rajya_verdict,
            },
        )
        return False

    # ── CHECK 3: token_status is VALID ──
    if token.token_status != "VALID":
        logger.error(
            f"SARATHI HARD BLOCK | execution_id={token.execution_id} | reason=token_status_invalid | status={token.token_status}",
            extra={
                "event_type": "sarathi_token_hard_block",
                "code": "TOKEN_STATUS_INVALID",
                "execution_id": token.execution_id,
                "token_status": token.token_status,
            },
        )
        return False

    # ── CHECK 4: Token integrity — hash check ──
    expected_hash = hashlib.sha256(
        f"{token.execution_id}|{token.rajya_verdict}|{token.timestamp}".encode("utf-8")
    ).hexdigest()

    if token.signature_hash != expected_hash:
        logger.error(
            f"SARATHI HARD BLOCK | execution_id={token.execution_id} | reason=signature_hash_tampered",
            extra={
                "event_type": "sarathi_token_hard_block",
                "code": "SIGNATURE_HASH_TAMPERED",
                "execution_id": token.execution_id,
                "expected_hash": expected_hash,
                "actual_hash": token.signature_hash,
            },
        )
        return False

    logger.info(
        f"SARATHI TOKEN VALID | execution_id={token.execution_id}",
        extra={
            "event_type": "sarathi_token_validated",
            "execution_id": token.execution_id,
        },
    )
    return True


# ============================================================
# enforce_token — Phase 4: Gate Implementation
# ============================================================

# Gate verdicts — NO other values allowed
_GATE_ALLOW = "ALLOW"
_GATE_BLOCK = "BLOCK"


def enforce_token(
    token: Optional[SarathiEnforcementToken],
    pipeline_execution_id: Optional[str] = None,
) -> str:
    """
    Sarathi Enforcement Gate — the SOLE public interface.

    Rules:
      - VALID token → ALLOW
      - INVALID token → BLOCK
      - Missing token (None) → BLOCK

    NO other logic allowed. NO decision-making. NO risk evaluation.
    This is a pure gate: token in → verdict out.

    Args:
      token: The SarathiEnforcementToken to validate (or None).
      pipeline_execution_id: The canonical pipeline execution_id to match against.

    Returns:
      "ALLOW" — token is valid, Core may execute
      "BLOCK" — token is invalid or missing, Core must NOT execute

    Raises:
      SarathiHardBlockError on BLOCK (if caller needs structured error handling).
    """
    # ── GATE: Missing token → HARD BLOCK ──
    if token is None:
        logger.error(
            "SARATHI GATE BLOCK | reason=token_missing | No enforcement token provided",
            extra={
                "event_type": "sarathi_gate_block",
                "code": "TOKEN_MISSING",
                "pipeline_execution_id": pipeline_execution_id,
            },
        )
        raise SarathiHardBlockError(
            code="TOKEN_MISSING",
            message="No enforcement token provided. Execution blocked.",
        )

    # ── GATE: Validate token (Phase 3 engine) ──
    is_valid = validate_enforcement_token(token, pipeline_execution_id)

    if not is_valid:
        logger.error(
            f"SARATHI GATE BLOCK | execution_id={token.execution_id} | token_status={token.token_status}",
            extra={
                "event_type": "sarathi_gate_block",
                "code": "TOKEN_INVALID",
                "execution_id": token.execution_id,
                "token_status": token.token_status,
                "rajya_verdict": token.rajya_verdict,
            },
        )
        raise SarathiHardBlockError(
            code="TOKEN_INVALID",
            message=f"Enforcement token for execution_id='{token.execution_id}' failed validation. Execution blocked.",
        )

    # ── GATE: ALLOW ──
    logger.info(
        f"SARATHI GATE ALLOW | execution_id={token.execution_id} | signature={token.signature_hash[:16]}...",
        extra={
            "event_type": "sarathi_gate_allow",
            "execution_id": token.execution_id,
            "token_status": token.token_status,
            "signature_hash": token.signature_hash,
        },
    )
    return _GATE_ALLOW

