from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import InputSchema, OutputSchema, DGICIngestRequest, AggregateRequest
from app.engine import analyze_text
from app.contract_enforcement import validate_input_contract, validate_output_contract, ContractViolation
from app.dgic_adapter import validate_dgic_input, adapt_dgic, apply_dgic_modifiers, DGICContractViolation
from app.enforcement_aggregator import aggregate_signals
from app.insightbridge_adapter import map_to_insightbridge_contract
import logging
import uuid
from app.observability import setup_json_logging
from app.unified_schemas import UnifiedAggregateRequest, UnifiedSignalInput
from app.signal_aggregator import aggregate_unified_signals, UnifiedSignal, SignalType
from app.dgic_enforcement_bridge import wrap_in_dgic_envelope
from app.insightbridge_telemetry import emit_telemetry_dict
from app.enforcement_schemas import EvaluateActionRequest, EvaluateActionResponse
from app.enforcement_gate import evaluate_action


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
    correlation_id = str(uuid.uuid4())[:8]
    logger.info("Request received", extra={"correlation_id": correlation_id, "event_type": "analysis_request"})
    
    try:
        request_data = payload.dict()
        logger.debug("Input validation starting", extra={"correlation_id": correlation_id, "event_type": "contract_enforcement"})
        
        text = validate_input_contract(request_data)
        logger.info(f"Input validated | length={len(text)}", extra={"correlation_id": correlation_id, "event_type": "contract_passed", "details": {"length": len(text)}})
        
        response = analyze_text(text, correlation_id=correlation_id)
        logger.info(f"Analysis complete | risk={response['risk_category']}", extra={"correlation_id": correlation_id, "event_type": "engine_success", "details": {"risk": response['risk_category']}})
        
        validate_output_contract(response)
        logger.debug("Output validated", extra={"correlation_id": correlation_id, "event_type": "contract_enforcement_passed"})
        
        return response
        
    except ContractViolation as e:
        logger.warning(f"Contract violation | code={e.code}", extra={"correlation_id": correlation_id, "event_type": "input_validation_failed", "details": {"code": e.code, "why": e.message}})
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
        logger.error(f"Unexpected error | correlation_id={correlation_id} | event_type=unhandled_exception | why={str(e)}", exc_info=True)
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
    correlation_id = str(uuid.uuid4())[:8]
    logger.info("DGIC envelope received", extra={"correlation_id": correlation_id, "event_type": "dgic_ingest"})
    try:
        dgic_input = validate_dgic_input(payload.dgic_envelope)
        base_result = analyze_text(payload.text, correlation_id=correlation_id)
        final_result = apply_dgic_modifiers(base_result, adapter_result=adapt_dgic(dgic_input))
        return final_result
    except DGICContractViolation as e:
        logger.warning(f"DGIC Contract violation | code={e.code}", extra={"correlation_id": correlation_id, "details": {"why": e.message}})
        return {"error": e.message, "error_code": e.code}

@app.post("/api/v1/aggregate")
def aggregate_endpoint(payload: AggregateRequest):
    correlation_id = str(uuid.uuid4())[:8]
    logger.info("Aggregation request received", extra={"correlation_id": correlation_id, "event_type": "aggregation"})
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
    correlation_id = str(uuid.uuid4())[:8]
    logger.info("Unified aggregation request received", extra={"correlation_id": correlation_id, "event_type": "unified_aggregation"})
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
        telemetry = emit_telemetry_dict(dgic_envelope)
        
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
# Canonical Enforcement Gateway Endpoint
# ============================================================

@app.post("/api/v1/enforce/evaluate_action", response_model=EvaluateActionResponse)
def enforce_evaluate_action(payload: EvaluateActionRequest):
    """
    The deterministic enforcement gate for all BHIV systems.
    All proposed actions MUST pass through this endpoint before execution.
    """
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(
        "Enforcement evaluation request received",
        extra={
            "correlation_id": correlation_id,
            "event_type": "enforcement_request",
            "action_id": payload.action_id,
            "source_system": payload.source_system.value,
        },
    )
    try:
        result = evaluate_action(payload)
        logger.info(
            f"Enforcement result: {result.enforcement_decision}",
            extra={
                "correlation_id": correlation_id,
                "event_type": "enforcement_result",
                "decision": result.enforcement_decision,
                "risk_score": result.risk_score,
                "trace_hash": result.trace_hash,
            },
        )
        return result
    except Exception as e:
        logger.error(
            "Enforcement evaluation error",
            exc_info=True,
            extra={"correlation_id": correlation_id, "event_type": "enforcement_error"},
        )
        return EvaluateActionResponse(
            risk_score=0.0,
            enforcement_decision="ABSTAIN",
            confidence=0.0,
            failure_reason=f"Internal enforcement error: {str(e)}",
            trace_hash="0" * 64,
        )


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "bhiv-enforcement-gateway"}
