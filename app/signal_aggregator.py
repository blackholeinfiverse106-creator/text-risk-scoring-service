"""
Multi-Signal Enforcement Aggregator
====================================
Accepts multiple (signal_type, base_score, base_confidence, dgic_envelope) tuples,
and deterministically aggregates them into a single enforcement-grade signal output.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - Aggregation CANNOT silently escalate on contradictions.
  - safety_metadata.authority remains "NONE" in all outputs.
  - safety_metadata.is_decision remains False in all outputs.
  - All aggregation operations are purely algebraic — no ML, no probabilistic inference.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any

from app.dgic_adapter import (
    DGICInput,
    DGICAdapterResult,
    EpistemicState,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    DGICContractViolation,
    ABSTENTION_ERROR_CODE,
)
from app.enforcement_aggregator import (
    AggregationContractViolation,
    MAX_AGGREGATE_SCORE,
    CONTRADICTION_PENALTY_FACTOR,
    CONTRADICTION_FLOOR,
    MIN_SIGNALS,
    MAX_SIGNALS,
    LOW_THRESHOLD,
    HIGH_THRESHOLD,
    _SAFETY_METADATA,
    _ABSTAIN_ALL_ERROR,
    _score_to_category
)

logger = logging.getLogger(__name__)

# ============================================================
# Signal Types & Weighting Constants
# ============================================================

class SignalType(str, Enum):
    TEXT_RISK_SIGNAL = "TEXT_RISK_SIGNAL"
    BEHAVIOR_ANOMALY_SIGNAL = "BEHAVIOR_ANOMALY_SIGNAL"
    POLICY_VIOLATION_SIGNAL = "POLICY_VIOLATION_SIGNAL"
    EXTERNAL_DETECTOR_SIGNAL = "EXTERNAL_DETECTOR_SIGNAL"

SIGNAL_WEIGHTS = {
    SignalType.POLICY_VIOLATION_SIGNAL: 1.5,
    SignalType.BEHAVIOR_ANOMALY_SIGNAL: 1.2,
    SignalType.TEXT_RISK_SIGNAL: 1.0,
    SignalType.EXTERNAL_DETECTOR_SIGNAL: 0.8,
}

# ============================================================
# Input / Output Dataclasses
# ============================================================

@dataclass(frozen=True)
class UnifiedSignal:
    """
    A single unified signal fed into the multi-signal aggregator.
    """
    signal_id: str
    signal_type: SignalType
    base_risk_score: float
    base_confidence_score: float
    dgic_envelope: DGICInput


@dataclass(frozen=True)
class ScoredUnifiedSignal:
    """
    The fully-scored output for a single unified signal input.
    """
    signal_id: str
    signal_type: SignalType
    risk_score: float
    confidence_score: float
    risk_category: str
    epistemic_state: EpistemicState
    scoring_mode: str
    abstained: bool
    epistemic_warning: bool
    contradiction_flag: bool
    evidence_hash: str
    effective_weight: float


@dataclass(frozen=True)
class AggregatedUnifiedSignal:
    """
    Final aggregated output across N unified signals.
    """
    aggregate_risk_score: float
    aggregate_confidence: float
    aggregate_risk_category: str
    signal_count: int
    active_signal_count: int
    abstained_signal_count: int
    contradiction_count: int
    contradiction_density: float
    contradiction_penalty_applied: float
    epistemic_warning: bool
    any_abstained: bool
    all_abstained: bool
    scored_signals: List[ScoredUnifiedSignal]
    safety_metadata: dict
    errors: Optional[dict]
    aggregation_hash: str


# ============================================================
# Input validation
# ============================================================

def validate_unified_signals(signals: List[UnifiedSignal]) -> None:
    """
    Validate the unified signal input list structurally.
    """
    if not isinstance(signals, list):
        raise AggregationContractViolation("INVALID_SIGNALS_TYPE", f"signals must be a list, got {type(signals).__name__}")
    if len(signals) < MIN_SIGNALS:
        raise AggregationContractViolation("EMPTY_SIGNALS", "At least one signal is required")
    if len(signals) > MAX_SIGNALS:
        raise AggregationContractViolation("EXCESSIVE_SIGNALS", f"Maximum {MAX_SIGNALS} signals per aggregation call, got {len(signals)}")

    for i, sig in enumerate(signals):
        if not isinstance(sig, UnifiedSignal):
            raise AggregationContractViolation("INVALID_SIGNAL_ELEMENT", f"signals[{i}] must be a UnifiedSignal instance")
        if not isinstance(sig.signal_type, SignalType):
            raise AggregationContractViolation("INVALID_SIGNAL_TYPE", f"signals[{i}].signal_type must be a valid SignalType, got {sig.signal_type}")
        if not isinstance(sig.base_risk_score, float) or not (0.0 <= sig.base_risk_score <= 1.0):
            raise AggregationContractViolation("INVALID_RISK_SCORE", f"signals[{i}].base_risk_score must be a float in [0.0, 1.0]")
        if not isinstance(sig.base_confidence_score, float) or not (0.0 <= sig.base_confidence_score <= 1.0):
            raise AggregationContractViolation("INVALID_CONFIDENCE_SCORE", f"signals[{i}].base_confidence_score must be a float in [0.0, 1.0]")
        try:
            validate_dgic_input(sig.dgic_envelope)
        except DGICContractViolation as e:
            raise AggregationContractViolation("INVALID_SIGNAL_DGIC", f"signals[{i}] DGIC envelope invalid: {e.code}: {e.message}") from e


# ============================================================
# Unified Per-signal scoring
# ============================================================

def _score_unified_signal(signal: UnifiedSignal) -> ScoredUnifiedSignal:
    """
    Score one UnifiedSignal through the DGIC adapter modifiers.
    """
    # Create the simulated 'base_result' dictionary that the DGIC modifier expects
    base_result = {
        "risk_score": signal.base_risk_score,
        "confidence_score": signal.base_confidence_score,
        "risk_category": _score_to_category(signal.base_risk_score),
        "processed_length": 0,
        "trigger_reasons": []
    }
    
    adapter_result = adapt_dgic(signal.dgic_envelope)
    modified = apply_dgic_modifiers(base_result, adapter_result)
    
    abstained = adapter_result.abstain
    
    risk_score = round(modified.get("risk_score", 0.0), 4)
    confidence_score = round(modified.get("confidence_score", 0.0), 4)
    
    # Calculate the effective weight: static weight * scaled confidence (only if not abstained)
    effective_weight = 0.0
    if not abstained:
        effective_weight = SIGNAL_WEIGHTS[signal.signal_type] * confidence_score

    return ScoredUnifiedSignal(
        signal_id=signal.signal_id,
        signal_type=signal.signal_type,
        risk_score=risk_score,
        confidence_score=confidence_score,
        risk_category=modified.get("risk_category", "LOW"),
        epistemic_state=adapter_result.epistemic_state,
        scoring_mode=adapter_result.scoring_mode,
        abstained=abstained,
        epistemic_warning=adapter_result.epistemic_warning,
        contradiction_flag=signal.dgic_envelope.payload.contradiction_flag,
        evidence_hash=adapter_result.evidence_hash,
        effective_weight=effective_weight
    )


def _compute_unified_aggregation_hash(signals: List[UnifiedSignal]) -> str:
    """
    Stable SHA-256 fingerprint of the unified aggregation inputs.
    """
    fingerprint = [
        {
            "signal_id": sig.signal_id,
            "signal_type": sig.signal_type.value,
            "base_risk_score": sig.base_risk_score,
            "base_confidence_score": sig.base_confidence_score,
            "epistemic_state": sig.dgic_envelope.payload.epistemic_state.value,
            "entropy_score": sig.dgic_envelope.payload.entropy_score,
            "contradiction_flag": sig.dgic_envelope.payload.contradiction_flag,
            "collapse_flag": sig.dgic_envelope.collapse_flag,
            "evidence_hash": sig.dgic_envelope.evidence_hash,
        }
        for sig in signals
    ]
    serialised = json.dumps(fingerprint, sort_keys=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ============================================================
# Main aggregation entry point for unified signals
# ============================================================

def aggregate_unified_signals(signals: List[UnifiedSignal]) -> AggregatedUnifiedSignal:
    """
    Deterministically aggregate N UnifiedSignal objects.
    
    Steps:
      1. Validate all inputs structurally.
      2. Score each signal through its DGIC adapter independently.
      3. Separate abstained signals from active ones.
      4. Compute contradiction density from contradiction_flag across ALL signals.
      5. Calculate Weighted mean of active risk scores using `effective_weight` (weight * confidence).
      6. Apply contradiction penalty to raw aggregate.
      7. Clamp to MAX_AGGREGATE_SCORE.
      8. Derive risk_category from clamped score.
      9. Compute aggregate confidence (arithmetic mean of active confidences).
      10. Re-assert safety_metadata invariants.
    """
    validate_unified_signals(signals)

    agg_hash = _compute_unified_aggregation_hash(signals)
    n = len(signals)

    logger.info("Unified aggregation started", extra={"event_type": "unified_aggregation_start", "signal_count": n, "aggregation_hash": agg_hash})

    # Step 2: Score all signals
    scored: List[ScoredUnifiedSignal] = []
    for sig in signals:
        scored_sig = _score_unified_signal(sig)
        scored.append(scored_sig)
        logger.info(
            "Unified signal scored", 
            extra={
                "event_type": "unified_signal_scored", 
                "signal_id": scored_sig.signal_id,
                "epistemic_state": scored_sig.epistemic_state.value, 
                "scoring_mode": scored_sig.scoring_mode,
                "risk_score": scored_sig.risk_score, 
                "abstained": scored_sig.abstained
            }
        )

    # Step 3: Partition
    active = [s for s in scored if not s.abstained]
    abstained = [s for s in scored if s.abstained]

    # Step 4: Contradiction density (across ALL signals)
    contradiction_count = sum(1 for s in scored if s.contradiction_flag)
    contradiction_density = round(contradiction_count / n, 6)

    # Step 5: Weighted mean of active risk scores
    if not active:
        # All signals abstained — emit structured abstention
        return AggregatedUnifiedSignal(
            aggregate_risk_score=0.0,
            aggregate_confidence=0.0,
            aggregate_risk_category="LOW",
            signal_count=n,
            active_signal_count=0,
            abstained_signal_count=len(abstained),
            contradiction_count=contradiction_count,
            contradiction_density=contradiction_density,
            contradiction_penalty_applied=1.0,
            epistemic_warning=True,
            any_abstained=True,
            all_abstained=True,
            scored_signals=scored,
            safety_metadata=dict(_SAFETY_METADATA),
            errors=dict(_ABSTAIN_ALL_ERROR),
            aggregation_hash=agg_hash,
        )

    total_weight = sum(s.effective_weight for s in active)
    if total_weight == 0.0:
        raw_aggregate = sum(s.risk_score for s in active) / len(active)
    else:
        raw_aggregate = sum(s.risk_score * s.effective_weight for s in active) / total_weight

    # Step 6: Contradiction penalty
    penalty_factor = round(1.0 - contradiction_density * CONTRADICTION_PENALTY_FACTOR, 6)
    penalty_factor = max(0.0, min(1.0, penalty_factor))
    penalised = max(CONTRADICTION_FLOOR, raw_aggregate * penalty_factor)

    # Step 7: Clamp
    clamped = round(min(MAX_AGGREGATE_SCORE, penalised), 4)

    # Step 8: Risk category
    agg_category = _score_to_category(clamped)

    # Step 9: Aggregate confidence (mean of active confidences)
    agg_confidence = round(sum(s.confidence_score for s in active) / len(active), 4)

    # Step 10: Flags
    any_warn = any(s.epistemic_warning for s in scored)
    any_abstain = len(abstained) > 0

    logger.info(
        "Unified aggregation complete",
        extra={
            "event_type": "unified_aggregation_complete",
            "raw_aggregate": raw_aggregate,
            "penalised": penalised,
            "clamped": clamped,
            "contradiction_density": contradiction_density,
            "penalty_factor": penalty_factor,
            "aggregate_risk_category": agg_category,
            "active_signals": len(active),
            "abstained_signals": len(abstained),
        }
    )

    return AggregatedUnifiedSignal(
        aggregate_risk_score=clamped,
        aggregate_confidence=agg_confidence,
        aggregate_risk_category=agg_category,
        signal_count=n,
        active_signal_count=len(active),
        abstained_signal_count=len(abstained),
        contradiction_count=contradiction_count,
        contradiction_density=contradiction_density,
        contradiction_penalty_applied=round(penalty_factor, 6),
        epistemic_warning=any_warn,
        any_abstained=any_abstain,
        all_abstained=False,
        scored_signals=scored,
        safety_metadata=dict(_SAFETY_METADATA),
        errors=None,
        aggregation_hash=agg_hash,
    )
