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
class DGICPayload:
    epistemic_state: EpistemicState
    entropy_score: float
    contradiction_flag: bool

@dataclass(frozen=True)
class DGICInput:
    """The strict schema_v1 epistemic envelope from DGIC."""
    version: str
    lineage_hash: str
    envelope_hash: str
    payload: DGICPayload
    
    # Internal flags
    collapse_flag: bool = False
    
    @property
    def evidence_hash(self) -> str:
        # Legacy property alias for previous pipeline steps
        return self.lineage_hash

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
    """Raised when the DGIC input violates the structural or cryptographic contract."""
    pass


# ============================================================
# Part A — Input Validation
# ============================================================

def build_evidence_hash(text: str) -> str:
    """Stub to simulate computing a hash. (Legacy/Test method)"""
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()

def compute_envelope_hash(version: str, lineage_hash: str, payload_dict: dict) -> str:
    """Computes the deterministic cryptographic seal of a DGIC envelope."""
    import hashlib
    import json
    # Ensure stable sorting for deterministic hashing
    payload_str = json.dumps(payload_dict, sort_keys=True)
    raw = f"{version}|{lineage_hash}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()

def validate_dgic_input(dgic: DGICInput) -> None:
    """
    Validates the structural and cryptographic integrity of the DGIC schema_v1 envelope.
    Raises DGICContractViolation if invalid.
    """
    if not isinstance(dgic, DGICInput):
        raise DGICContractViolation("Input must be a DGICInput instance.")

    if dgic.version != "schema_v1":
        raise DGICContractViolation(f"Unsupported envelope version: {dgic.version}. Expected 'schema_v1'.")
        
    if not isinstance(dgic.lineage_hash, str) or len(dgic.lineage_hash) != 64:
        raise DGICContractViolation("lineage_hash must be a 64-character SHA-256 hex string.")
        
    if not isinstance(dgic.envelope_hash, str) or len(dgic.envelope_hash) != 64:
        raise DGICContractViolation("envelope_hash must be a 64-character SHA-256 hex string.")
        
    if not isinstance(dgic.payload, DGICPayload):
        raise DGICContractViolation("payload must be a valid DGICPayload object.")
        
    if not isinstance(dgic.payload.epistemic_state, EpistemicState):
        raise DGICContractViolation("payload.epistemic_state must be an EpistemicState enum.")
        
    if isinstance(dgic.payload.entropy_score, bool) or not isinstance(dgic.payload.entropy_score, (int, float)):
        raise DGICContractViolation("payload.entropy_score must be a numeric float.")
            
    import math
    if math.isnan(dgic.payload.entropy_score):
         raise DGICContractViolation("payload.entropy_score cannot be NaN (fails range check conceptually).")
         
    if not (0.0 <= dgic.payload.entropy_score <= 1.0):
        raise DGICContractViolation(f"payload.entropy_score {dgic.payload.entropy_score} out of bounds [0.0, 1.0].")
        
    if not isinstance(dgic.payload.contradiction_flag, bool):
        raise DGICContractViolation("payload.contradiction_flag must be a boolean.")
        
    # Cryptographic Seal Verification
    payload_dict = {
        "epistemic_state": dgic.payload.epistemic_state.value,
        "entropy_score": dgic.payload.entropy_score,
        "contradiction_flag": dgic.payload.contradiction_flag
    }
    expected_seal = compute_envelope_hash(dgic.version, dgic.lineage_hash, payload_dict)
    
    if expected_seal != dgic.envelope_hash:
        raise DGICContractViolation("Cryptographic seal broken: envelope_hash does not match payload hash. ENVELOPE TAMPERED.")

    if dgic.payload.epistemic_state == EpistemicState.AMBIGUOUS and dgic.collapse_flag:
        raise DGICContractViolation("Illegal epistemic collapse: AMBIGUOUS state cannot be forcefully collapsed to KNOWN/escalated.")


# ============================================================
# Part B — Epistemic Mapping (Deterministic)
# ============================================================

def adapt_dgic(dgic: DGICInput) -> DGICAdapterResult:
    """
    Deterministically maps the DGIC EpistemicState into scoring parameters.
    No probabilistic inference. No collapse of AMBIGUOUS.
    """
    # Defensive structural validation first
    validate_dgic_input(dgic)
    
    state = dgic.payload.epistemic_state
    entropy = dgic.payload.entropy_score

    if state == EpistemicState.KNOWN:
        result = DGICAdapterResult(
            scoring_mode          = "NORMAL",
            confidence_multiplier = 1.0,
            risk_ceiling          = None,
            epistemic_warning     = False,
            abstain               = False,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    elif state == EpistemicState.INFERRED:
        multiplier = round(1.0 - entropy * INFERRED_ENTROPY_SCALING_FACTOR, 6)
        multiplier = max(0.0, min(1.0, multiplier))  # clamp defensively
        result = DGICAdapterResult(
            scoring_mode          = "CONFIDENCE_SCALED",
            confidence_multiplier = multiplier,
            risk_ceiling          = None,
            epistemic_warning     = False,
            abstain               = False,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    elif state == EpistemicState.AMBIGUOUS:
        # Prevent escalation to HIGH entirely.
        result = DGICAdapterResult(
            scoring_mode          = "RISK_BOUNDED",
            confidence_multiplier = AMBIGUOUS_CONFIDENCE_MULTIPLIER,
            risk_ceiling          = AMBIGUOUS_RISK_CEILING,
            epistemic_warning     = True,
            abstain               = False,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    else:  # EpistemicState.UNKNOWN
        # Fail closed. Abstain.
        result = DGICAdapterResult(
            scoring_mode          = "ABSTAIN",
            confidence_multiplier = 0.0,
            risk_ceiling          = UNKNOWN_RISK_CEILING,
            epistemic_warning     = True,
            abstain               = True,
            evidence_hash         = dgic.lineage_hash,
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

# Abstention error code
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
    Returns a NEW dict.
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
        return result

    # --- CONFIDENCE_SCALED ---
    if mode == "CONFIDENCE_SCALED":
        raw_conf = result.get("confidence_score", 1.0)
        scaled   = round(
            max(0.0, min(1.0, raw_conf * adapter_result.confidence_multiplier)),
            2
        )
        result["confidence_score"] = scaled

    # --- RISK_BOUNDED ---
    elif mode == "RISK_BOUNDED":
        ceiling = adapter_result.risk_ceiling
        raw_score = result.get("risk_score", 0.0)
        if ceiling is not None and raw_score > ceiling:
            clamped = round(ceiling, 2)
            result["risk_score"] = clamped
            result["risk_category"] = _score_to_category(clamped)
        
        raw_conf = result.get("confidence_score", 1.0)
        result["confidence_score"] = round(
            max(0.0, min(1.0, raw_conf * adapter_result.confidence_multiplier)), 2
        )

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


def _score_to_category(score: float) -> str:
    """Recalculate risk_category from a (possibly clamped) score."""
    if score < 0.3:
        return "LOW"
    elif score < 0.7:
        return "MEDIUM"
    else:
        return "HIGH"
