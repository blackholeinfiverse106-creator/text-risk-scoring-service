from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import InputSchema, OutputSchema
from app.engine import analyze_text
from app.contract_enforcement import validate_input_contract, validate_output_contract, ContractViolation
import logging
import uuid
from app.observability import setup_json_logging

# Initialize JSON logging
setup_json_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Text Risk Scoring Service")

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
