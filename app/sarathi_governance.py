"""
Sarathi Governance Engine — Layer 1 Decision Engine
==================================================
The single deterministic governance gate through which ALL proposed actions
pass before being sent to the execution gate in the BHIV ecosystem.

Invariants (IMMUTABLE):
  - All decisions are deterministic: same inputs → same output, always.
  - No probabilistic outputs. No mutation of upstream epistemic states.
  - DGIC epistemic state is consumed read-only.
  - Trace hash enables byte-identical replay verification.
  - UNKNOWN epistemic state → ABSTAIN (fail-safe).
  - AMBIGUOUS + elevated risk → DENY (conservative).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional

from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
    SourceSystem,
)
from app.dgic_adapter import (
    adapt_dgic,
    apply_dgic_modifiers,
)
from app.dgic_snapshot_consumer import (
    ingest_dgic_snapshot,
    verify_snapshot_integrity,
    DGICSnapshotError,
    EntropyBoundary,
)
from app.engine import analyze_text
from app.insightbridge_rules import calculate_weighted_signal
from app.marine_rules import calculate_marine_signal
from app.aiaic_rules import calculate_aiaic_signal
from app.c4s_rules import calculate_c4s_signal
from app.dgic_snapshot_consumer import snapshot_to_dict

logger = logging.getLogger(__name__)


# ============================================================
# Constants — Enforcement Thresholds
# ============================================================

# Risk score at or above this threshold → DENY
DENY_RISK_THRESHOLD = 0.7

# AMBIGUOUS epistemic state + risk at or above this → DENY
AMBIGUOUS_DENY_THRESHOLD = 0.3


# ============================================================
# Trace Hash Computation
# ============================================================

def compute_trace_hash(request: EvaluateActionRequest) -> str:
    """
    Compute a deterministic SHA-256 trace hash from all input fields.
    Guarantees: same inputs → same hash. Enables replay verification.
    """
    # Build a canonical, sorted representation of all inputs
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
# Context Signal Aggregation
# ============================================================

def aggregate_context_signals(request: EvaluateActionRequest) -> float:
    """
    Deterministic weighted aggregation of context signals.
    Returns 0.0 if no signals provided.
    
    InsightBridge signals are mathematically weighted by severity type.
    Other sources currently default to 1.0 multiplier (raw value).
    
    Uses max-of-weighted-signals (fail-high) strategy.
    """
    if not request.context_signals:
        return 0.0

    weighted_values = []
    for signal in request.context_signals:
        source_upper = signal.source.upper()
        if source_upper == SourceSystem.INSIGHTBRIDGE.value:
            weighted_values.append(calculate_weighted_signal(signal))
        elif source_upper == SourceSystem.MARINE_INTELLIGENCE.value:
            weighted_values.append(calculate_marine_signal(signal))
        elif source_upper == SourceSystem.AIAIC.value:
            weighted_values.append(calculate_aiaic_signal(signal))
        elif source_upper == SourceSystem.C4S.value:
            weighted_values.append(calculate_c4s_signal(signal))
        else:
            # Other signals maintain 1.0 multiplier (raw value)
            weighted_values.append(signal.value)

    # Fail-high: take the maximum computed weighted signal
    return max(weighted_values)


# ============================================================
# Sarathi Governance Evaluation
# ============================================================

def evaluate_action(request: EvaluateActionRequest) -> SarathiEvaluateResponse:
    """
    The deterministic governance gate.

    Pipeline:
      1. Compute trace hash (for replay verification)
      2. Validate DGIC envelope
      3. Map epistemic state to scoring modifiers
      4. Analyze proposed action text for risk
      5. Apply DGIC epistemic modifiers
      6. Aggregate context signals
      7. Compute final risk = max(text_risk, context_risk)
      8. Make deterministic decision (ALLOW / DENY / ABSTAIN)

    Returns: SarathiEvaluateResponse — fully structured, no unstructured output.
    """
    execution_id = request.execution_id
    start_time = time.time()
    from datetime import datetime, timezone
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Sarathi governance evaluation started",
        extra={
            "event_type": "sarathi_evaluate_start",
            "execution_id": execution_id,
            "actor": request.actor,
            "source_system": request.source_system.value,
        },
    )

    # Step 1: Trace hash (computed FIRST — before any processing)
    trace_hash = compute_trace_hash(request)

    # Step 2: Ingest and freeze DGIC snapshot
    try:
        snapshot = ingest_dgic_snapshot(
            epistemic_state=request.dgic_epistemic_state.epistemic_state,
            entropy_score=request.dgic_epistemic_state.entropy_score,
            contradiction_flag=request.dgic_epistemic_state.contradiction_flag,
            lineage_hash=request.dgic_epistemic_state.lineage_hash,
            envelope_hash=request.dgic_epistemic_state.envelope_hash,
        )
    except DGICSnapshotError as e:
        logger.warning(
            f"DGIC snapshot ingestion failed | execution_id={execution_id}",
            extra={
                "execution_id": execution_id,
                "event_type": "sarathi_snapshot_error",
                "details": str(e),
            },
        )
        return SarathiEvaluateResponse(
            execution_id=execution_id,
            risk_score=0.0,
            sarathi_decision=SarathiDecision.ABSTAIN,
            confidence=0.0,
            failure_reason=f"DGIC snapshot rejected: {str(e)}",
            trace_hash=trace_hash,
        )

    # Step 3: Map epistemic state to scoring modifiers
    adapter_result = adapt_dgic(snapshot.dgic_input)

    # Step 4: Check for epistemic ABSTAIN (UNKNOWN state)
    if adapter_result.abstain:
        logger.info(
            f"Epistemic abstention | execution_id={execution_id}",
            extra={
                "execution_id": execution_id,
                "event_type": "sarathi_abstain",
                "epistemic_state": adapter_result.epistemic_state.value,
            },
        )
        return SarathiEvaluateResponse(
            execution_id=execution_id,
            risk_score=0.0,
            sarathi_decision=SarathiDecision.ABSTAIN,
            confidence=0.0,
            failure_reason="Epistemic abstention: no grounded evidence available (DGIC UNKNOWN state). Caller must handle conservatively.",
            trace_hash=trace_hash,
        )

    # Step 5: Analyze proposed action text for risk
    base_result = analyze_text(request.proposed_action, execution_id=execution_id)

    # Step 6: Apply DGIC epistemic modifiers
    modified_result = apply_dgic_modifiers(base_result, adapter_result=adapter_result)
    text_risk = modified_result["risk_score"]
    confidence = modified_result["confidence_score"]

    # Step 7: Aggregate context signals
    context_risk = aggregate_context_signals(request)

    # Step 8: Final risk = max(text_risk, context_risk) — fail-high
    final_risk = round(max(text_risk, context_risk), 2)

    # Clamp to [0.0, 1.0]
    final_risk = max(0.0, min(1.0, final_risk))

    # Step 9: Deterministic decision
    decision: SarathiDecision
    failure_reason: Optional[str] = None

    if final_risk >= DENY_RISK_THRESHOLD:
        decision = SarathiDecision.DENY
        failure_reason = f"Risk score {final_risk} exceeds governance threshold {DENY_RISK_THRESHOLD}"
    elif snapshot.entropy_boundary == EntropyBoundary.CRITICAL:
        decision = SarathiDecision.DENY
        failure_reason = (
            f"CRITICAL entropy boundary exceeded. "
            "Action denied as fail-safe."
        )
    elif (
        adapter_result.epistemic_state.value == "AMBIGUOUS"
        and final_risk >= AMBIGUOUS_DENY_THRESHOLD
    ):
        decision = SarathiDecision.DENY
        failure_reason = (
            f"Ambiguous epistemic state with risk {final_risk} >= "
            f"conservative threshold {AMBIGUOUS_DENY_THRESHOLD}. "
            "Cannot allow action under epistemic uncertainty."
        )
    else:
        decision = SarathiDecision.ALLOW

    processing_time = time.time() - start_time

    # Construct the response
    response = SarathiEvaluateResponse(
        execution_id=execution_id,
        risk_score=final_risk,
        sarathi_decision=decision,
        confidence=confidence,
        failure_reason=failure_reason,
        trace_hash=trace_hash,
    )

    # Step 10: Verify snapshot immutability
    verify_snapshot_integrity(snapshot)

    # Step 11: Log decision
    logger.info(
        f"Sarathi decision: {decision.value}",
        extra={
            "execution_id": execution_id,
            "event_type": "sarathi_decision",
            "actor": request.actor,
            "source_system": request.source_system.value,
            "risk_score": final_risk,
            "confidence": confidence,
            "sarathi_decision": decision.value,
            "failure_reason": failure_reason,
            "trace_hash": trace_hash,
            "epistemic_state": adapter_result.epistemic_state.value,
            "entropy_boundary": snapshot.entropy_boundary.value,
            "context_signal_count": len(request.context_signals),
            "snapshot_id": snapshot.snapshot_id,
            "processing_time_ms": round(processing_time * 1000, 2),
        },
    )

    return response
