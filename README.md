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

### `POST /api/v1/aggregate/unified`

Multi-signal aggregation endpoint. Accepts 1–32 typed signals, returns an InsightBridge-compatible payload with DGIC envelope and telemetry.

**Request:**
```json
{
  "signals": [
    {
      "signal_id": "sig-001",
      "signal_type": "POLICY_VIOLATION_SIGNAL",
      "base_risk_score": 0.9,
      "base_confidence_score": 1.0,
      "dgic_envelope": {
        "version": "schema_v1",
        "lineage_hash": "<SHA-256>",
        "envelope_hash": "<SHA-256>",
        "payload": {
          "epistemic_state": "KNOWN",
          "entropy_score": 0.0,
          "contradiction_flag": false
        }
      }
    }
  ]
}
```

**Signal types & weights:**

| Type | Weight |
|---|---|
| `POLICY_VIOLATION_SIGNAL` | 1.5 |
| `BEHAVIOR_ANOMALY_SIGNAL` | 1.2 |
| `TEXT_RISK_SIGNAL` | 1.0 |
| `EXTERNAL_DETECTOR_SIGNAL` | 0.8 |

**Response** includes `aggregated_risk_score`, `epistemic_confidence`, `dgic_envelope` (with `collapse_state`), and `telemetry` sidecar.

Full integration guide: see [`SYSTEM_INTEGRATION_GUIDE.md`](SYSTEM_INTEGRATION_GUIDE.md).

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

## Sovereign Layer Architecture

> **You are here → Layer 4 — Core Execution (Raj Prajapati)**

```
┌─────────────────────────────────────────────────────────────┐
│                    BHIV Enforcement Ecosystem                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Layer 2: Sūtradhāra Control Plane                  │    │
│  │  (Agent Registry + Routing)                         │    │
│  │  File: sutradhara_control_plane.py                  │    │
│  └──────────────────┬──────────────────────────────────┘    │
│                     │                                       │
│                     ▼                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Layer 1: Sarathi Governance (Aakanksha Parab)      │    │
│  │  FINAL decision authority: ALLOW / DENY / ABSTAIN   │    │
│  │  File: layer1_sarathi.py                            │    │
│  └──────────────────┬──────────────────────────────────┘    │
│                     │                                       │
│         ┌───────────┼──────────────┐                        │
│         ▼                          ▼                        │
│  ┌──────────────┐    ┌─────────────────────────────────┐    │
│  │  Layer 3:    │    │  Layer 4: Enforcement Gate      │    │
│  │  DGIC        │    │  Pure sovereign gate            │    │
│  │  (Pritesh)   │───▶│  ALLOW / DENY / ABSTAIN only   │    │
│  │  Epistemic   │    │  File: layer4_enforcement.py    │    │
│  │  reasoning   │    └──────────────┬──────────────────┘    │
│  │  NO execution│                   │                       │
│  │  layer3_dgic │                   ▼                       │
│  │  .py         │    ┌─────────────────────────────────┐    │
│  └──────────────┘    │  Layer 4: Core Execution ★      │    │
│                      │  (Raj Prajapati — YOU)           │    │
│                      │  Owns: execution + bucket writes │    │
│                      │  File: layer4_core.py            │    │
│                      └──────────────┬──────────────────┘    │
│                                     │                       │
│                     ┌───────────────┼──────────────┐        │
│                     ▼                              ▼        │
│  ┌──────────────────────────┐  ┌───────────────────────┐    │
│  │  Layer 5: Bucket         │  │  Layer 6: InsightBridge│   │
│  │  (Siddhesh Narkar)       │  │  (Vijay Dhawan)       │    │
│  │  Immutable storage       │  │  Telemetry emission   │    │
│  │  via API only            │  │  layer6_insightbridge │    │
│  │  layer5_bucket.py        │  │  .py                  │    │
│  └──────────────────────────┘  └───────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer Map

| Layer | Name | File | Owner | Responsibility |
|---|---|---|---|---|
| **1** | Sarathi Governance | `app/layer1_sarathi.py` | Aakanksha Parab | FINAL decision (ALLOW / DENY / ABSTAIN) |
| **2** | Sūtradhāra Control Plane | `app/sutradhara_control_plane.py` | Sūtradhāra Team | Agent registry + routing |
| **3** | DGIC Epistemic | `app/layer3_dgic.py` | Pritesh Patra | Epistemic reasoning (no execution) |
| **4** | Enforcement Gate | `app/layer4_enforcement.py` | *(pure gate)* | Sovereign compliance validation |
| **4** | **Core Execution** | `app/layer4_core.py` | **Raj Prajapati** | **Executes approved actions ONLY** |
| **5** | Bucket Ledger | `app/layer5_bucket.py` | Siddhesh Narkar | Immutable storage via API |
| **6** | InsightBridge | `app/layer6_insightbridge.py` | Vijay Dhawan | Telemetry emission |
| — | KSML | `app/enforcement_schemas.py` | Tanvi | Structured input/output contracts |

---

## Integration Block

| Role | Owner | System Interaction |
|---|---|---|
| **Sarathi** | Aakanksha Parab | Provides FINAL governance decision. All layers depend on this. |
| **Core** | Raj Prajapati | Executes approved actions ONLY. Owns execution mapping + bucket writes. |
| **DGIC** | Pritesh Patra | Provides epistemic reasoning. No execution authority. |
| **Bucket** | Siddhesh Narkar | Immutable storage via external API. Only Core writes to it. |
| **InsightBridge** | Vijay Dhawan | Telemetry emission. Observability only. |
| **KSML** | Tanvi | Structured input/output contract (schemas). |
| **Sūtradhāra** | Agent Registry | All agents must be registered + visible. |

---

## Enforcement Gate Compliance (Sovereign Core Law)

The Enforcement Gate (`layer4_enforcement.py`) is a **pure, zero-intelligence gate**:

| Rule | Status |
|---|---|
| Does NOT think | ✅ |
| Does NOT decide beyond enforcement | ✅ |
| Does NOT own execution | ✅ |
| Does NOT write to Bucket | ✅ |
| HARD FAILS without Sarathi decision | ✅ |
| HARD FAILS without DGIC snapshot | ✅ |
| Returns ONLY ALLOW / DENY / ABSTAIN + reasoning | ✅ |

---

## Pipeline Flow

```
Agent Request
  → Sūtradhāra (verify agent, provision execution_id)
    → Core (build request)
      → Sarathi (governance decision: ALLOW/DENY/ABSTAIN)
        → Enforcement Gate (validate sovereign compliance)
      ← Core (map verdict → executed flag)
      → Bucket (record decision — Core writes, not enforcement)
    ← MandalaInvocationResult
```

---

## Architecture (Service Endpoints)

```
POST /analyze                        POST /api/v1/aggregate/unified
     │                                    │
     ├─ validate_input_contract()         ├─ Core Adapter (schema validation)
     ├─ analyze_text()                    ├─ Multi-Signal Aggregator
     ├─ validate_output_contract()        │   ├─ Per-signal DGIC scoring
     └─ Return response                  │   ├─ Weighted mean + penalty
                                          │   └─ Bounded [0.0, 1.0]
POST /api/v1/sutradhara/invoke           ├─ DGIC Enforcement Bridge
     │                                    ├─ InsightBridge Telemetry
     ├─ Sūtradhāra (agent verify)        └─ Return enriched payload
     ├─ Core (invoke_mandala)
     │   ├─ Sarathi governance
     │   ├─ Enforcement gate
     │   ├─ Bucket recording
     │   └─ MandalaInvocationResult
     └─ Return result
```

No database. No cache. Bucket writes via external API. Fully sovereign-compliant.

---

## Proofs & Certification

| Proof | Command | Result |
|---|---|---|
| Engine determinism | `python replay_harness.py` | 150k runs, 0 divergences |
| Aggregator determinism | `pytest tests/test_deterministic_signal_replay.py` | 7k runs, 0 divergences |
| Thread safety | `python thread_safety_proof.py` | 200 threads, 0 divergences |
| Error propagation | `python error-propagation-proof.py` | 9/9 paths verified |
| Trace lineage | `python trace-lineage-demo.py` | 3/3 proven, 0 bleed |
| Misuse resistance | `python -m pytest decision-injection-tests/ escalation-tests/` | 67 tests pass |
| Sovereign compliance | `python -m pytest tests/ -v` | 407 tests pass |

---

## Key Documents

| Document | Purpose |
|---|---|
| [`contracts-v3.md`](contracts-v3.md) | **Frozen** API contract |
| [`invariants-v2.md`](invariants-v2.md) | 14 revalidated invariants |
| [`fail-mode-matrix.md`](fail-mode-matrix.md) | Fail-open vs fail-closed for every error code |
| [`logging-schema-v1.md`](logging-schema-v1.md) | **Frozen** log schema |
| [`misuse-matrix-v2.md`](misuse-matrix-v2.md) | 34 misuse vectors and contract responses |
| [`MULTI_SIGNAL_AGGREGATOR_ARCHITECTURE.md`](MULTI_SIGNAL_AGGREGATOR_ARCHITECTURE.md) | Multi-signal aggregator design |
| [`SYSTEM_INTEGRATION_GUIDE.md`](SYSTEM_INTEGRATION_GUIDE.md) | Integration guide for DGIC, Core, InsightBridge |
| [`DETERMINISM_PROOF.md`](DETERMINISM_PROOF.md) | Aggregator determinism proof (7k executions) |
| [`FINAL-HANDOVER-PHASE-4.md`](FINAL-HANDOVER-PHASE-4.md) | Integration handover |

---

## Limitations

- Keyword-density heuristic only — no NLP, no ML
- No authentication or rate limiting (infra responsibility)
- English only
- Scores are not probabilities — do not use for automated enforcement