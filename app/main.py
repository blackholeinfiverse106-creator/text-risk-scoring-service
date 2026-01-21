from fastapi import FastAPI
from app.schemas import InputSchema, OutputSchema
from app.engine import analyze_text

app = FastAPI(title="Text Risk Scoring Service")

@app.post("/analyze", response_model=OutputSchema)
def analyze(payload: InputSchema):
    return analyze_text(payload.text)


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
