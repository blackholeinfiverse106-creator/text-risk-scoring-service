from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
from typing import Dict, Any, List

app = FastAPI(title="Mock External Bucket Service")

# In-memory ledger
_ledger: List[Dict[str, Any]] = []

class ArtifactRequest(BaseModel):
    artifact_id: str
    source_module_id: str
    schema_version: str
    timestamp_utc: str
    artifact_type: str
    payload: Dict[str, Any]
    artifact_hash: str

@app.post("/bucket/artifact")
def record_artifact(artifact: ArtifactRequest):
    _ledger.append(artifact.dict())
    return {"status": "success", "artifact_id": artifact.artifact_id}

@app.get("/bucket/artifacts")
def get_artifacts(limit: int = 100, offset: int = 0):
    return {"items": _ledger[offset:offset+limit]}

@app.get("/bucket/artifact/{artifact_id}")
def get_artifact(artifact_id: str):
    for entry in _ledger:
        if entry["artifact_id"] == artifact_id:
            return entry
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
