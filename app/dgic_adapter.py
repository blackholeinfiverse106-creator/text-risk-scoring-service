"""
DGIC Integration Adapter
========================
Consumes structured epistemic outputs from the Deterministic Graph Intelligence Core (DGIC)
and maps them deterministically to scoring behaviour modifiers.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority from DGIC fields.
  - This module NEVER collapses Ambiguous epistemic state into a binary decision.
  - safety_metadata.is_decision remains False under ALL epistemic states.
  - safety_metadata.authority remains "NONE" under ALL epistemic states.
  - All transformations are purely structural — no ML, no probabilistic inference.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

# Confidence scaling: how much entropy reduces confidence under INFERRED state.
# confidence_multiplier = 1.0 - entropy_score * INFERRED_ENTROPY_SCALING_FACTOR
INFERRED_ENTROPY_SCALING_FACTOR = 0.4

# Under AMBIGUOUS state the risk score is capped below the HIGH threshold.
# 0.69 keeps the score in MEDIUM range at worst — the system cannot escalate
# an ambiguous signal to HIGH on its own.
AMBIGUOUS_RISK_CEILING = 0.69

# Confidence multiplier applied when state is AMBIGUOUS — signals are contradictory.
AMBIGUOUS_CONFIDENCE_MULTIPLIER = 0.5

# Abstention ceiling: UNKNOWN state forces risk_score to 0.0.
UNKNOWN_RISK_CEILING = 0.0

# Valid entropy score range
ENTROPY_MIN = 0.0
ENTROPY_MAX = 1.0


# ============================================================
# Epistemic State Enum
# ============================================================

class EpistemicState(str, Enum):
    """
    The four epistemic states emitted by DGIC.

    KNOWN     — The intelligence core has high-confidence, grounded evidence.
    INFERRED  — Evidence exists but confidence is reduced by entropy.
    AMBIGUOUS — Contradictory or insufficient signals; state must NOT be collapsed.
    UNKNOWN   — No epistemic grounding available; system must abstain.
    """
    KNOWN     = "KNOWN"
    INFERRED  = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN   = "UNKNOWN"


# ============================================================
# Input / Output Dataclasses
# ============================================================

@dataclass(frozen=True)
class DGICInput:
    """
    Structured epistemic output from DGIC.
    All five fields are required; none may be absent or None.

    Fields:
        epistemic_state   : Epistemic certainty level of the DGIC assessment.
        entropy_score     : Measure of information uncertainty in [0.0, 1.0].
                            0.0 = fully ordered; 1.0 = maximum entropy.
        contradiction_flag: True if DGIC detected internal evidence contradictions.
        collapse_flag     : True if DGIC collapsed a superposition during processing.
                            MUST NOT be used by this adapter to derive authority.
        evidence_hash     : Opaque SHA-256 fingerprint of the evidence chain.
                            Passed through unmodified. Never inspected for content.
    """
    epistemic_state:    EpistemicState
    entropy_score:      float
    contradiction_flag: bool
    collapse_flag:      bool
    evidence_hash:      str


@dataclass(frozen=True)
class DGICAdapterResult:
    """
    The output of epistemic adaptation.

    Fields:
        scoring_mode           : How the engine result should be modified.
                                 One of: NORMAL | CONFIDENCE_SCALED | RISK_BOUNDED | ABSTAIN
        confidence_multiplier  : Factor applied to the engine's raw confidence_score.
        risk_ceiling           : Upper bound on risk_score (None = no ceiling).
        epistemic_warning      : True when epistemic state is ambiguous or unknown.
        abstain                : True when the system must not emit a risk signal.
        evidence_hash          : DGIC evidence_hash passed through unmodified.
        epistemic_state        : Original state, retained for auditability.
    """
    scoring_mode:          str
    confidence_multiplier: float
    risk_ceiling:          Optional[float]
    epistemic_warning:     bool
    abstain:               bool
    evidence_hash:         str
    epistemic_state:       EpistemicState


# ============================================================
# Contract Violation
# ============================================================

class DGICContractViolation(Exception):
    """Raised when DGICInput fails structural validation."""
    def __init__(self, code: str, message: str):
        self.code    = code
        self.message = message
        super().__init__(f"{code}: {message}")


# ============================================================
# Part A — Input Validation
# ============================================================

def validate_dgic_input(dgic: Any) -> None:
    """
    Structural contract check for DGICInput.
    Raises DGICContractViolation on any violation.

    Rules:
      - Must be a DGICInput instance
      - epistemic_state must be a valid EpistemicState
      - entropy_score must be float/int in [0.0, 1.0]
      - contradiction_flag must be bool
      - collapse_flag must be bool (never used to derive authority)
      - evidence_hash must be a non-empty string
    """
    if not isinstance(dgic, DGICInput):
        raise DGICContractViolation(
            "INVALID_DGIC_TYPE",
            f"Expected DGICInput, got {type(dgic).__name__}"
        )

    if not isinstance(dgic.epistemic_state, EpistemicState):
        raise DGICContractViolation(
            "INVALID_EPISTEMIC_STATE",
            f"epistemic_state must be an EpistemicState member, got {dgic.epistemic_state!r}"
        )

    if isinstance(dgic.entropy_score, bool) or not isinstance(dgic.entropy_score, (int, float)):
        raise DGICContractViolation(
            "INVALID_ENTROPY_TYPE",
            "entropy_score must be a float in [0.0, 1.0]"
        )
    if not (ENTROPY_MIN <= dgic.entropy_score <= ENTROPY_MAX):
        raise DGICContractViolation(
            "INVALID_ENTROPY_RANGE",
            f"entropy_score must be in [{ENTROPY_MIN}, {ENTROPY_MAX}], got {dgic.entropy_score}"
        )

    if not isinstance(dgic.contradiction_flag, bool):
        raise DGICContractViolation(
            "INVALID_CONTRADICTION_FLAG",
            "contradiction_flag must be a bool"
        )

    if not isinstance(dgic.collapse_flag, bool):
        raise DGICContractViolation(
            "INVALID_COLLAPSE_FLAG",
            "collapse_flag must be a bool"
        )

    if not isinstance(dgic.evidence_hash, str) or not dgic.evidence_hash.strip():
        raise DGICContractViolation(
            "INVALID_EVIDENCE_HASH",
            "evidence_hash must be a non-empty string"
        )


# ============================================================
# Part B — Epistemic Mapping (Deterministic)
# ============================================================

def adapt_dgic(dgic: DGICInput) -> DGICAdapterResult:
    """
    Maps a validated DGICInput to a DGICAdapterResult deterministically.

    Epistemic state mapping:

      KNOWN     → NORMAL scoring.   confidence_multiplier=1.0. No ceiling. No warning.
      INFERRED  → CONFIDENCE_SCALED. Multiplier reduced by entropy (1.0 - entropy * 0.4).
                  No risk ceiling. No warning flag.
      AMBIGUOUS → RISK_BOUNDED.    risk capped at 0.69 (below HIGH threshold).
                  confidence_multiplier=0.5. epistemic_warning=True.
                  Ambiguity is NOT collapsed — the system emits a bounded signal only.
      UNKNOWN   → ABSTAIN.          risk_ceiling=0.0. confidence_multiplier=0.0.
                  abstain=True. epistemic_warning=True.
                  System emits no risk signal when there is no epistemic grounding.

    Note: contradiction_flag and collapse_flag do NOT alter the scoring mode.
    They are preserved in the audit trail but confer no additional authority.
    """
    validate_dgic_input(dgic)

    state = dgic.epistemic_state

    if state == EpistemicState.KNOWN:
        result = DGICAdapterResult(
            scoring_mode          = "NORMAL",
            confidence_multiplier = 1.0,
            risk_ceiling          = None,
            epistemic_warning     = False,
            abstain               = False,
            evidence_hash         = dgic.evidence_hash,
            epistemic_state       = state,
        )

    elif state == EpistemicState.INFERRED:
        # Confidence is scaled down proportionally to entropy.
        # A high-entropy (uncertain) inference warrants lower confidence.
        multiplier = round(1.0 - dgic.entropy_score * INFERRED_ENTROPY_SCALING_FACTOR, 6)
        multiplier = max(0.0, min(1.0, multiplier))  # clamp defensively
        result = DGICAdapterResult(
            scoring_mode          = "CONFIDENCE_SCALED",
            confidence_multiplier = multiplier,
            risk_ceiling          = None,
            epistemic_warning     = False,
            abstain               = False,
            evidence_hash         = dgic.evidence_hash,
            epistemic_state       = state,
        )

    elif state == EpistemicState.AMBIGUOUS:
        # Risk is bounded below HIGH. Ambiguity is preserved — we do NOT decide.
        # The warning flag surfaces to downstream consumers.
        result = DGICAdapterResult(
            scoring_mode          = "RISK_BOUNDED",
            confidence_multiplier = AMBIGUOUS_CONFIDENCE_MULTIPLIER,
            risk_ceiling          = AMBIGUOUS_RISK_CEILING,
            epistemic_warning     = True,
            abstain               = False,
            evidence_hash         = dgic.evidence_hash,
            epistemic_state       = state,
        )

    else:  # EpistemicState.UNKNOWN
        result = DGICAdapterResult(
            scoring_mode          = "ABSTAIN",
            confidence_multiplier = 0.0,
            risk_ceiling          = UNKNOWN_RISK_CEILING,
            epistemic_warning     = True,
            abstain               = True,
            evidence_hash         = dgic.evidence_hash,
            epistemic_state       = state,
        )

    logger.info(
        "DGIC adapter mapped epistemic state",
        extra={
            "event_type":         "dgic_adaptation",
            "epistemic_state":    state.value,
            "scoring_mode":       result.scoring_mode,
            "confidence_mult":    result.confidence_multiplier,
            "risk_ceiling":       result.risk_ceiling,
            "epistemic_warning":  result.epistemic_warning,
            "abstain":            result.abstain,
        }
    )

    return result


# ============================================================
# Part A — Score Modifier Application
# ============================================================

# Abstention error code — not in the existing v3 VALID_ERROR_CODES set.
# This is an integration-layer code, not a contract-layer code.
ABSTENTION_ERROR_CODE = "EPISTEMIC_ABSTENTION"

# Frozen safety_metadata — always identical, never derived from DGIC.
_SAFETY_METADATA: Dict[str, Any] = {
    "is_decision": False,
    "authority":   "NONE",
    "actionable":  False,
}


def apply_dgic_modifiers(
    base_result:    Dict[str, Any],
    adapter_result: DGICAdapterResult,
) -> Dict[str, Any]:
    """
    Applies DGIC-derived modifiers to a base engine result.
    Returns a NEW dict — does not mutate base_result.

    The returned dict:
      - Preserves all v3 contract fields unchanged (plus applied modifiers).
      - Adds a 'dgic_metadata' key (outside v3 contract — library-only for Day 1).
      - ALWAYS has safety_metadata = {is_decision: False, authority: "NONE", actionable: False}.

    Scoring modes:
      NORMAL           — No score modification. dgic_metadata passthrough.
      CONFIDENCE_SCALED — confidence_score *= confidence_multiplier (clamped to [0.0, 1.0]).
      RISK_BOUNDED      — risk_score clamped to risk_ceiling; risk_category recalculated.
                          epistemic_warning added to dgic_metadata.
      ABSTAIN           — Full abstention. risk_score=0.0, risk_category="LOW",
                          errors set to EPISTEMIC_ABSTENTION.
    """
    import copy
    result = copy.deepcopy(base_result)

    mode    = adapter_result.scoring_mode
    state   = adapter_result.epistemic_state

    # --- ABSTAIN ---
    if adapter_result.abstain:
        result["risk_score"]       = 0.0
        result["confidence_score"] = 0.0
        result["risk_category"]    = "LOW"
        result["trigger_reasons"]  = []
        result["processed_length"] = result.get("processed_length", 0)
        result["safety_metadata"]  = dict(_SAFETY_METADATA)
        result["errors"] = {
            "error_code": ABSTENTION_ERROR_CODE,
            "message":    (
                "Epistemic abstention: no grounded evidence available. "
                "Risk signal suppressed by DGIC UNKNOWN state."
            ),
        }
        result["dgic_metadata"] = {
            "epistemic_state":   state.value,
            "scoring_mode":      mode,
            "epistemic_warning": True,
            "evidence_hash":     adapter_result.evidence_hash,
        }
        logger.warning(
            "Epistemic abstention applied — risk signal suppressed",
            extra={"event_type": "dgic_abstention", "epistemic_state": state.value}
        )
        return result

    # --- CONFIDENCE_SCALED ---
    if mode == "CONFIDENCE_SCALED":
        raw_conf = result.get("confidence_score", 1.0)
        scaled   = round(
            max(0.0, min(1.0, raw_conf * adapter_result.confidence_multiplier)),
            2
        )
        result["confidence_score"] = scaled
        logger.info(
            "Confidence scaled by DGIC entropy",
            extra={
                "event_type":       "dgic_confidence_scale",
                "multiplier":       adapter_result.confidence_multiplier,
                "original_conf":    raw_conf,
                "scaled_conf":      scaled,
            }
        )

    # --- RISK_BOUNDED ---
    elif mode == "RISK_BOUNDED":
        ceiling = adapter_result.risk_ceiling
        raw_score = result.get("risk_score", 0.0)
        if ceiling is not None and raw_score > ceiling:
            clamped = round(ceiling, 2)
            result["risk_score"] = clamped
            # Recalculate risk_category from clamped score
            result["risk_category"] = _score_to_category(clamped)
            logger.warning(
                "Risk score bounded by DGIC AMBIGUOUS state",
                extra={
                    "event_type":   "dgic_risk_bounded",
                    "raw_score":    raw_score,
                    "ceiling":      ceiling,
                    "clamped_score": clamped,
                }
            )
        # Scale confidence too
        raw_conf = result.get("confidence_score", 1.0)
        result["confidence_score"] = round(
            max(0.0, min(1.0, raw_conf * adapter_result.confidence_multiplier)), 2
        )

    # NORMAL — no score changes

    # --- Authority invariant re-assertion (defensive) ---
    result["safety_metadata"] = dict(_SAFETY_METADATA)

    # --- dgic_metadata sidecar ---
    result["dgic_metadata"] = {
        "epistemic_state":   state.value,
        "scoring_mode":      mode,
        "epistemic_warning": adapter_result.epistemic_warning,
        "evidence_hash":     adapter_result.evidence_hash,
    }

    return result


# ============================================================
# Helpers
# ============================================================

def _score_to_category(score: float) -> str:
    """Recalculate risk_category from a (possibly clamped) score.
    Mirrors the threshold logic in engine.py exactly."""
    if score < 0.3:
        return "LOW"
    elif score < 0.7:
        return "MEDIUM"
    else:
        return "HIGH"


def build_evidence_hash(text: str) -> str:
    """
    Utility: generate a stable SHA-256 evidence_hash from arbitrary text.
    For use in tests and replay harness. Evidence hash is opaque to the adapter.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
