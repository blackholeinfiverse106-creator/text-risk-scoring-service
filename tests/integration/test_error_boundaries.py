from fastapi.testclient import TestClient
from api.production import app

client = TestClient(app)

def test_valid_request():
    payload = {"task_id": "t-1", "text": "Normal text", "risk_level": "low"}
    resp = client.post("/api/v1/review", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert "state_hash" in data

def test_malformed_input():
    # Missing required field 'text'
    payload = {"task_id": "t-1"}
    resp = client.post("/api/v1/review", json=payload)
    assert resp.status_code == 422  # Pydantic validation error (not 500)

def test_error_boundary_catches_unhandled_exception():
    # task_id = CRASH_ME triggers a RuntimeError in the endpoint
    payload = {"task_id": "CRASH_ME", "text": "Crash this", "risk_level": "low"}
    resp = client.post("/api/v1/review", json=payload)
    # The middleware should catch it and return 400, not 500
    assert resp.status_code == 400
    assert "Error boundary caught" in resp.json()["message"]
