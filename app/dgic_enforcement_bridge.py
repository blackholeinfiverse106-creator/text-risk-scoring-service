"""
DGIC Enforcement Bridge
========================
Wraps an AggregatedUnifiedSignal into a DGIC-compliant epistemic envelope
for downstream consumption by the Deterministic Graph Intelligence Core.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - safety_metadata.is_decision remains False in all outputs.
  - safety_metadata.authority remains "NONE" in all outputs.
  - collapse_state is purely informational — it MUST NOT be used to derive authority.
  - All transformations are purely structural — no ML, no probabilistic inference.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.signal_aggregator import AggregatedUnifiedSignal, ScoredUnifiedSignal

logger = logging.getLogger(__name__)


# ============================================================
# Collapse State Enum (Deterministic)
# ============================================================

class CollapseState:
    """
    Deterministic collapse states derived from aggregation flags.

    STABLE    — No epistemic warnings, no abstentions. Full signal fidelity.
    DEGRADED  — At least one epistemic warning or partial abstention. Signal is usable but weakened.
    COLLAPSED — All signals abstained. No usable risk signal was produced.
    """
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    COLLAPSED = "COLLAPSED"


# Frozen safety metadata — always identical, never derived from DGIC.
_SAFETY_METADATA = {
    "is_decision": False,
    "authority": "NONE",
    "actionable": False,
}


# ============================================================
# Output Dataclass
# ============================================================

@dataclass(frozen=True)
class DGICEnforcementEnvelope:
    """
    DGIC-compliant epistemic envelope wrapping an aggregated signal.

    Fields:
        epistemic_confidence       : Deterministic composite confidence from aggregation.
        signal_lineage             : SHA-256 provenance chain of aggregation inputs.
        collapse_state             : STABLE | DEGRADED | COLLAPSED — informational only.
        truth_boundary_reference   : Immutable fingerprint of the aggregation inputs.
        aggregate_risk_score       : Clamped [0.0, 1.0] risk score.
        aggregate_risk_category    : LOW | MEDIUM | HIGH.
        signal_count               : Total number of input signals.
        active_signal_count        : Signals that were not abstained.
        contradiction_density      : Fraction of signals with contradiction_flag=True.
        safety_metadata            : Always {is_decision: False, authority: "NONE", actionable: False}.
        errors                     : None or structured error (e.g. all-abstain).
    """
    epistemic_confidence: float
    signal_lineage: str
    collapse_state: str
    truth_boundary_reference: str
    aggregate_risk_score: float
    aggregate_risk_category: str
    signal_count: int
    active_signal_count: int
    contradiction_density: float
    safety_metadata: dict
    errors: Optional[dict]


# ============================================================
# Collapse State Derivation (Deterministic)
# ============================================================

def _derive_collapse_state(agg: AggregatedUnifiedSignal) -> str:
    """
    Deterministically derive the collapse state from aggregation flags.

    Rules (evaluated in order):
      1. all_abstained=True  → COLLAPSED
      2. epistemic_warning=True OR any_abstained=True → DEGRADED
      3. Otherwise → STABLE
    """
    if agg.all_abstained:
        return CollapseState.COLLAPSED
    if agg.epistemic_warning or agg.any_abstained:
        return CollapseState.DEGRADED
    return CollapseState.STABLE


# ============================================================
# Lineage Computation
# ============================================================

def _compute_signal_lineage(agg: AggregatedUnifiedSignal) -> str:
    """
    Compute a deterministic SHA-256 lineage hash from the aggregation hash
    and per-signal evidence hashes.

    This provides full provenance: the lineage uniquely identifies
    which signals were combined and what evidence chain backs each one.
    """
    evidence_hashes = [s.evidence_hash for s in agg.scored_signals]
    lineage_input = {
        "aggregation_hash": agg.aggregation_hash,
        "evidence_chain": evidence_hashes,
    }
    serialised = json.dumps(lineage_input, sort_keys=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ============================================================
# Main Bridge Function
# ============================================================

def wrap_in_dgic_envelope(agg: AggregatedUnifiedSignal) -> DGICEnforcementEnvelope:
    """
    Wrap an AggregatedUnifiedSignal into a DGIC-compliant epistemic envelope.

    This is a pure structural transformation — no scoring, no mutation,
    no authority derivation, no probabilistic inference.
    """
    collapse_state = _derive_collapse_state(agg)
    signal_lineage = _compute_signal_lineage(agg)

    envelope = DGICEnforcementEnvelope(
        epistemic_confidence=agg.aggregate_confidence,
        signal_lineage=signal_lineage,
        collapse_state=collapse_state,
        truth_boundary_reference=agg.aggregation_hash,
        aggregate_risk_score=agg.aggregate_risk_score,
        aggregate_risk_category=agg.aggregate_risk_category,
        signal_count=agg.signal_count,
        active_signal_count=agg.active_signal_count,
        contradiction_density=agg.contradiction_density,
        safety_metadata=dict(_SAFETY_METADATA),
        errors=agg.errors,
    )

    logger.info(
        "DGIC enforcement envelope created",
        extra={
            "event_type": "dgic_envelope_created",
            "collapse_state": collapse_state,
            "epistemic_confidence": envelope.epistemic_confidence,
            "signal_lineage": signal_lineage[:16] + "...",
            "truth_boundary_reference": envelope.truth_boundary_reference[:16] + "...",
            "aggregate_risk_score": envelope.aggregate_risk_score,
        },
    )

    return envelope
