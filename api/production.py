from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from security.middleware import ErrorBoundaryMiddleware
from task_selector.review_orchestrator import orchestrate_review

app = FastAPI(title="Parikshak Remediation API")
app.add_middleware(ErrorBoundaryMiddleware)

class ReviewRequest(BaseModel):
    task_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    risk_level: str = Field(default="low")

class ReviewResponse(BaseModel):
    status: str
    state_hash: str
    score: int
    llm_analysis: str

@app.post("/api/v1/review", response_model=ReviewResponse)
async def submit_review(request: ReviewRequest):
    # This route validates inbound request schemas with strict Pydantic models (ReviewRequest)
    
    # Trigger an explicit exception for testing if task_id == "CRASH_ME"
    if request.task_id == "CRASH_ME":
        raise RuntimeError("Simulated internal crash")

    result = orchestrate_review(request.model_dump())
    
    return ReviewResponse(
        status=result["status"],
        state_hash=result["rule_engine_output"]["state_hash"],
        score=result["rule_engine_output"]["result"]["score"],
        llm_analysis=result["llm_analysis"]
    )
