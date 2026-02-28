# Text Risk Scoring Service

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Release](https://img.shields.io/badge/release-v1.0.0--integration-green.svg)](#)

A **deterministic, contract-sealed** text risk scoring API. Scores text content across 10 risk categories using rule-based keyword detection. Structurally incapable of making enforcement decisions.

---

## Design Principles

| Principle | Implementation |
|---|---|
| Deterministic | Same input → same output, always (proven across 150k runs) |
| Non-authority | `safety_metadata.authority` is permanently `"NONE"` |
| Non-decision | `safety_metadata.is_decision` is permanently `false` |
| Fail-safe | All error paths return a complete, structured response |
| Stateless | No memory between requests; no shared mutable state |

---

## Quick Start

```bash
# Clone and install
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run all tests
python -m pytest tests/ decision-injection-tests/ escalation-tests/ -q
```

---

## API

### `POST /analyze`

**Request:**
```json
{
  "text": "string (1–5000 chars, UTF-8)",
  "context": {
    "caller_id": "string (optional)",
    "use_case":  "string (optional)"
  }
}
```

**Response:**
```json
{
  "risk_score":       0.8,
  "confidence_score": 0.8,
  "risk_category":    "HIGH",
  "trigger_reasons":  ["Detected violence keyword: kill"],
  "processed_length": 42,
  "safety_metadata": {
    "is_decision": false,
    "authority":   "NONE",
    "actionable":  false
  },
  "errors": null
}
```

**Risk categories:** `LOW` (score < 0.3) · `MEDIUM` (0.3–0.69) · `HIGH` (≥ 0.7)

**Error response shape** (same structure, `errors` is non-null, `risk_score` is 0.0).

Full contract: see [`contracts-v3.md`](contracts-v3.md).

---

## Risk Categories

| Category | Examples |
|---|---|
| violence | kill, attack, bomb, shoot |
| fraud | scam, phishing, money laundering |
| abuse | harassment, bully, slur |
| sexual | explicit content, rape, minors |
| drugs | cocaine, heroin, overdose |
| extremism | terrorism, radicalize, ISIS |
| self_harm | suicide, self harm, want to die |
| cybercrime | malware, ransomware, SQL injection |
| weapons | firearm, explosive, silencer |
| threats | "I will kill you", blackmail |

---

## Architecture

```
POST /analyze
     │
     ├─ validate_input_contract()   [contract_enforcement.py]
     ├─ analyze_text()              [engine.py]  ← all logic here
     ├─ validate_output_contract()  [contract_enforcement.py]
     └─ Return structured response
```

No database. No cache. No external calls. Fully self-contained.

---

## Proofs & Certification

| Proof | Command | Result |
|---|---|---|
| Determinism | `python replay_harness.py` | 150k runs, 0 divergences |
| Thread safety | `python thread_safety_proof.py` | 200 threads, 0 divergences |
| Error propagation | `python error-propagation-proof.py` | 9/9 paths verified |
| Trace lineage | `python trace-lineage-demo.py` | 3/3 proven, 0 bleed |
| Misuse resistance | `python -m pytest decision-injection-tests/ escalation-tests/` | 67 tests pass |

---

## Key Documents

| Document | Purpose |
|---|---|
| [`contracts-v3.md`](contracts-v3.md) | **Frozen** API contract |
| [`invariants-v2.md`](invariants-v2.md) | 14 revalidated invariants |
| [`fail-mode-matrix.md`](fail-mode-matrix.md) | Fail-open vs fail-closed for every error code |
| [`logging-schema-v1.md`](logging-schema-v1.md) | **Frozen** log schema |
| [`misuse-matrix-v2.md`](misuse-matrix-v2.md) | 34 misuse vectors and contract responses |
| [`FINAL-HANDOVER-PHASE-4.md`](FINAL-HANDOVER-PHASE-4.md) | Integration handover |

---

## Limitations

- Keyword-density heuristic only — no NLP, no ML
- No authentication or rate limiting (infra responsibility)
- English only
- Scores are not probabilities — do not use for automated enforcement
-0-0-0-0-0