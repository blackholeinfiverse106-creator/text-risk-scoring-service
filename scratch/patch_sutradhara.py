import os

filepath = r"c:\blackhole\text-risk-scoring-service\app\sutradhara_control_plane.py"

with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Rename invoke_mandala to _invoke_mandala_internal
code = code.replace(
"""def invoke_mandala(
    execution_id: str,
    actor: str,
    proposed_action: str,
    context_signals: List[ContextSignal],
    dgic_epistemic_state: DGICEpistemicStateInput,
    source_system: SourceSystem,
) -> MandalaInvocationResult:""",
"""def _invoke_mandala_internal(
    execution_id: str,
    actor: str,
    proposed_action: str,
    context_signals: List[ContextSignal],
    dgic_epistemic_state: DGICEpistemicStateInput,
    source_system: SourceSystem,
    niyantran_state: dict
) -> MandalaInvocationResult:"""
)

# 2. Inject state updates
code = code.replace(
"""    rajya_result, rajya_rejection = validate_execution_request({""",
"""    rajya_result, rajya_rejection = validate_execution_request({"""
) # No wait, let's inject after
code = code.replace(
"""    # ── PROOF LOG: RAJYA decision ──""",
"""    niyantran_state["rajya_verdict"] = rajya_result.value
    # ── PROOF LOG: RAJYA decision ──"""
)

code = code.replace(
"""    # ── Sarathi Gate: enforce_token() pre-Core validation ──""",
"""    niyantran_state["sarathi_status"] = enforcement_token.token_status
    # ── Sarathi Gate: enforce_token() pre-Core validation ──"""
)

code = code.replace(
"""    emit_enforcement_telemetry(
        execution_id=core_result.execution_id,""",
"""    niyantran_state["core_status"] = core_result.enforcement_decision.value
    niyantran_state["bucket_persistence"] = True  # If core_result returned, bucket layer succeeded (or failed-open)
    
    emit_enforcement_telemetry(
        execution_id=core_result.execution_id,"""
)

# 3. Add the wrapper function right before invoke_agent
wrapper = """
def invoke_mandala(
    execution_id: str,
    actor: str,
    proposed_action: str,
    context_signals: List[ContextSignal],
    dgic_epistemic_state: DGICEpistemicStateInput,
    source_system: SourceSystem,
) -> MandalaInvocationResult:
    niyantran_state = {
        "execution_id": execution_id,
        "execution_status": "IN_PROGRESS",
        "dgic_state": dgic_epistemic_state.epistemic_state,
        "risk_score": None,
        "confidence": None,
        "rajya_verdict": "PENDING",
        "sarathi_status": "PENDING",
        "core_status": "PENDING",
        "bucket_persistence": False,
        "failure_reason": None,
        "trace_hash": None
    }
    try:
        result = _invoke_mandala_internal(
            execution_id, actor, proposed_action, context_signals, dgic_epistemic_state, source_system, niyantran_state
        )
        niyantran_state["risk_score"] = result.risk_score
        niyantran_state["confidence"] = result.confidence
        niyantran_state["trace_hash"] = result.trace_hash
        
        if result.failure_reason:
            niyantran_state["failure_reason"] = result.failure_reason
            niyantran_state["execution_status"] = "FAILED"
        elif result.enforcement_decision.value == "ALLOW":
            niyantran_state["execution_status"] = "COMPLETED"
        else:
            niyantran_state["execution_status"] = result.enforcement_decision.value
            
        return result
    except Exception as e:
        niyantran_state["execution_status"] = "CRASHED"
        niyantran_state["failure_reason"] = str(e)
        raise
    finally:
        from app.niyantran_streamer import record_canonical_state
        record_canonical_state(niyantran_state)

def invoke_agent(ksml_input: KSMLInput) -> MandalaInvocationResult:
"""

code = code.replace("def invoke_agent(ksml_input: KSMLInput) -> MandalaInvocationResult:", wrapper)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Patch applied successfully.")
