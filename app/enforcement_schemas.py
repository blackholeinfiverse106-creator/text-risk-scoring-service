"""
Enforcement Gateway Schemas
============================
Strict Pydantic models for the canonical /evaluate_action endpoint.

All fields are validated — no unstructured input or output is permitted.
All types are deterministic and serializable for replay verification.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ============================================================
# Source System Enum — All BHIV consumers
# ============================================================

class SourceSystem(str, Enum):
    """
    Every BHIV system that submits actions for enforcement validation.
    No unknown source systems are accepted.
    """
    AI_BEING = "AI_BEING"
    MARINE_INTELLIGENCE = "MARINE_INTELLIGENCE"
    AIAIC = "AIAIC"
    C4S = "C4S"
    INSIGHTBRIDGE = "INSIGHTBRIDGE"
    SOVEREIGN_CORE = "SOVEREIGN_CORE"


# ============================================================
# Enforcement Decision Enum
# ============================================================

class SarathiDecision(str, Enum):
    """
    The authoritative governance decision made by the Sarathi layer.
    """
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


class EnforcementDecision(str, Enum):
    """
    The deterministic enforcement decision.
    ALLOW   — action is permitted to execute.
    DENY    — action is blocked; execution MUST NOT proceed.
    ABSTAIN — system cannot evaluate; caller must handle conservatively.

    Sovereign Law: No BLOCK, ESCALATE, or REQUEST_MORE_DATA.
    Those are execution/intelligence concepts that violate enforcement boundaries.
    """
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


# ============================================================
# Context Signal Schema
# ============================================================

class ContextSignal(BaseModel):
    """
    A single intelligence signal from any upstream system.
    """
    signal_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier for this signal"
    )
    signal_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Type classification of the signal (e.g., 'threat', 'anomaly', 'environmental')"
    )
    value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Signal intensity value, clamped to [0.0, 1.0]"
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Originating subsystem or sensor"
    )


# ============================================================
# DGIC Epistemic State Input
# ============================================================

class DGICEpistemicStateInput(BaseModel):
    """
    The DGIC epistemic state snapshot for enforcement evaluation.
    This is consumed read-only — enforcement NEVER mutates upstream epistemic state.
    """
    epistemic_state: str = Field(
        ...,
        description="One of: KNOWN, INFERRED, AMBIGUOUS, UNKNOWN"
    )
    entropy_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Entropy score from DGIC [0.0, 1.0]"
    )
    contradiction_flag: bool = Field(
        ...,
        description="True if DGIC detected contradictory evidence"
    )
    lineage_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="64-character SHA-256 lineage hash from DGIC"
    )
    envelope_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="64-character SHA-256 envelope hash — cryptographic seal"
    )

    @field_validator("epistemic_state")
    @classmethod
    def validate_epistemic_state(cls, v: str) -> str:
        valid = {"KNOWN", "INFERRED", "AMBIGUOUS", "UNKNOWN"}
        if v not in valid:
            raise ValueError(f"epistemic_state must be one of {valid}, got '{v}'")
        return v


# ============================================================
# KSML Input (Phase 6)
# ============================================================

class KSMLInput(BaseModel):
    """
    Phase 6 Boundary Defense: KSML Canonical Input Envelope.
    Only KSML formatted inputs are allowed at the Sūtradhāra edge.
    """
    execution_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Global unique identifier"
    )
    structured_signals: List[ContextSignal] = Field(
        default_factory=list,
        description="List of KSML contextual signals"
    )
    metadata: Dict[str, Any] = Field(
        ...,
        description="Strict namespace for legacy actor/proposed_action/source_system details"
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata_fields(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure critical routing headers exist inside the KSML metadata block."""
        required = {"actor", "proposed_action", "source_system", "dgic_epistemic_state"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"KSML metadata missing required canonical fields: {sorted(missing)}")
        return v


# ============================================================
# Evaluate Action Request
# ============================================================

class EvaluateActionRequest(BaseModel):
    """
    The canonical enforcement evaluation request.
    All BHIV systems submit proposed actions through this schema.
    """
    execution_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Global unique identifier for the execution pipeline"
    )
    actor: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Identity of the entity proposing the action"
    )
    proposed_action: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Text description of the proposed action"
    )
    context_signals: List[ContextSignal] = Field(
        default_factory=list,
        max_length=50,
        description="Optional upstream intelligence signals (0-50)"
    )
    dgic_epistemic_state: DGICEpistemicStateInput = Field(
        ...,
        description="DGIC epistemic state snapshot — consumed read-only"
    )
    source_system: SourceSystem = Field(
        ...,
        description="The BHIV subsystem submitting the action for enforcement"
    )


# ============================================================
# Evaluate Action Response
# ============================================================

class SarathiEvaluateResponse(BaseModel):
    """
    The canonical governance evaluation response from Sarathi.
    Every field is deterministic and serializable.
    No unstructured output is permitted.
    """
    execution_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Global unique identifier for this evaluation"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final computed risk score [0.0, 1.0]"
    )
    sarathi_decision: SarathiDecision = Field(
        ...,
        description="ALLOW, DENY, or ABSTAIN — authoritarian governance decision"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Decision confidence [0.0, 1.0], scaled by epistemic state"
    )
    failure_reason: Optional[str] = Field(
        None,
        description="Null on ALLOW. Structured reason string on DENY or ABSTAIN."
    )
    trace_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 of all inputs — deterministic replay verification key"
    )


# ============================================================
# Execute Action Request (For Enforcement Gate)
# ============================================================

class ExecuteActionRequest(BaseModel):
    """
    The canonical enforcement request sent to the Execution Gate,
    carrying the explicit, approved Sarathi decision.
    """
    execution_id: str = Field(..., max_length=128, description="Global specific execution ID")
    actor: str = Field(..., max_length=256)
    source_system: SourceSystem
    sarathi_response: SarathiEvaluateResponse = Field(
        ...,
        description="The authoritative governance decision from Sarathi"
    )


# ============================================================
# Execute Action Response
# ============================================================

class ExecuteActionResponse(BaseModel):
    """
    The final executed response showing if the gate allowed it.
    """
    execution_id: str = Field(
        ...,
        description="Global execution ID tracked through the enforcement pipeline"
    )
    enforcement_decision: EnforcementDecision = Field(
        ...,
        description="The final gate decision (e.g. ALLOW, DENY, BLOCK)"
    )
    executed: bool = Field(
        ...,
        description="True ONLY if the enforcement gate permitted execution"
    )
    trace_hash: str = Field(
        ...,
        description="The trace hash of the Sarathi evaluation"
    )
