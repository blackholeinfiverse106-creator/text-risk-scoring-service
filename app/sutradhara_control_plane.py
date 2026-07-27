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

Pipeline Flow (Post-Sarathi Refactor):
  Sūtradhāra → DGIC → Intelligence → Enforcement → RAJYA → Sarathi[TOKEN MINT] → Core

  Sarathi no longer decides. Sarathi only mints enforcement tokens after RAJYA approval.
  Decision derivation from intelligence output is performed inline by the orchestrator
  to feed RAJYA's existing interface (RAJYA is NOT modified).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from app.enforcement_schemas import (
    SourceSystem,
    ContextSignal,
    DGICEpistemicStateInput,
    KSMLInput,
    EvaluateActionRequest,
    EnforcementDecision,
    SarathiDecision,
)
from app.layer4_core import execute_core_mandala, MandalaInvocationResult
from app.layer3_dgic import ingest_dgic_snapshot, adapt_dgic, DGICSnapshotError, evaluate_external_dgic
from app.layer0_intelligence import compute_intelligence
from app.layer1_sarathi import (
    compute_trace_hash,
    mint_enforcement_token,
    enforce_token,
    SarathiTokenMintError,
    SarathiHardBlockError,
)
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

# ============================================================
# Intelligence → Decision derivation thresholds
# These were previously in Sarathi. They are now inline in the
# orchestrator to feed RAJYA's existing interface.
# Sarathi itself contains ZERO decision logic.
# ============================================================
_DENY_RISK_THRESHOLD = 0.7
_AMBIGUOUS_DENY_THRESHOLD = 0.3


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


def _derive_decision_from_intelligence(intelligence, adapter_result, snapshot) -> str:
    """
    Inline decision derivation from intelligence output.
    This feeds RAJYA's existing interface (RAJYA is NOT modified).

    This is NOT Sarathi deciding — this is the orchestrator mapping
    intelligence results to a decision value for RAJYA consumption.
    Sarathi itself contains ZERO decision logic.
    """
    from app.layer3_dgic import EntropyBoundary

    if adapter_result.abstain:
        return SarathiDecision.ABSTAIN.value

    final_risk = intelligence.final_risk

    if final_risk >= _DENY_RISK_THRESHOLD:
        return SarathiDecision.DENY.value
    elif snapshot.entropy_boundary == EntropyBoundary.CRITICAL:
        return SarathiDecision.DENY.value
    elif (
        adapter_result.epistemic_state.value == "AMBIGUOUS"
        and final_risk >= _AMBIGUOUS_DENY_THRESHOLD
    ):
        return SarathiDecision.DENY.value
    else:
        return SarathiDecision.ALLOW.value


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
    
    # ── Step 1: DGIC Snapshot Ingestion ──
    try:
        external_eval = evaluate_external_dgic(
            execution_id=execution_id,
            signals=context_signals,
            metadata={"actor": actor, "proposed_action": proposed_action, "source_system": source_system.value}
        )
        if external_eval:
            ep_state = external_eval["epistemic_state"]
            ent_score = external_eval["entropy_score"]
            contra_flag = external_eval["contradiction_flag"]
            lin_hash = external_eval["lineage_hash"]
            env_hash = external_eval["envelope_hash"]
            logger.info(f"Adopted external deployed DGIC evaluation | state={ep_state} | entropy={ent_score}")
        else:
            ep_state = dgic_epistemic_state.epistemic_state
            ent_score = dgic_epistemic_state.entropy_score
            contra_flag = dgic_epistemic_state.contradiction_flag
            lin_hash = dgic_epistemic_state.lineage_hash
            env_hash = dgic_epistemic_state.envelope_hash

        snapshot = ingest_dgic_snapshot(
            epistemic_state=ep_state,
            entropy_score=ent_score,
            contradiction_flag=contra_flag,
            lineage_hash=lin_hash,
            envelope_hash=env_hash,
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

    # ── Step 2: Intelligence Computation (Layer 0 — unchanged) ──
    intelligence = compute_intelligence(proposed_action, context_signals, adapter_result, execution_id)

    # ── Step 3: Decision derivation (inline — NOT Sarathi) ──
    # This feeds RAJYA's existing interface. Sarathi does NOT decide.
    derived_decision = _derive_decision_from_intelligence(intelligence, adapter_result, snapshot)
    derived_confidence = intelligence.confidence

    logger.info(
        f"Orchestrator derived decision | execution_id={execution_id} | decision={derived_decision}",
        extra={
            "event_type": "sutradhara_decision_derived",
            "execution_id": execution_id,
            "derived_decision": derived_decision,
            "risk_score": intelligence.final_risk,
            "confidence": derived_confidence,
        },
    )

    # ── Step 4: Enforcement Gate ──
    dgic_snapshot_dict = dgic_epistemic_state.model_dump(mode="json")

    try:
        verdict = enforce(
            original_execution_id=execution_id,
            sarathi_decision=derived_decision,
            sarathi_execution_id=execution_id,
            sarathi_confidence=derived_confidence,
            dgic_snapshot=dgic_snapshot_dict,
        )
    except EnforcementHardFailure as e:
        logger.error(f"Enforcement hard failure | execution_id={execution_id}")
        result = MandalaInvocationResult(execution_id=execution_id, enforcement_decision=EnforcementDecision.DENY, risk_score=0.0, confidence=0.0, trace_hash=trace_hash, failure_reason=f"Enforcement hard failure: {e.code} — {e.message}")
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    # ── PROOF LOG: RAJYA validation start ──
    logger.info(
        f"RAJYA VALIDATION START | execution_id={execution_id} | sarathi_decision={derived_decision}",
        extra={
            "event_type": "rajya_validation_start",
            "execution_id": execution_id,
            "sarathi_decision": derived_decision,
        },
    )

    # ── Step 5: RAJYA — Final authority validation (UNMODIFIED) ──
    rajya_result, rajya_rejection = validate_execution_request({
        "execution_id": execution_id,
        "sarathi_decision": derived_decision,
        "sarathi_execution_id": execution_id,
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
            risk_score=intelligence.final_risk,
            confidence=derived_confidence,
            trace_hash=trace_hash,
            failure_reason=f"RAJYA REJECT: {rajya_rejection.code} — {rajya_rejection.reason}",
        )
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    # ── Step 6: Sarathi — Mint enforcement token (ONLY after RAJYA approval) ──
    # Sarathi does NOT decide. It ONLY mints the token.
    token_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    try:
        enforcement_token = mint_enforcement_token(
            execution_id=execution_id,
            rajya_verdict=rajya_result.value,
            timestamp=token_timestamp,
        )
    except SarathiTokenMintError as e:
        logger.error(f"Sarathi token mint failed | execution_id={execution_id} | code={e.code}")
        result = MandalaInvocationResult(
            execution_id=execution_id,
            enforcement_decision=EnforcementDecision.DENY,
            risk_score=intelligence.final_risk,
            confidence=derived_confidence,
            trace_hash=trace_hash,
            failure_reason=f"Sarathi token mint error: {e.code} — {e.message}",
        )
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    # ── Sarathi Gate: enforce_token() pre-Core validation ──
    try:
        enforce_token(enforcement_token, pipeline_execution_id=execution_id)
    except SarathiHardBlockError as e:
        logger.error(f"Sarathi gate HARD BLOCK post-mint | execution_id={execution_id} | code={e.code}")
        result = MandalaInvocationResult(
            execution_id=execution_id,
            enforcement_decision=EnforcementDecision.DENY,
            risk_score=intelligence.final_risk,
            confidence=derived_confidence,
            trace_hash=trace_hash,
            failure_reason=f"Sarathi gate HARD BLOCK: {e.code} — {e.message}",
        )
        emit_enforcement_telemetry(execution_id, result.enforcement_decision.value, result.risk_score, result.confidence, result.trace_hash)
        return result

    # ── PROOF LOG: Core execution decision ──
    logger.info(
        f"CORE HANDOFF | execution_id={execution_id} | rajya=EXECUTION_APPROVED | token_status=VALID → Core will execute",
        extra={
            "event_type": "core_handoff_proof",
            "execution_id": execution_id,
            "rajya_result": rajya_result.value,
            "token_status": enforcement_token.token_status,
            "token_signature": enforcement_token.signature_hash,
        },
    )

    # ── Step 7: Core — Execute ONLY with valid enforcement token ──
    core_result = execute_core_mandala(
        execution_id=execution_id,
        proposed_action=proposed_action,
        enforcement_token=enforcement_token,
        sarathi_risk_score=intelligence.final_risk,
        sarathi_confidence=derived_confidence,
        sarathi_trace_hash=trace_hash,
        request_payload=request.model_dump(mode="json"),
        dgic_snapshot_dict=request.dgic_epistemic_state.model_dump(mode="json"),
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
