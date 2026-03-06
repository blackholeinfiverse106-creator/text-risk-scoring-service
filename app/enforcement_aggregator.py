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

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.engine import analyze_text
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
        contradiction_flag = dgic.contradiction_flag,
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
            "epistemic_state":   dgic.epistemic_state.value,
            "entropy_score":     dgic.entropy_score,
            "contradiction_flag":dgic.contradiction_flag,
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
