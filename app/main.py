from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import InputSchema, OutputSchema
from app.engine import analyze_text
from app.contract_enforcement import validate_input_contract, validate_output_contract, ContractViolation
import json

app = FastAPI(title="Text Risk Scoring Service")

@app.post("/analyze", response_model=OutputSchema)
def analyze(payload: InputSchema):
    try:
        # Convert Pydantic model to dict for contract validation
        request_data = payload.dict()
        
        # Validate input contract
        text = validate_input_contract(request_data)
        
        # Perform analysis
        response = analyze_text(text)
        
        # Validate output contract
        validate_output_contract(response)
        
        return response
        
    except ContractViolation as e:
        # Return contract violation as structured response
        return {
            "risk_score": 0.0,
            "confidence_score": 0.0,
            "risk_category": "LOW",
            "trigger_reasons": [],
            "processed_length": 0,
            "errors": {
                "error_code": e.code,
                "message": e.message
            }
        }
    except Exception as e:
        # Handle unexpected errors
        return {
            "risk_score": 0.0,
            "confidence_score": 0.0,
            "risk_category": "LOW",
            "trigger_reasons": [],
            "processed_length": 0,
            "errors": {
                "error_code": "INTERNAL_ERROR",
                "message": "Unexpected system error"
            }
        }


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
