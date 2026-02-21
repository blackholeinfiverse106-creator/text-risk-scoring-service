# Clean Clone Validation

**Claim:** The service starts correctly from a clean clone with no pre-existing state.

## Steps to Verify

```bash
# 1. Clone and enter
git clone <repo>
cd text-risk-scoring-service

# 2. Create virtualenv and install
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. Run all proofs
python -m pytest tests/ -q
python error-propagation-proof.py
python trace-lineage-demo.py

# 4. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Validation Checklist

| Check | Expected |
|---|---|
| `pip install -r requirements.txt` succeeds | ✓ No version conflicts |
| `pytest tests/ -q` exits 0 | ✓ All tests pass |
| `error-propagation-proof.py` exits 0 | ✓ 9/9 paths verified |
| `trace-lineage-demo.py` exits 0 | ✓ Lineage proven |
| `uvicorn app.main:app` starts | ✓ No config files required |
| `POST /analyze` with `{"text":"hello"}` | ✓ Returns valid response |

## Zero External Dependencies

| Dependency | Role | Version pinned? |
|---|---|---|
| `fastapi` | HTTP server | No (latest stable) |
| `uvicorn` | ASGI runner | No |
| `pydantic` | Schema validation | No |
| `pytest` | Test runner | No |
| `pytest-cov` | Coverage | No |

No database, no cache, no queue, no cloud SDK. Service is **fully self-contained**.

## Environment Variables Required

**None.** All configuration is baked into constants in `app/engine.py`. No `.env` file needed.
