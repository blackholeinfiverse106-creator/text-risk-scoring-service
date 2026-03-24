"""
Enforcement Gateway Schemas
============================
Strict Pydantic models for the canonical /evaluate_action endpoint.

All fields are validated — no unstructured input or output is permitted.
All types are deterministic and serializable for replay verification.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
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

class EnforcementDecision(str, Enum):
    """
    The deterministic enforcement decision.
    ALLOW             — action is permitted to execute.
    DENY              — action is blocked; execution MUST NOT proceed.
    ABSTAIN           — system cannot evaluate; caller must handle conservatively.
    BLOCK             — Core-specific hard block (equivalent to DENY).
    ESCALATE          — risk too ambiguous for automated decision; requires human review.
    REQUEST_MORE_DATA — insufficient signal evidence to decide; caller must supply more data.
    """
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    REQUEST_MORE_DATA = "REQUEST_MORE_DATA"


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
# Evaluate Action Request
# ============================================================

class EvaluateActionRequest(BaseModel):
    """
    The canonical enforcement evaluation request.
    All BHIV systems submit proposed actions through this schema.
    """
    action_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier for the proposed action"
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

class EvaluateActionResponse(BaseModel):
    """
    The canonical enforcement evaluation response.
    Every field is deterministic and serializable.
    No unstructured output is permitted.
    """
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Final computed risk score [0.0, 1.0]"
    )
    enforcement_decision: EnforcementDecision = Field(
        ...,
        description="ALLOW, DENY, or ABSTAIN — deterministic gate decision"
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
