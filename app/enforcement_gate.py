"""
Enforcement Gate — Deterministic Decision Engine
==================================================
The single deterministic decision gate through which ALL proposed actions
pass before execution in the BHIV ecosystem.

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
    EvaluateActionResponse,
    EnforcementDecision,
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
from app.enforcement_ledger import record_decision
from app.engine import analyze_text
from app.insightbridge_rules import calculate_weighted_signal
from app.marine_rules import calculate_marine_signal
from app.aiaic_rules import calculate_aiaic_signal
from app.c4s_rules import calculate_c4s_signal
from app.bucket_ledger import write_bucket_entry
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
        "action_id": request.action_id,
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
# Core Enforcement Evaluation
# ============================================================

def evaluate_action(request: EvaluateActionRequest) -> EvaluateActionResponse:
    """
    The deterministic enforcement gate.

    Pipeline:
      1. Compute trace hash (for replay verification)
      2. Validate DGIC envelope
      3. Map epistemic state to scoring modifiers
      4. Analyze proposed action text for risk
      5. Apply DGIC epistemic modifiers
      6. Aggregate context signals
      7. Compute final risk = max(text_risk, context_risk)
      8. Make deterministic decision (ALLOW / DENY / ABSTAIN)
      9. Log decision for replay ledger

    Returns: EvaluateActionResponse — fully structured, no unstructured output.
    """
    correlation_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    from datetime import datetime, timezone
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Enforcement evaluation started",
        extra={
            "correlation_id": correlation_id,
            "event_type": "enforcement_evaluate_start",
            "action_id": request.action_id,
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
            f"DGIC snapshot ingestion failed | action_id={request.action_id}",
            extra={
                "correlation_id": correlation_id,
                "event_type": "enforcement_snapshot_error",
                "details": str(e),
            },
        )
        return EvaluateActionResponse(
            risk_score=0.0,
            enforcement_decision=EnforcementDecision.ABSTAIN,
            confidence=0.0,
            failure_reason=f"DGIC snapshot rejected: {str(e)}",
            trace_hash=trace_hash,
        )

    # Step 3: Map epistemic state to scoring modifiers
    adapter_result = adapt_dgic(snapshot.dgic_input)

    # Step 4: Check for epistemic ABSTAIN (UNKNOWN state)
    if adapter_result.abstain:
        logger.info(
            f"Epistemic abstention | action_id={request.action_id}",
            extra={
                "correlation_id": correlation_id,
                "event_type": "enforcement_abstain",
                "epistemic_state": adapter_result.epistemic_state.value,
            },
        )
        return EvaluateActionResponse(
            risk_score=0.0,
            enforcement_decision=EnforcementDecision.ABSTAIN,
            confidence=0.0,
            failure_reason="Epistemic abstention: no grounded evidence available (DGIC UNKNOWN state). Caller must handle conservatively.",
            trace_hash=trace_hash,
        )

    # Step 5: Analyze proposed action text for risk
    base_result = analyze_text(request.proposed_action, correlation_id=correlation_id)

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
    decision: EnforcementDecision
    failure_reason: Optional[str] = None

    if final_risk >= DENY_RISK_THRESHOLD:
        decision = EnforcementDecision.DENY
        failure_reason = f"Risk score {final_risk} exceeds enforcement threshold {DENY_RISK_THRESHOLD}"
    elif snapshot.entropy_boundary == EntropyBoundary.CRITICAL:
        decision = EnforcementDecision.DENY
        failure_reason = (
            f"CRITICAL entropy boundary exceeded. "
            "Action blocked as fail-safe."
        )
    elif (
        adapter_result.epistemic_state.value == "AMBIGUOUS"
        and final_risk >= AMBIGUOUS_DENY_THRESHOLD
    ):
        decision = EnforcementDecision.DENY
        failure_reason = (
            f"Ambiguous epistemic state with risk {final_risk} >= "
            f"conservative threshold {AMBIGUOUS_DENY_THRESHOLD}. "
            "Cannot allow action under epistemic uncertainty."
        )
    else:
        decision = EnforcementDecision.ALLOW

    processing_time = time.time() - start_time

    # Construct the response
    response = EvaluateActionResponse(
        risk_score=final_risk,
        enforcement_decision=decision,
        confidence=confidence,
        failure_reason=failure_reason,
        trace_hash=trace_hash,
    )

    # Step 10: Verify snapshot immutability
    verify_snapshot_integrity(snapshot)

    # Step 11: Record decision to replay ledger
    record_decision(
        correlation_id=correlation_id,
        timestamp_utc=timestamp_utc,
        request=request,
        snapshot=snapshot,
        response=response,
    )

    # Step 12: Write to persistent bucket ledger
    write_bucket_entry(
        action_id=request.action_id,
        request_payload=request.model_dump(mode="json"),
        dgic_snapshot=snapshot_to_dict(snapshot),
        decision=response.enforcement_decision.value,
        risk_score=final_risk,
        confidence=confidence,
        failure_reason=failure_reason,
        trace_hash=trace_hash,
    )

    # Step 13: Log decision
    logger.info(
        f"Enforcement decision: {decision.value}",
        extra={
            "correlation_id": correlation_id,
            "event_type": "enforcement_decision",
            "action_id": request.action_id,
            "actor": request.actor,
            "source_system": request.source_system.value,
            "risk_score": final_risk,
            "confidence": confidence,
            "enforcement_decision": decision.value,
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
