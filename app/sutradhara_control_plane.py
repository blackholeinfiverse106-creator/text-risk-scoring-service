"""
Sūtradhāra Control Plane — Layer 2
==================================
The master orchestrator and agent registry for the BHIV Enforcement Ecosystem.
ALL agent invocations MUST pass through this control plane. 
It prevents direct exposure of the lower-level governance and enforcement gates.

Responsibilities:
  1. Agent verification (Registry)
  2. Canonical execution_id provisioning
  3. Orchestrating the Authority-based Mandala
"""

import uuid
import logging
from typing import Optional, List

from app.enforcement_schemas import (
    SourceSystem,
    ContextSignal,
    DGICEpistemicStateInput,
    KSMLInput,
    EvaluateActionRequest,
    EnforcementDecision
)
from app.layer4_core import execute_core_mandala, MandalaInvocationResult
from app.layer3_dgic import ingest_dgic_snapshot, adapt_dgic, DGICSnapshotError
from app.layer0_intelligence import compute_intelligence
from app.layer1_sarathi import evaluate_action, compute_trace_hash
from app.layer4_enforcement import enforce, EnforcementHardFailure
from app.layer6_insightbridge import emit_enforcement_telemetry
from app.rajya_validation_engine import validate_execution_request, RajyaValidationResult

logger = logging.getLogger(__name__)

class AgentVerificationError(Exception):
    pass

class ControlPlaneHardFailure(Exception):
    pass

SUTRADHARA_AGENT_REGISTRY = {
    "enforcement_gate_v1": {
        "agent_id": "enforcement_gate_v1",
        "capability": "enforcement_gate",
        "permissions": ["READ_ONLY", "NO_EXECUTION_RIGHTS", "NO_SYSTEM_ACCESS"]
    }
}

def verify_agent_capabilities(agent_id: str, required_capability: str) -> None:
    agent = SUTRADHARA_AGENT_REGISTRY.get(agent_id)
    if not agent:
        raise AgentVerificationError(f"Agent {agent_id} is not registered in Sūtradhāra.")
    if agent.get("capability") != required_capability:
        raise AgentVerificationError(f"Agent {agent_id} lacks capability: {required_capability}.")
    if "NO_EXECUTION_RIGHTS" not in agent.get("permissions", []):
        raise ControlPlaneHardFailure(f"Agent {agent_id} failed to prove NO_EXECUTION_RIGHTS. Boundary violation.")

def provision_execution_id(provided_id: Optional[str] = None) -> str:
    return provided_id if provided_id else f"exec-{uuid.uuid4().hex[:12]}"

def verify_agent(source_system_str: str) -> SourceSystem:
    try:
        return SourceSystem(source_system_str)
    except ValueError:
        logger.error("Agent verification failed", extra={"event_type": "sutradhara_registration_failure", "attempted_agent": source_system_str})
        raise AgentVerificationError(f"Unregistered or invalid agent identity: {source_system_str}")

def invoke_mandala(
    execution_id: str,
    actor: str,
    proposed_action: str,
    context_signals: List[ContextSignal],
    dgic_epistemic_state: DGICEpistemicStateInput,
    source_system: SourceSystem,
) -> MandalaInvocationResult:
    logger.info(f"Mandala invocation started | execution_id={execution_id}", extra={"event_type": "mandala_invoked", "execution_id": execution_id, "actor": actor, "source_system": source_system.value})
    
    request = EvaluateActionRequest(
        execution_id=execution_id, actor=actor, proposed_action=proposed_action, 
        context_signals=context_signals, dgic_epistemic_state=dgic_epistemic_state, source_system=source_system
    )
    
    trace_hash = compute_trace_hash(request)
    
    try:
        snapshot = ingest_dgic_snapshot(
            epistemic_state=dgic_epistemic_state.epistemic_state,
            entropy_score=dgic_epistemic_state.entropy_score,
            contradiction_flag=dgic_epistemic_state.contradiction_flag,
            lineage_hash=dgic_epistemic_state.lineage_hash,
            envelope_hash=dgic_epistemic_state.envelope_hash,
        )
        adapter_result = adapt_dgic(snapshot.dgic_input)
    except DGICSnapshotError as e:
        logger.warning(f"DGIC snapshot ingestion failed | execution_id={execution_id}")
        result = MandalaInvocationResult(
            execution_id=execution_id, enforcement_decision=EnforcementDecision.ABSTAIN,
            risk_score=0.0, confidence=0.0, trace_hash=trace_hash, failure_reason=f"DGIC snapshot rejected: {str(e)}"
        )
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    intelligence = compute_intelligence(proposed_action, context_signals, adapter_result, execution_id)
    sarathi_response = evaluate_action(request, intelligence, snapshot, adapter_result, trace_hash)
    
    if sarathi_response is None:
        logger.error("System reject before enforcement: Sarathi missing")
        result = MandalaInvocationResult(
            execution_id=execution_id, enforcement_decision=EnforcementDecision.DENY,
            risk_score=0.0, confidence=0.0, trace_hash=execution_id[-64:].ljust(64, '0'), failure_reason="System reject: Sarathi evaluation missing"
        )
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    if sarathi_response.execution_id != execution_id:
        result = MandalaInvocationResult(execution_id=execution_id, enforcement_decision=EnforcementDecision.DENY, risk_score=0.0, confidence=0.0, trace_hash=sarathi_response.trace_hash, failure_reason=f"Execution ID mismatch: pipeline sent '{execution_id}' but Sarathi returned '{sarathi_response.execution_id}'. Execution rejected.")
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    dgic_snapshot_dict = dgic_epistemic_state.model_dump(mode="json")
    
    try:
        verdict = enforce(
            original_execution_id=execution_id,
            sarathi_decision=sarathi_response.sarathi_decision.value,
            sarathi_execution_id=sarathi_response.execution_id,
            sarathi_confidence=sarathi_response.confidence,
            dgic_snapshot=dgic_snapshot_dict,
        )
    except EnforcementHardFailure as e:
        logger.error(f"Enforcement hard failure | execution_id={execution_id}")
        result = MandalaInvocationResult(execution_id=execution_id, enforcement_decision=EnforcementDecision.DENY, risk_score=0.0, confidence=0.0, trace_hash=sarathi_response.trace_hash, failure_reason=f"Enforcement hard failure: {e.code} — {e.message}")
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    # ── PROOF LOG: RAJYA validation start ──
    logger.info(
        f"RAJYA VALIDATION START | execution_id={execution_id} | sarathi_decision={sarathi_response.sarathi_decision.value}",
        extra={
            "event_type": "rajya_validation_start",
            "execution_id": execution_id,
            "sarathi_decision": sarathi_response.sarathi_decision.value,
        },
    )

    # ── RAJYA — Final authority validation before Core execution ──
    rajya_result, rajya_rejection = validate_execution_request({
        "execution_id": execution_id,
        "sarathi_decision": sarathi_response.sarathi_decision.value,
        "sarathi_execution_id": sarathi_response.execution_id,
        "enforcement_verdict": verdict,
    })

    # ── PROOF LOG: RAJYA decision ──
    logger.info(
        f"RAJYA DECISION | execution_id={execution_id} | result={rajya_result.value} | rejection={rajya_rejection.code if rajya_rejection else 'NONE'}",
        extra={
            "event_type": "rajya_decision",
            "execution_id": execution_id,
            "rajya_result": rajya_result.value,
            "rajya_rejection_code": rajya_rejection.code if rajya_rejection else None,
        },
    )

    if rajya_result != RajyaValidationResult.EXECUTION_APPROVED:
        logger.warning(
            f"RAJYA rejected execution | execution_id={execution_id} | code={rajya_rejection.code}",
            extra={"event_type": "rajya_pipeline_reject", "execution_id": execution_id, "rajya_code": rajya_rejection.code},
        )
        result = MandalaInvocationResult(
            execution_id=execution_id,
            enforcement_decision=EnforcementDecision.DENY,
            risk_score=sarathi_response.risk_score,
            confidence=sarathi_response.confidence,
            trace_hash=sarathi_response.trace_hash,
            failure_reason=f"RAJYA REJECT: {rajya_rejection.code} — {rajya_rejection.reason}",
        )
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    # ── PROOF LOG: Core execution decision ──
    logger.info(
        f"CORE HANDOFF | execution_id={execution_id} | rajya=EXECUTION_APPROVED → Core will execute",
        extra={
            "event_type": "core_handoff_proof",
            "execution_id": execution_id,
            "rajya_result": rajya_result.value,
        },
    )

    core_result = execute_core_mandala(
        execution_id=execution_id,
        proposed_action=proposed_action,
        rajya_result=rajya_result,
        sarathi_risk_score=sarathi_response.risk_score,
        sarathi_confidence=sarathi_response.confidence,
        sarathi_trace_hash=sarathi_response.trace_hash,
        sarathi_failure_reason=sarathi_response.failure_reason,
        request_payload=request.model_dump(mode="json"),
        dgic_snapshot_dict=dgic_snapshot_dict
    )
    
    emit_enforcement_telemetry(
        execution_id=core_result.execution_id,
        enforcement_decision=core_result.enforcement_decision.value,
        risk_score=core_result.risk_score,
        confidence=core_result.confidence,
        trace_hash=core_result.trace_hash,
    )
    
    return core_result

def invoke_agent(ksml_input: KSMLInput) -> MandalaInvocationResult:
    if not isinstance(ksml_input, KSMLInput):
        raise ControlPlaneHardFailure("NON_KSML_INPUT_DETACHED: Input must be a valid KSMLInput instance.")

    canonical_exec_id = provision_execution_id(ksml_input.execution_id)
    metadata = ksml_input.metadata
    actor = metadata.get("actor", "UNKNOWN")
    proposed_action = metadata.get("proposed_action", "UNKNOWN")
    source_system_str = metadata.get("source_system", "UNKNOWN")

    verify_agent_capabilities("enforcement_gate_v1", "enforcement_gate")
    
    dgic_dict = metadata["dgic_epistemic_state"]
    if isinstance(dgic_dict, DGICEpistemicStateInput):
        dgic_epistemic_state = dgic_dict
    else:
        dgic_epistemic_state = DGICEpistemicStateInput(**dgic_dict)

    canonical_system = verify_agent(source_system_str)

    result = invoke_mandala(
        execution_id=canonical_exec_id,
        actor=actor,
        proposed_action=proposed_action,
        context_signals=ksml_input.structured_signals,
        dgic_epistemic_state=dgic_epistemic_state,
        source_system=canonical_system
    )

    if result.execution_id != canonical_exec_id:
        raise ControlPlaneHardFailure("EXECUTION_ID_CORRUPTION: Pipeline failed to preserve execution identity.")

    return result
