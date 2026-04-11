from __future__ import annotations

import logging
import time
from typing import Dict, Any, Optional
import hashlib
import json

from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
)
from app.layer3_dgic import (
    EntropyBoundary,
    DGICSnapshot,
    DGICAdapterResult,
    verify_snapshot_integrity
)
from app.layer0_intelligence import IntelligencePayload

logger = logging.getLogger(__name__)

DENY_RISK_THRESHOLD = 0.7
AMBIGUOUS_DENY_THRESHOLD = 0.3

def compute_trace_hash(request: EvaluateActionRequest) -> str:
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

def evaluate_action(
    request: EvaluateActionRequest,
    intelligence: IntelligencePayload,
    snapshot: DGICSnapshot,
    adapter_result: DGICAdapterResult,
    trace_hash: str
) -> SarathiEvaluateResponse:
    start_time = time.time()
    execution_id = request.execution_id

    logger.info(
        "Sarathi governance evaluation started",
        extra={
            "event_type": "sarathi_evaluate_start",
            "execution_id": execution_id,
            "actor": request.actor,
            "source_system": request.source_system.value,
        },
    )

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

    final_risk = intelligence.final_risk
    confidence = intelligence.confidence

    decision: SarathiDecision
    failure_reason: Optional[str] = None

    if final_risk >= DENY_RISK_THRESHOLD:
        decision = SarathiDecision.DENY
        failure_reason = f"Risk score {final_risk} exceeds governance threshold {DENY_RISK_THRESHOLD}"
    elif snapshot.entropy_boundary == EntropyBoundary.CRITICAL:
        decision = SarathiDecision.DENY
        failure_reason = "CRITICAL entropy boundary exceeded. Action denied as fail-safe."
    elif (
        adapter_result.epistemic_state.value == "AMBIGUOUS"
        and final_risk >= AMBIGUOUS_DENY_THRESHOLD
    ):
        decision = SarathiDecision.DENY
        failure_reason = (
            f"Ambiguous epistemic state with risk {final_risk} >= conservative threshold {AMBIGUOUS_DENY_THRESHOLD}. Cannot allow action under epistemic uncertainty."
        )
    else:
        decision = SarathiDecision.ALLOW

    verify_snapshot_integrity(snapshot)

    response = SarathiEvaluateResponse(
        execution_id=execution_id,
        risk_score=final_risk,
        sarathi_decision=decision,
        confidence=confidence,
        failure_reason=failure_reason,
        trace_hash=trace_hash,
    )

    processing_time = time.time() - start_time
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

from dataclasses import dataclass as _governance_dataclass

@_governance_dataclass(frozen=True)
class SarathiGovernanceOutput:
    execution_id: str
    decision: str
    confidence: float
    reason: Optional[str]
    risk_score: float
    trace_hash: str

def govern(
    request: EvaluateActionRequest,
    intelligence: IntelligencePayload,
    snapshot: DGICSnapshot,
    adapter_result: DGICAdapterResult,
    trace_hash: str
) -> SarathiGovernanceOutput:
    response = evaluate_action(request, intelligence, snapshot, adapter_result, trace_hash)
    return SarathiGovernanceOutput(
        execution_id=response.execution_id,
        decision=response.sarathi_decision.value,
        confidence=response.confidence,
        reason=response.failure_reason,
        risk_score=response.risk_score,
        trace_hash=response.trace_hash,
    )


def evaluate_action_full(request: EvaluateActionRequest) -> SarathiEvaluateResponse:
    """
    Backward-compatible convenience entry point that composes the full
    Intelligence → DGIC → Governance pipeline internally.

    This exists so that test suites validating end-to-end Sarathi governance
    decisions can call evaluate_action_full(request) without needing to
    manually construct the intermediate objects.

    Production code should NOT use this — Sūtradhāra orchestrates the
    individual steps explicitly.
    """
    from app.layer3_dgic import (
        ingest_dgic_snapshot,
        adapt_dgic,
        DGICSnapshotError,
    )
    from app.layer0_intelligence import compute_intelligence

    trace_hash = compute_trace_hash(request)

    try:
        snapshot = ingest_dgic_snapshot(
            epistemic_state=request.dgic_epistemic_state.epistemic_state,
            entropy_score=request.dgic_epistemic_state.entropy_score,
            contradiction_flag=request.dgic_epistemic_state.contradiction_flag,
            lineage_hash=request.dgic_epistemic_state.lineage_hash,
            envelope_hash=request.dgic_epistemic_state.envelope_hash,
        )
    except DGICSnapshotError as e:
        return SarathiEvaluateResponse(
            execution_id=request.execution_id,
            risk_score=0.0,
            sarathi_decision=SarathiDecision.ABSTAIN,
            confidence=0.0,
            failure_reason=f"DGIC snapshot rejected: {str(e)}",
            trace_hash=trace_hash,
        )

    adapter_result = adapt_dgic(snapshot.dgic_input)
    intelligence = compute_intelligence(
        request.proposed_action,
        request.context_signals,
        adapter_result,
        request.execution_id,
    )

    return evaluate_action(request, intelligence, snapshot, adapter_result, trace_hash)
