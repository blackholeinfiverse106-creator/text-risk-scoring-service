from __future__ import annotations
"""
Sovereign Layer File: app/layer6_insightbridge.py
"""


# ==================================================
# Source: app/signal_aggregator.py
# ==================================================

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


import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any

from app.layer3_dgic import (
    DGICInput,
    DGICAdapterResult,
    EpistemicState,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    DGICContractViolation,
    ABSTENTION_ERROR_CODE,
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

# ==================================================
# Source: app/enforcement_aggregator.py
# ==================================================

"""
Multi-Signal Enforcement Aggregator
====================================
Accepts multiple (text, DGICInput) signal pairs, scores each individually,
and deterministically aggregates them into a single enforcement-grade signal.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - Aggregation CANNOT silently escalate on contradictions.
  - safety_metadata.authority remains "NONE" in all outputs.
  - safety_metadata.is_decision remains False in all outputs.
  - All aggregation operations are purely algebraic — no ML, no probabilistic inference.

Aggregation Algebra (summary — see multi_signal_algebra.md for full proof):
  1. Each signal is scored independently: score_i, confidence_i, state_i
  2. Contradiction density D = (# contradicting signals) / (# total signals)
  3. Raw aggregate = weighted mean of non-abstained scores, weights = confidence_i
  4. Contradiction penalty: aggregate *= (1 - D * CONTRADICTION_PENALTY_FACTOR)
  5. Global ceiling = MAX_AGGREGATE_SCORE (prevents saturation from signal volume)
  6. risk_category derived from clamped aggregate (standard 0.3 / 0.7 thresholds)
"""


import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.layer0_intelligence import analyze_text
from app.layer3_dgic import (
    DGICInput,
    DGICAdapterResult,
    EpistemicState,
    validate_dgic_input,
    adapt_dgic,
    apply_dgic_modifiers,
    DGICContractViolation,
    ABSTENTION_ERROR_CODE,
)

logger = logging.getLogger(__name__)

# ============================================================
# Aggregation Constants
# ============================================================

# Maximum allowable aggregate risk score.
# Caps the combined output — prevents score inflation from signal volume.
MAX_AGGREGATE_SCORE: float = 1.0

# Per-unit penalty applied to aggregate score per unit of contradiction density.
# contradiction_density ∈ [0.0, 1.0]; penalty_factor in (0, 1].
# aggregate *= (1.0 - contradiction_density * CONTRADICTION_PENALTY_FACTOR)
# At D=1.0 (all signals conflict): aggregate *= (1 - FACTOR) = 0.5 × aggregate.
CONTRADICTION_PENALTY_FACTOR: float = 0.5

# Floor below which a contradiction-penalised score is NOT further reduced.
# Prevents the penalty from zeroing out genuine high-risk multi-signal inputs.
CONTRADICTION_FLOOR: float = 0.0

# Minimum number of signals required for aggregation.
MIN_SIGNALS: int = 1

# Maximum number of signals accepted by a single aggregation call.
# Prevents resource exhaustion from unbounded signal lists.
MAX_SIGNALS: int = 32

# Thresholds (mirror engine.py — kept in sync deliberately)
LOW_THRESHOLD:  float = 0.3
HIGH_THRESHOLD: float = 0.7


# ============================================================
# Input / Output Dataclasses
# ============================================================

@dataclass(frozen=True)
class ScoredSignal:
    """
    The fully-scored output for a single (text, DGICInput) pair.

    Fields:
        signal_index     : Position in the input list (0-indexed).
        text_label       : Optional caller-supplied label for this signal (audit only).
        risk_score       : Score from engine + DGIC modifiers (after ceilings/abstention).
        confidence_score : Confidence after DGIC scaling.
        risk_category    : LOW | MEDIUM | HIGH derived from risk_score.
        epistemic_state  : DGIC epistemic state for this signal.
        scoring_mode     : DGIC scoring mode applied.
        abstained        : True if UNKNOWN state forced abstention.
        epistemic_warning: True if AMBIGUOUS or UNKNOWN state.
        contradiction_flag: DGIC contradiction_flag value (preserved, not scored upon).
        evidence_hash    : DGIC evidence_hash (audit trail, unmodified).
    """
    signal_index:       int
    text_label:         Optional[str]
    risk_score:         float
    confidence_score:   float
    risk_category:      str
    epistemic_state:    EpistemicState
    scoring_mode:       str
    abstained:          bool
    epistemic_warning:  bool
    contradiction_flag: bool
    evidence_hash:      str


@dataclass(frozen=True)
class AggregatedSignal:
    """
    Final aggregated output across N scored signals.

    Fields:
        aggregate_risk_score     : Deterministic combination of non-abstained signals.
        aggregate_confidence     : Weighted mean confidence of non-abstained signals.
        aggregate_risk_category  : LOW | MEDIUM | HIGH from aggregate score.
        signal_count             : Total signals submitted.
        active_signal_count      : Signals that were not abstained.
        abstained_signal_count   : Signals that abstained (UNKNOWN epistemic state).
        contradiction_count      : Number of signals with contradiction_flag=True.
        contradiction_density    : contradiction_count / signal_count ∈ [0.0, 1.0].
        contradiction_penalty_applied: Factor by which score was penalised.
        epistemic_warning        : True if any signal emitted an epistemic_warning.
        any_abstained            : True if any signal abstained.
        all_abstained            : True if ALL signals abstained.
        scored_signals           : Ordered list of individual ScoredSignal results.
        safety_metadata          : Always {is_decision:False, authority:"NONE", actionable:False}.
        errors                   : None or structured error (e.g. all-abstain, no signals).
        aggregation_hash         : SHA-256 of the deterministic aggregation inputs (audit).
    """
    aggregate_risk_score:          float
    aggregate_confidence:          float
    aggregate_risk_category:       str
    signal_count:                  int
    active_signal_count:           int
    abstained_signal_count:        int
    contradiction_count:           int
    contradiction_density:         float
    contradiction_penalty_applied: float
    epistemic_warning:             bool
    any_abstained:                 bool
    all_abstained:                 bool
    scored_signals:                List[ScoredSignal]
    safety_metadata:               dict
    errors:                        Optional[dict]
    aggregation_hash:              str


class AggregationContractViolation(Exception):
    """Raised when the aggregator input fails structural validation."""
    def __init__(self, code: str, message: str):
        self.code    = code
        self.message = message
        super().__init__(f"{code}: {message}")


# ============================================================
# Frozen safety sidecar (re-asserted after every path)
# ============================================================

_SAFETY_METADATA = {
    "is_decision": False,
    "authority":   "NONE",
    "actionable":  False,
}

_ABSTAIN_ALL_ERROR = {
    "error_code": "ALL_SIGNALS_ABSTAINED",
    "message":    (
        "All submitted signals returned epistemic abstention (UNKNOWN state). "
        "No aggregate risk score can be produced."
    ),
}


# ============================================================
# Input validation
# ============================================================

def validate_aggregation_inputs(
    signals: List[Tuple[str, DGICInput]],
) -> None:
    """
    Validate the aggregation input list before any processing.
    Raises AggregationContractViolation on failure.

    Rules:
      - signals must be a non-empty list
      - len(signals) must not exceed MAX_SIGNALS
      - Each element must be (str, DGICInput)
      - Each DGICInput must pass validate_dgic_input()
    """
    if not isinstance(signals, list):
        raise AggregationContractViolation(
            "INVALID_SIGNALS_TYPE",
            f"signals must be a list, got {type(signals).__name__}"
        )
    if len(signals) < MIN_SIGNALS:
        raise AggregationContractViolation(
            "EMPTY_SIGNALS",
            "At least one signal is required"
        )
    if len(signals) > MAX_SIGNALS:
        raise AggregationContractViolation(
            "EXCESSIVE_SIGNALS",
            f"Maximum {MAX_SIGNALS} signals per aggregation call, got {len(signals)}"
        )

    for i, item in enumerate(signals):
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            raise AggregationContractViolation(
                "INVALID_SIGNAL_ELEMENT",
                f"signals[{i}] must be a (text: str, dgic: DGICInput) pair"
            )
        text, dgic = item
        if not isinstance(text, str):
            raise AggregationContractViolation(
                "INVALID_SIGNAL_TEXT",
                f"signals[{i}][0] (text) must be a str, got {type(text).__name__}"
            )
        try:
            validate_dgic_input(dgic)
        except DGICContractViolation as e:
            raise AggregationContractViolation(
                "INVALID_SIGNAL_DGIC",
                f"signals[{i}] DGIC input invalid: {e.code}: {e.message}"
            ) from e


# ============================================================
# Per-signal scoring
# ============================================================

def _score_single_signal(
    index: int,
    text: str,
    dgic: DGICInput,
    label: Optional[str] = None,
) -> ScoredSignal:
    """Score one (text, DGICInput) pair through the full engine + adapter pipeline."""
    base_result    = analyze_text(text)
    adapter_result = adapt_dgic(dgic)
    modified       = apply_dgic_modifiers(base_result, adapter_result)

    abstained = adapter_result.abstain

    return ScoredSignal(
        signal_index       = index,
        text_label         = label,
        risk_score         = round(modified.get("risk_score", 0.0), 4),
        confidence_score   = round(modified.get("confidence_score", 0.0), 4),
        risk_category      = modified.get("risk_category", "LOW"),
        epistemic_state    = adapter_result.epistemic_state,
        scoring_mode       = adapter_result.scoring_mode,
        abstained          = abstained,
        epistemic_warning  = adapter_result.epistemic_warning,
        contradiction_flag = dgic.payload.contradiction_flag,
        evidence_hash      = adapter_result.evidence_hash,
    )


# ============================================================
# Part A — Aggregation Algebra
# ============================================================

def _compute_aggregation_hash(signals: List[Tuple[str, DGICInput]]) -> str:
    """
    Stable SHA-256 fingerprint of the aggregation inputs.
    Enables downstream audit of what was aggregated.
    """
    fingerprint = [
        {
            "text":              text,
            "epistemic_state":   dgic.payload.epistemic_state.value,
            "entropy_score":     dgic.payload.entropy_score,
            "contradiction_flag":dgic.payload.contradiction_flag,
            "collapse_flag":     dgic.collapse_flag,
            "evidence_hash":     dgic.evidence_hash,
        }
        for text, dgic in signals
    ]
    serialised = json.dumps(fingerprint, sort_keys=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _weighted_mean(scores: List[float], weights: List[float]) -> float:
    """
    Weighted arithmetic mean. Returns 0.0 if all weights are zero.
    weights are confidence scores ∈ [0.0, 1.0].
    """
    total_weight = sum(weights)
    if total_weight == 0.0:
        # All active signals have zero confidence — fall back to simple mean.
        return sum(scores) / len(scores) if scores else 0.0
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


# ============================================================
# Part B — Contradiction Density Scaling
# ============================================================

def _apply_contradiction_penalty(
    raw_score: float,
    contradiction_density: float,
) -> Tuple[float, float]:
    """
    Apply contradiction density penalty to the raw aggregate score.

    Formula:
        penalty_factor = 1.0 - contradiction_density * CONTRADICTION_PENALTY_FACTOR
        penalised      = raw_score * penalty_factor

    Rationale:
        When signals conflict, the aggregate CANNOT silently inflate.
        A density of 1.0 (all signals contradictory) halves the score.
        The penalty is monotonically decreasing with density.
        It is deterministic and bounded — it cannot produce negative scores.

    Returns:
        (penalised_score, penalty_factor_applied)
    """
    penalty_factor = round(
        1.0 - contradiction_density * CONTRADICTION_PENALTY_FACTOR,
        6
    )
    penalty_factor = max(0.0, min(1.0, penalty_factor))  # bound in [0, 1]
    penalised      = max(CONTRADICTION_FLOOR, raw_score * penalty_factor)
    return round(penalised, 4), penalty_factor


# ============================================================
# Part C — Weighted Confidence Model
# ============================================================

def _aggregate_confidence(scored: List[ScoredSignal]) -> float:
    """
    Deterministic weighted confidence across active (non-abstained) signals.

    Method:
        Simple arithmetic mean of confidence scores.
        No probabilistic combination — no variance estimation.
        Result is purely a structural average.

    This is intentionally conservative: it does not boost composite
    confidence beyond what the individual signals support.
    """
    active_confs = [s.confidence_score for s in scored if not s.abstained]
    if not active_confs:
        return 0.0
    result = sum(active_confs) / len(active_confs)
    return round(result, 4)


def _score_to_category(score: float) -> str:
    """Mirror of engine.py threshold logic — kept in sync."""
    if score < LOW_THRESHOLD:
        return "LOW"
    elif score < HIGH_THRESHOLD:
        return "MEDIUM"
    else:
        return "HIGH"


# ============================================================
# Main aggregation entry point
# ============================================================

def aggregate_signals(
    signals:    List[Tuple[str, DGICInput]],
    labels:     Optional[List[Optional[str]]] = None,
) -> AggregatedSignal:
    """
    Deterministically aggregate N (text, DGICInput) signal pairs.

    Steps:
      1. Validate all inputs structurally.
      2. Score each signal independently through engine + DGIC adapter.
      3. Separate abstained signals from active ones.
      4. Compute contradiction density from contradiction_flag across ALL signals.
      5. Weighted mean of active risk scores (weight = confidence_score).
      6. Apply contradiction penalty to raw aggregate.
      7. Clamp to MAX_AGGREGATE_SCORE.
      8. Derive risk_category from clamped score.
      9. Compute aggregate confidence (arithmetic mean of active confidences).
      10. Re-assert safety_metadata invariants.

    If ALL signals abstained:
      Returns aggregate_risk_score=0.0, risk_category="LOW",
      errors.error_code="ALL_SIGNALS_ABSTAINED".
    """
    validate_aggregation_inputs(signals)

    agg_hash = _compute_aggregation_hash(signals)
    n        = len(signals)
    label_list = labels if (labels and len(labels) == n) else [None] * n

    logger.info(
        "Aggregation started",
        extra={
            "event_type":         "aggregation_start",
            "signal_count":       n,
            "aggregation_hash":   agg_hash,
        }
    )

    # ── Step 2: Score all signals ──────────────────────────────────────────
    scored: List[ScoredSignal] = []
    for i, (text, dgic) in enumerate(signals):
        sig = _score_single_signal(i, text, dgic, label=label_list[i])
        scored.append(sig)
        logger.info(
            "Signal scored",
            extra={
                "event_type":       "signal_scored",
                "index":            i,
                "epistemic_state":  sig.epistemic_state.value,
                "scoring_mode":     sig.scoring_mode,
                "risk_score":       sig.risk_score,
                "abstained":        sig.abstained,
            }
        )

    # ── Step 3: Partition ──────────────────────────────────────────────────
    active    = [s for s in scored if not s.abstained]
    abstained = [s for s in scored if s.abstained]

    # ── Step 4: Contradiction density (across ALL signals, not just active) ─
    contradiction_count   = sum(1 for s in scored if s.contradiction_flag)
    contradiction_density = round(contradiction_count / n, 6)

    # ── Step 5: Weighted mean of active risk scores ─────────────────────────
    if not active:
        # All signals abstained — emit structured abstention
        return AggregatedSignal(
            aggregate_risk_score           = 0.0,
            aggregate_confidence           = 0.0,
            aggregate_risk_category        = "LOW",
            signal_count                   = n,
            active_signal_count            = 0,
            abstained_signal_count         = len(abstained),
            contradiction_count            = contradiction_count,
            contradiction_density          = contradiction_density,
            contradiction_penalty_applied  = 1.0,
            epistemic_warning              = True,
            any_abstained                  = True,
            all_abstained                  = True,
            scored_signals                 = scored,
            safety_metadata                = dict(_SAFETY_METADATA),
            errors                         = dict(_ABSTAIN_ALL_ERROR),
            aggregation_hash               = agg_hash,
        )

    active_scores  = [s.risk_score        for s in active]
    active_weights = [s.confidence_score  for s in active]
    
    # Handle the edge case where the active list effectively evaluates to 0
    if not active_scores:
        raw_aggregate = 0.0
    else:
        raw_aggregate  = _weighted_mean(active_scores, active_weights)

    # ── Step 6: Contradiction penalty ─────────────────────────────────────
    penalised, penalty_factor = _apply_contradiction_penalty(
        raw_aggregate, contradiction_density
    )

    # ── Step 7: Clamp ──────────────────────────────────────────────────────
    clamped = round(min(MAX_AGGREGATE_SCORE, penalised), 2)

    # ── Step 8: Risk category ──────────────────────────────────────────────
    agg_category = _score_to_category(clamped)

    # ── Step 9: Aggregate confidence ──────────────────────────────────────
    agg_confidence = round(_aggregate_confidence(scored), 2)

    # ── Step 10: Flags ─────────────────────────────────────────────────────
    any_warn    = any(s.epistemic_warning for s in scored)
    any_abstain = len(abstained) > 0

    logger.info(
        "Aggregation complete",
        extra={
            "event_type":              "aggregation_complete",
            "raw_aggregate":           raw_aggregate,
            "penalised":               penalised,
            "clamped":                 clamped,
            "contradiction_density":   contradiction_density,
            "penalty_factor":          penalty_factor,
            "aggregate_risk_category": agg_category,
            "active_signals":          len(active),
            "abstained_signals":       len(abstained),
        }
    )

    return AggregatedSignal(
        aggregate_risk_score           = clamped,
        aggregate_confidence           = agg_confidence,
        aggregate_risk_category        = agg_category,
        signal_count                   = n,
        active_signal_count            = len(active),
        abstained_signal_count         = len(abstained),
        contradiction_count            = contradiction_count,
        contradiction_density          = contradiction_density,
        contradiction_penalty_applied  = round(penalty_factor, 6),
        epistemic_warning              = any_warn,
        any_abstained                  = any_abstain,
        all_abstained                  = False,
        scored_signals                 = scored,
        safety_metadata                = dict(_SAFETY_METADATA),
        errors                         = None,
        aggregation_hash               = agg_hash,
    )

# ==================================================
# Source: app/insightbridge_adapter.py
# ==================================================

from typing import Dict, Any
import hashlib
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def map_to_insightbridge_contract(internal_result: Any, lineage_hash: str) -> Dict[str, Any]:
    """
    Deterministically transforms the internal enforcement payload into the strict
    InsightBridge v4 contract schema. 
    Guarantees 'decision' is null and 'authority' is 'NONE'.
    Guarantees mapping of ambiguous and abstained states.
    """
    
    # Handle both dict and object formats (like AggregatedSignal)
    if hasattr(internal_result, "aggregate_risk_score"):
        risk_score = getattr(internal_result, "aggregate_risk_score", 0.0)
        confidence = getattr(internal_result, "aggregate_confidence", 0.0)
        abstain_flag = getattr(internal_result, "all_abstained", False)
        contradiction_flag = getattr(internal_result, "contradiction_count", 0) > 0
    else:
        # Dictionary format
        risk_score = internal_result.get("risk_score", 0.0)
        confidence = internal_result.get("confidence_score", 0.0)
        
        # Metadata fields
        dgic_meta = internal_result.get("dgic_metadata", {})
        
        # Determine flags
        abstain_flag = False
        if "errors" in internal_result and internal_result["errors"].get("error_code") == "EPISTEMIC_ABSTENTION":
            abstain_flag = True
            
        contradiction_flag = dgic_meta.get("epistemic_warning", False) and dgic_meta.get("epistemic_state") == "AMBIGUOUS"
        
        # If the aggregator was used, contradiction_flag might also be mapped from "contradiction_penalty"
        if "aggregation_metadata" in internal_result:
            agg_meta = internal_result["aggregation_metadata"]
            if agg_meta.get("contradictions", 0) > 0:
                contradiction_flag = True

    if abstain_flag:
        risk_score = 0.0  # Force to 0.0 if abstaining
                
    # We must construct a deterministic signal ID. 
    # Use a hash of the original lineage hash and the risk result
    raw_for_id = f"{lineage_hash}|{risk_score}|{confidence}|{abstain_flag}|{contradiction_flag}"
    signal_id = hashlib.sha256(raw_for_id.encode("utf-8")).hexdigest()
    
    # The absolute invariant hardcodes
    decision = None
    authority = "NONE"
    
    signal_timestamp = datetime.now(timezone.utc).isoformat()
    
    output = {
        "signal_id": signal_id,
        "source_type": "text_risk_scoring_service",
        "signal_timestamp": signal_timestamp,
        "lineage_reference": lineage_hash,
        "aggregated_risk_score": float(risk_score),
        "epistemic_confidence": float(confidence),
        "contradiction_flag": contradiction_flag,
        "abstention_flag": abstain_flag,
        "decision": decision,
        "authority": authority
    }
    
    logger.debug("Mapped to InsightBridge contract", extra={"signal_id": signal_id})
    return output

# ==================================================
# Source: app/insightbridge_telemetry.py
# ==================================================

"""
InsightBridge Telemetry Emitter
================================
Emits structured telemetry events for each aggregated signal, making them
observable and auditable by InsightBridge telemetry pipelines and bucket logging.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - Telemetry events are informational only — they MUST NOT trigger actions.
  - All fields are deterministically derived — no ML, no probabilistic inference.
"""


import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

from app.layer3_dgic import DGICEnforcementEnvelope

logger = logging.getLogger(__name__)


# ============================================================
# Telemetry Event Dataclass
# ============================================================

@dataclass(frozen=True)
class InsightBridgeTelemetryEvent:
    """
    A structured telemetry event emitted for each aggregated signal.

    Fields:
        signal_id           : Deterministic hash of aggregation inputs.
        signal_source       : Always "multi_signal_aggregator".
        confidence          : Epistemic confidence from DGIC envelope.
        timestamp           : UTC ISO-8601 timestamp of emission.
        lineage_reference   : Signal lineage from DGIC envelope (full provenance).
        risk_score          : Aggregate risk score.
        signal_count        : Number of input signals aggregated.
        collapse_state      : STABLE | DEGRADED | COLLAPSED from DGIC envelope.
        execution_id        : Global unique execution ID trace.
    """
    execution_id: str
    signal_id: str
    signal_source: str
    confidence: float
    timestamp: str
    lineage_reference: str
    risk_score: float
    signal_count: int
    collapse_state: str


@dataclass(frozen=True)
class EmittedEnforcementTelemetry:
    """
    Sovereign-compliant, guaranteed telemetry for Core enforcement outcomes.
    Prevents silent execution by broadcasting the decision trace.
    """
    execution_id: str
    enforcement_decision: str
    risk_score: float
    confidence: float
    trace_hash: str


# ============================================================
# Signal ID Computation
# ============================================================

def _compute_telemetry_signal_id(envelope: DGICEnforcementEnvelope) -> str:
    """
    Compute a deterministic signal ID for the telemetry event.
    Derived from truth_boundary_reference + signal_lineage.
    """
    raw = f"{envelope.truth_boundary_reference}|{envelope.signal_lineage}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Telemetry Emission
# ============================================================

def emit_telemetry_event(execution_id: str, envelope: DGICEnforcementEnvelope) -> InsightBridgeTelemetryEvent:
    """
    Build and emit a structured telemetry event from a DGIC enforcement envelope.

    The event is emitted via structured JSON logging, making it consumable
    by InsightBridge telemetry pipelines and bucket logging infrastructure.

    Returns the event for programmatic use (e.g. API response enrichment).
    """
    signal_id = _compute_telemetry_signal_id(envelope)
    timestamp = datetime.now(timezone.utc).isoformat()

    event = InsightBridgeTelemetryEvent(
        execution_id=execution_id,
        signal_id=signal_id,
        signal_source="multi_signal_aggregator",
        confidence=envelope.epistemic_confidence,
        timestamp=timestamp,
        lineage_reference=envelope.signal_lineage,
        risk_score=envelope.aggregate_risk_score,
        signal_count=envelope.signal_count,
        collapse_state=envelope.collapse_state,
    )

    # Emit via structured logging for InsightBridge / bucket logging consumption
    logger.info(
        "InsightBridge telemetry event emitted",
        extra={
            "event_type": "insightbridge_telemetry",
            "telemetry": asdict(event),
        },
    )

    return event


def emit_telemetry_dict(execution_id: str, envelope: DGICEnforcementEnvelope) -> dict:
    """
    Convenience wrapper: emit telemetry and return as a plain dict
    for JSON serialisation in API responses.
    """
    event = emit_telemetry_event(execution_id, envelope)
    return asdict(event)


def emit_enforcement_telemetry(
    execution_id: str,
    enforcement_decision: str,
    risk_score: float,
    confidence: float,
    trace_hash: str,
) -> EmittedEnforcementTelemetry:
    """
    Phase 5: Emit the final enforcement decision telemetry to InsightBridge.
    This guarantees NO SILENT EXECUTION. Every terminal decision is broadcast.
    """
    telemetry = EmittedEnforcementTelemetry(
        execution_id=execution_id,
        enforcement_decision=enforcement_decision,
        risk_score=risk_score,
        confidence=confidence,
        trace_hash=trace_hash,
    )

    logger.info(
        "InsightBridge enforcement decision telemetry emitted",
        extra={
            "event_type": "insightbridge_enforcement_emission",
            "telemetry": asdict(telemetry),
        },
    )

    # LIVE EXTERNAL INTEGRATION: Broadcast to InsightBridge Registry
    import requests
    import os
    import uuid

    insightbridge_url = os.environ.get("INSIGHTBRIDGE_URL", "https://bhiv-6.onrender.com")
    endpoint = f"{insightbridge_url}/api/v1/flow/events"
    
    # Generate a deterministic W3C traceparent for the execution_id (UUID -> hex string)
    # W3C Trace Context Format: 00-{trace-id (32 chars)}-{span-id (16 chars)}-01
    trace_id = execution_id.replace('-', '')
    if len(trace_id) < 32:
        trace_id = trace_id.ljust(32, '0')
    span_id = uuid.uuid4().hex[:16]
    traceparent = f"00-{trace_id}-{span_id}-01"

    headers = {
        "X-API-Key": "vijay_insightflow_10c5cbe7831071d120a52db97695fdb6",
        "Content-Type": "application/json",
        "traceparent": traceparent
    }
    
    payload = asdict(telemetry)
    payload["registry_id"] = "BHIV-DS-GOVERNANCE-CONTRADICTION-AUDITS-001"
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            logger.info(f"InsightBridge POST Success | execution_id={execution_id} | response={response.text}")
        else:
            logger.warning(f"InsightBridge POST Failed | status={response.status_code} | response={response.text}")
    except Exception as e:
        logger.error(f"InsightBridge Connection Error: {str(e)}")

    return telemetry


# ==============================================================================
# InsightBridge Signal Registry — Shared Telemetry Provider (Phase 3)
# ==============================================================================

"""
Stateful signal registry that accumulates context signals during an execution
pipeline and exposes them via get_context_signals(execution_id).

This is the canonical entry point for any layer that needs to query what
signals were observed during a given execution.

Thread-safety: All operations on the registry are guarded by a threading lock.
Lifecycle: Signals are accumulated per execution_id. Call clear_signals() to
           purge after the execution pipeline completes.
"""

import threading
from collections import defaultdict
from typing import Callable

# Thread-safe signal store: execution_id -> list of signal dicts
_signal_store: dict[str, list[dict]] = defaultdict(list)
_signal_lock = threading.Lock()

# Registered external signal source providers
# Each provider is a callable: (execution_id: str) -> List[Dict[str, Any]]
_signal_source_registry: dict[str, Callable] = {}
_registry_lock = threading.Lock()


def register_signal_source(source_name: str, provider: Callable) -> None:
    """
    Register an external signal source provider.

    The provider must be a callable that accepts (execution_id: str)
    and returns a List[Dict[str, Any]], where each dict has at minimum:
        signal_id, signal_type, value, source

    Example:
        register_signal_source("MARINE_INTELLIGENCE", marine_signal_provider)
    """
    with _registry_lock:
        _signal_source_registry[source_name] = provider
        logger.info(
            f"InsightBridge: Signal source registered: {source_name}",
            extra={
                "event_type": "insightbridge_source_registered",
                "source_name": source_name,
            },
        )


def unregister_signal_source(source_name: str) -> None:
    """Remove a registered signal source provider."""
    with _registry_lock:
        _signal_source_registry.pop(source_name, None)
        logger.info(
            f"InsightBridge: Signal source unregistered: {source_name}",
            extra={
                "event_type": "insightbridge_source_unregistered",
                "source_name": source_name,
            },
        )


def record_signal(
    execution_id: str,
    signal_id: str,
    signal_type: str,
    value: float,
    source: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Record a context signal into the execution-scoped signal store.

    This is called during the enforcement pipeline as signals are observed.
    Downstream consumers call get_context_signals(execution_id) to retrieve them.

    Returns the recorded signal dict.
    """
    signal = {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "value": max(0.0, min(1.0, value)),  # Clamp to [0.0, 1.0]
        "source": source,
    }
    if metadata:
        signal["metadata"] = metadata

    with _signal_lock:
        _signal_store[execution_id].append(signal)

    logger.debug(
        f"InsightBridge: Signal recorded for {execution_id}",
        extra={
            "event_type": "insightbridge_signal_recorded",
            "execution_id": execution_id,
            "signal_id": signal_id,
            "signal_type": signal_type,
            "source": source,
            "value": signal["value"],
        },
    )
    return signal


def get_context_signals(execution_id: str) -> list[dict]:
    """
    Shared telemetry provider — the canonical interface for querying
    context signals observed during a given execution pipeline.

    Pipeline:
      1. Retrieve all locally recorded signals for this execution_id
      2. Query all registered external signal source providers
      3. Merge and return the complete signal list

    Fail-open: If any external provider fails, its signals are skipped
    (logged as warning). The pipeline NEVER halts on a provider failure.

    Returns:
        List of signal dicts, each containing at minimum:
        signal_id, signal_type, value, source
    """
    # Step 1: Local signals
    with _signal_lock:
        local_signals = list(_signal_store.get(execution_id, []))

    # Step 2: External providers
    external_signals = []
    with _registry_lock:
        providers = dict(_signal_source_registry)

    for source_name, provider in providers.items():
        try:
            provider_signals = provider(execution_id)
            if isinstance(provider_signals, list):
                external_signals.extend(provider_signals)
                logger.debug(
                    f"InsightBridge: {source_name} provided {len(provider_signals)} signals",
                    extra={
                        "event_type": "insightbridge_provider_response",
                        "execution_id": execution_id,
                        "source_name": source_name,
                        "signal_count": len(provider_signals),
                    },
                )
        except Exception as e:
            logger.warning(
                f"InsightBridge: Signal provider {source_name} failed (fail-open)",
                extra={
                    "event_type": "insightbridge_provider_failure",
                    "execution_id": execution_id,
                    "source_name": source_name,
                    "error": str(e),
                },
            )
            # Fail-open: skip this provider, continue with others

    # Step 3: Merge
    all_signals = local_signals + external_signals

    logger.info(
        f"InsightBridge: get_context_signals({execution_id}) -> {len(all_signals)} signals",
        extra={
            "event_type": "insightbridge_get_context_signals",
            "execution_id": execution_id,
            "local_count": len(local_signals),
            "external_count": len(external_signals),
            "total_count": len(all_signals),
        },
    )

    return all_signals


def clear_signals(execution_id: str) -> int:
    """
    Purge all recorded signals for a given execution_id.
    Call this after the execution pipeline completes to prevent memory leaks.

    Returns the number of signals purged.
    """
    with _signal_lock:
        signals = _signal_store.pop(execution_id, [])
    count = len(signals)
    if count > 0:
        logger.debug(
            f"InsightBridge: Cleared {count} signals for {execution_id}",
            extra={
                "event_type": "insightbridge_signals_cleared",
                "execution_id": execution_id,
                "purged_count": count,
            },
        )
    return count


def get_registered_sources() -> list[str]:
    """Return the names of all registered signal source providers."""
    with _registry_lock:
        return list(_signal_source_registry.keys())
