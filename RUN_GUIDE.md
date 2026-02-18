# Text Risk Scoring Service: COMPLETE RUN GUIDE

This guide details how to install, run, verify, and integrate the service.

## 1. Installation

### Prerequisites
- Python 3.10+
- Git

### Setup
```bash
# 1. Clone
git clone https://github.com/rajaryan0726/text-risk-scoring-service.git
cd text-risk-scoring-service

# 2. Virtual Env
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt

# To deactivate later:
deactivate
```

---

## 2. Running the API Server (Standalone)
Use this mode for testing, demos, or loose coupling (Sidecar pattern).

```bash
# Run server
uvicorn app.main:app --reload
```
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Endpoint**: `POST /analyze`

### Example Request
```json
{
  "text": "This is a test input"
}
```

---

## 3. Running as a Library (Recommended for Production)
This service is designed as "Code-as-Lib". You should import the engine directly to avoid HTTP overhead.

### Safe Integration Pattern (The Two-Key Rule)
See `integration_harness/mock_host.py` for a runnable example.

```python
from app.engine import analyze_text

# 1. Get Risk Signal
signal = analyze_text("user input")

# 2. Apply Policy (YOU decide the action)
if signal["risk_category"] == "HIGH":
    # Your enforcement logic here
    print("Review required")
```

---

## 4. Verifying the System
We provide a suite of "Provers" to validate the system guarantees.

### A. Run Full Regression Suite
```bash
python -m pytest
```
*Executes 160+ tests including fuzzing, concurrency, and contracts.*

### B. Verify Determinism
```bash
python tests/stress_test_determinism.py
```
*Runs 10,000 requests to prove bit-perfect repeatability.*

### C. Profile Latency
```bash
python tests/profile_latency.py
```
*Checks P99 latency and Jitter stats.*

### D. Verify Audit Replay
```bash
python tests/test_log_replay.py
```
*Proves that logs can be mathematically reconstructed into scores.*

---

## 5. Production Readiness
Before deploying, check:
1.  **[HANDOVER.md](HANDOVER.md)**: Confirm you are using the precise version tag.
2.  **[integration-readiness.md](integration-readiness.md)**: Review the "Red Lines" (e.g. do not edit keywords at runtime).
3.  **[resource-guard.md](resource-guard.md)**: Configure your host limits (Memory/CPU) to match our specs.
