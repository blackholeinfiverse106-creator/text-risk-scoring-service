from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import InputSchema, OutputSchema, DGICIngestRequest, AggregateRequest
from app.layer0_intelligence import analyze_text
from app.contract_enforcement import validate_input_contract, validate_output_contract, ContractViolation
from app.layer3_dgic import validate_dgic_input, adapt_dgic, apply_dgic_modifiers, DGICContractViolation
from app.layer6_insightbridge import aggregate_signals
from app.layer6_insightbridge import map_to_insightbridge_contract
import logging
import uuid
from app.observability import setup_json_logging
from app.unified_schemas import UnifiedAggregateRequest, UnifiedSignalInput
from app.layer6_insightbridge import aggregate_unified_signals, UnifiedSignal, SignalType
from app.layer3_dgic import wrap_in_dgic_envelope
from app.layer6_insightbridge import emit_telemetry_dict
from app.sutradhara_control_plane import invoke_agent, AgentVerificationError
from app.enforcement_schemas import ContextSignal, DGICEpistemicStateInput
from fastapi import HTTPException
from pydantic import BaseModel as _CoreBaseModel
from typing import Optional


# Initialize JSON logging
setup_json_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="BHIV Enforcement Gateway")

# CORS middleware - must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze", response_model=OutputSchema)
def analyze(payload: InputSchema):
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"
    logger.info("Request received", extra={"execution_id": execution_id, "event_type": "analysis_request"})
    
    try:
        request_data = payload.dict()
        logger.debug("Input validation starting", extra={"execution_id": execution_id, "event_type": "contract_enforcement"})
        
        text = validate_input_contract(request_data)
        logger.info(f"Input validated | length={len(text)}", extra={"execution_id": execution_id, "event_type": "contract_passed", "details": {"length": len(text)}})
        
        response = analyze_text(text, execution_id=execution_id)
        logger.info(f"Analysis complete | risk={response['risk_category']}", extra={"execution_id": execution_id, "event_type": "engine_success", "details": {"risk": response['risk_category']}})
        
        validate_output_contract(response)
        logger.debug("Output validated", extra={"execution_id": execution_id, "event_type": "contract_enforcement_passed"})
        
        return response
        
    except ContractViolation as e:
        logger.warning(f"Contract violation | code={e.code}", extra={"execution_id": execution_id, "event_type": "input_validation_failed", "details": {"code": e.code, "why": e.message}})
        return {
            "risk_score": 0.0,
            "confidence_score": 0.0,
            "risk_category": "LOW",
            "trigger_reasons": [],
            "processed_length": 0,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": {
                "error_code": e.code,
                "message": e.message
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error | execution_id={execution_id} | event_type=unhandled_exception | why={str(e)}", exc_info=True)
        return {
            "risk_score": 0.0,
            "confidence_score": 0.0,
            "risk_category": "LOW",
            "trigger_reasons": [],
            "processed_length": 0,
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": {
                "error_code": "INTERNAL_ERROR",
                "message": "Unexpected system error"
            }
        }

@app.post("/api/v1/dgic/ingest")
def dgic_ingest(payload: DGICIngestRequest):
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"
    logger.info("DGIC envelope received", extra={"execution_id": execution_id, "event_type": "dgic_ingest"})
    try:
        dgic_input = validate_dgic_input(payload.dgic_envelope)
        base_result = analyze_text(payload.text, execution_id=execution_id)
        final_result = apply_dgic_modifiers(base_result, adapter_result=adapt_dgic(dgic_input))
        return final_result
    except DGICContractViolation as e:
        logger.warning(f"DGIC Contract violation | code={e.code}", extra={"execution_id": execution_id, "details": {"why": e.message}})
        return {"error": e.message, "error_code": e.code}

@app.post("/api/v1/aggregate")
def aggregate_endpoint(payload: AggregateRequest):
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"
    logger.info("Aggregation request received", extra={"execution_id": execution_id, "event_type": "aggregation"})
    try:
        if not payload.signals:
            return {"error": "No signals provided"}
            
        signals = []
        for p in payload.signals:
            dgic_input = validate_dgic_input(p.dgic_envelope)
            signals.append((p.text, dgic_input))
            
        agg_result = aggregate_signals(signals)
        lineage_hash = signals[0][1].lineage_hash if signals else "none"
        ib_payload = map_to_insightbridge_contract(agg_result, lineage_hash)
        return ib_payload
    except Exception as e:
        logger.error("Aggregation error", exc_info=True)
        return {"error": str(e), "error_code": "AGGREGATION_FAILED"}

@app.post("/api/v1/aggregate/unified")
def aggregate_unified_endpoint(payload: UnifiedAggregateRequest):
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"
    logger.info("Unified aggregation request received", extra={"execution_id": execution_id, "event_type": "unified_aggregation"})
    try:
        if not payload.signals:
            return {"error": "No signals provided"}
            
        unified_signals = []
        for p in payload.signals:
            # Structurally validate and convert DGIC envelope
            dgic_obj = validate_dgic_input(p.dgic_envelope)
            
            sig = UnifiedSignal(
                signal_id=p.signal_id,
                signal_type=p.signal_type,
                base_risk_score=p.base_risk_score,
                base_confidence_score=p.base_confidence_score,
                dgic_envelope=dgic_obj
            )
            unified_signals.append(sig)
            
        agg_result = aggregate_unified_signals(unified_signals)
        
        # Day 2A: Wrap in DGIC epistemic envelope
        dgic_envelope = wrap_in_dgic_envelope(agg_result)
        
        # Day 2B: Emit InsightBridge telemetry event
        telemetry = emit_telemetry_dict(execution_id, dgic_envelope)
        
        # Map to InsightBridge contract
        lineage_hash = unified_signals[0].dgic_envelope.lineage_hash if unified_signals else "none"
        ib_payload = map_to_insightbridge_contract(agg_result, lineage_hash)
        
        # Enrich response with DGIC envelope and telemetry
        ib_payload["dgic_envelope"] = {
            "epistemic_confidence": dgic_envelope.epistemic_confidence,
            "signal_lineage": dgic_envelope.signal_lineage,
            "collapse_state": dgic_envelope.collapse_state,
            "truth_boundary_reference": dgic_envelope.truth_boundary_reference,
        }
        ib_payload["telemetry"] = telemetry
        
        return ib_payload
    except Exception as e:
        logger.error("Unified aggregation error", exc_info=True)
        return {"error": str(e), "error_code": "UNIFIED_AGGREGATION_FAILED"}


# ============================================================
# Sūtradhāra Control Plane Endpoint (Layer 2)
# ============================================================

from app.layer4_core import MandalaInvocationResult

class SutradharaInvokeRequest(_CoreBaseModel):
    """API-level request for Agent invocations."""
    execution_id: Optional[str] = None
    actor: str
    proposed_action: str
    context_signals: list[ContextSignal] = []
    dgic_epistemic_state: DGICEpistemicStateInput
    source_system: str  # String representation, dynamically validated by registry


@app.post("/api/v1/sutradhara/invoke", response_model=MandalaInvocationResult)
def sutradhara_invoke(payload: SutradharaInvokeRequest):
    """
    The exclusive operational entry-point for all BHIV agents.
    Control Plane (Layer 2) routing ensures agent registration verification
    before descending into Sarathi Governance (Layer 1) and Core Execution/Enforcement (Layer 4).
    """
    logger.info(
        "Sūtradhāra invocation requested",
        extra={
            "event_type": "sutradhara_api_request",
            "execution_id": payload.execution_id or "unassigned",
            "source_system": payload.source_system,
        },
    )
    try:
        from app.enforcement_schemas import KSMLInput
        ksml_input = KSMLInput(
            execution_id=payload.execution_id or f"exec-{uuid.uuid4().hex[:12]}",
            structured_signals=payload.context_signals,
            metadata={
                "actor": payload.actor,
                "proposed_action": payload.proposed_action,
                "source_system": payload.source_system,
                "dgic_epistemic_state": payload.dgic_epistemic_state.model_dump() if hasattr(payload.dgic_epistemic_state, "model_dump") else payload.dgic_epistemic_state.dict()
            }
        )
        result = invoke_agent(ksml_input)
        return result
    except AgentVerificationError as e:
        logger.error(f"Sūtradhāra registration breach: {str(e)}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(
            "Sūtradhāra invocation failed",
            exc_info=True,
            extra={"event_type": "sutradhara_error"},
        )
        return MandalaInvocationResult(
            execution_id=payload.execution_id or "sys-failure",
            enforcement_decision="DENY",
            risk_score=0.0,
            confidence=0.0,
            failure_reason=f"Internal Control Plane Error: {str(e)}",
            trace_hash="0" * 64
        )

# ============================================================
# Bucket Ledger + Replay Verification Endpoints
# ============================================================

from app.layer5_bucket import get_bucket_entries, get_bucket_entry
from app.layer5_bucket import verify_by_trace_hash, verify_all, ReplayResult
from dataclasses import asdict as _asdict

@app.get("/api/v1/bucket/entries")
def bucket_list_entries():
    """List all enforcement bucket entries."""
    entries = get_bucket_entries()
    # Support pagination dict or direct list list
    items = entries.get("items", []) if isinstance(entries, dict) else entries
    return items

@app.post("/api/v1/bucket/replay/{trace_hash}")
def bucket_replay_entry(trace_hash: str):
    """Replay-verify a specific bucket entry by trace hash."""
    result = verify_by_trace_hash(trace_hash)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"No bucket entry found for trace_hash={trace_hash}"},
        )
    return _asdict(result)

@app.post("/api/v1/bucket/replay_all")
def bucket_replay_all():
    """Replay-verify ALL bucket entries."""
    results = verify_all()
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.match),
        "failed": sum(1 for r in results if not r.match),
        "results": [_asdict(r) for r in results],
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "bhiv-enforcement-gateway"}

# ============================================================
# Sarathi Enforcement and Validation Endpoints
# ============================================================

from app.layer1_sarathi import (
    SarathiEnforcementToken,
    enforce_token,
    validate_enforcement_token,
    SarathiHardBlockError
)
from fastapi import Query

class SarathiTokenInput(_CoreBaseModel):
    execution_id: str
    rajya_verdict: str
    token_status: str
    timestamp: str
    signature_hash: str

class EnforceRequest(_CoreBaseModel):
    token: Optional[SarathiTokenInput] = None
    pipeline_execution_id: Optional[str] = None

@app.post("/sarathi/enforce")
def api_sarathi_enforce(request: EnforceRequest):
    token_obj = None
    if request.token:
        token_obj = SarathiEnforcementToken(
            execution_id=request.token.execution_id,
            rajya_verdict=request.token.rajya_verdict,
            token_status=request.token.token_status,
            timestamp=request.token.timestamp,
            signature_hash=request.token.signature_hash
        )
    try:
        verdict = enforce_token(token_obj, pipeline_execution_id=request.pipeline_execution_id)
        return {"status": verdict}
    except SarathiHardBlockError as e:
        return JSONResponse(status_code=403, content={"error": e.message, "code": e.code, "status": "BLOCK"})


@app.get("/sarathi/validate-token")
def api_validate_token(
    execution_id: str = Query(...),
    rajya_verdict: str = Query(...),
    token_status: str = Query(...),
    timestamp: str = Query(...),
    signature_hash: str = Query(...),
    pipeline_execution_id: Optional[str] = Query(None)
):
    token_obj = SarathiEnforcementToken(
        execution_id=execution_id,
        rajya_verdict=rajya_verdict,
        token_status=token_status,
        timestamp=timestamp,
        signature_hash=signature_hash
    )
    is_valid = validate_enforcement_token(token_obj, pipeline_execution_id)
    return {"is_valid": is_valid}
