# REVIEW_PACKET.md — BHIV Sovereign Enforcement Ecosystem

**Author:** Rajaryan Verma  
**System:** Text Risk Scoring / Sovereign Enforcement Gateway  
**Architecture:** 6-Layer Sovereign Decomposition  
**Date:** 2026-04-03 (Updated)

---

## 1. ARCHITECTURE OVERVIEW

The BHIV Enforcement Ecosystem is a **6-layer sovereign architecture** where each layer has immutable authority boundaries. No layer may exceed its jurisdiction. The system enforces a **zero-intelligence, deterministic pass-through** enforcement model.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Sūtradhāra Control Plane                         │
│  (Agent Registry + KSML Input Gate + Execution ID Provisioning)
│  File: sutradhara_control_plane.py                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Sarathi Governance Engine                        │
│  (Risk Analysis + DGIC Modifiers + Deterministic Decision) │
│  File: layer1_sarathi.py                                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: DGIC (Deterministic Graph Intelligence Core)     │
│  (Snapshot Ingestion + Seal Verification + Entropy Bounds)  │
│  File: layer3_dgic.py                                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Core Execution Pipeline + Enforcement Gate       │
│  (Submit → Evaluate → Enforce → Record → Emit)             │
│  Files: layer4_core.py, layer4_enforcement.py              │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Bucket (External API Persistence)                │
│  (Zero local state — all writes via external API)          │
│  File: layer5_bucket.py                                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: InsightBridge (Telemetry + Signal Aggregation)   │
│  (Enforcement telemetry emission — no silent execution)    │
│  File: layer6_insightbridge.py                             │
└─────────────────────────────────────────────────────────────┘
```

### Sovereign Core Laws

| Law | Enforcement |
|-----|-------------|
| **Zero Local State** | All persistence via external Bucket API. No in-memory ledger. |
| **No Silent Execution** | Every terminal decision emits InsightBridge telemetry. |
| **Execution ID Continuity** | A single `execution_id` propagates end-to-end. Mismatch = hard fail. |
| **KSML-Only Input** | All perimeter input must be a valid `KSMLInput` schema. Raw kwargs rejected. |
| **Core Execution Ownership** | Core executes `execute_action()` or `block_execution()` explicitly based on Enforcement payload. |
| **Enforcement Gate Passivity** | Enforcement purely gates execution; it does not trigger actions, store data, or orchestrate traces. |
| **Agent Registration** | All agents must be registered with explicit `NO_EXECUTION_RIGHTS`. |

---

## 2. ENTRY POINT

**File:** `app/main.py`  
**Server:** FastAPI (`BHIV Enforcement Gateway`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/enforce/evaluate_action` | POST | Canonical enforcement evaluation |
| `/api/v1/core/submit_proposal` | POST | Core execution gate (submit → evaluate → enforce → record → emit) |
| `/api/v1/bucket/entries` | GET | List bucket entries (external API) |
| `/api/v1/bucket/replay/{trace_hash}` | POST | Replay-verify a specific decision |
| `/api/v1/bucket/replay_all` | POST | Replay-verify entire ledger |

---

## 3. CORE EXECUTION FLOW

### Sūtradhāra Control Plane → Core Pipeline

```
  KSMLInput (Phase 6)
       │
       ▼
  invoke_agent()                    ← sutradhara_control_plane.py
  ├── Validate KSMLInput schema (reject non-KSML)
  ├── verify_agent_capabilities()   (Phase 7: prove NO_EXECUTION_RIGHTS)
  ├── verify_agent()                (SourceSystem enum match)
  ├── provision_execution_id()      (canonical ID for full pipeline)
  └── Unpack metadata → submit_proposal()
       │
       ▼
  submit_proposal()                 ← layer4_core.py
  ├── Build EvaluateActionRequest
  ├── Sarathi evaluate_action()     ← layer1_sarathi.py (Layer 1 governance)
  │    ├── ingest_dgic_snapshot()   ← layer3_dgic.py (seal verify + freeze)
  │    ├── adapt_dgic()             (epistemic state → scoring modifiers)
  │    ├── analyze_text()           (keyword risk scoring)
  │    ├── aggregate_context_signals() (InsightBridge/Marine/AIAIC/C4S)
  │    └── Return SarathiEvaluateResponse (ALLOW/DENY/ABSTAIN)
  ├── EXECUTION ID GUARD            (Phase 4: mismatch = hard DENY)
  ├── enforce()                     ← layer4_enforcement.py (pure gate)
  │    ├── Validate Sarathi decision exists
  │    ├── Validate execution_id match
  │    ├── Validate DGIC snapshot present
  │    └── Return Dict {execution_id, enforcement_decision, confidence}
  ├── evaluate gate output          (Phase 9: Real Execution Boundary)
  │    ├── If ALLOW → execute_action()
  │    └── If DENY or ABSTAIN → block_execution()
  ├── write_execution_record()      ← layer5_bucket.py (external API only)
  ├── emit_enforcement_telemetry()  ← layer6_insightbridge.py (Phase 5)
  └── Return CoreExecutionResult
```

---

## 4. CLEAN DECISION CONTRACT (Phase 8)

The **final enforcement output** is strictly shaped. No execution flags. No action triggers.

```json
{
  "execution_id": "exec-abc123def456",
  "enforcement_decision": "ALLOW",
  "risk_score": 0.0,
  "confidence": 1.0,
  "trace_hash": "8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe",
  "failure_reason": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | `str` | Global unique execution identifier, propagated end-to-end |
| `enforcement_decision` | `ALLOW \| DENY \| ABSTAIN` | The deterministic terminal gate decision |
| `risk_score` | `float [0.0, 1.0]` | Final computed risk score from Sarathi |
| `confidence` | `float [0.0, 1.0]` | Decision confidence, scaled by epistemic state |
| `trace_hash` | `str (64 chars)` | SHA-256 of all inputs — deterministic replay key |
| `failure_reason` | `str \| null` | Null on ALLOW. Structured reason on DENY/ABSTAIN |

**Prohibited fields:** `executed`, `gate_decision`, `action_trigger`, `execution_flag`.

---

## 5. KSML INPUT SCHEMA (Phase 6)

All perimeter input must conform to the KSML canonical envelope:

```json
{
  "execution_id": "exec-abc123def456",
  "structured_signals": [
    {"signal_id": "sig-1", "signal_type": "weather_anomaly", "value": 0.4, "source": "MARINE_INTELLIGENCE"}
  ],
  "metadata": {
    "actor": "review-agent",
    "proposed_action": "Generate compliance report",
    "source_system": "MARINE_INTELLIGENCE",
    "dgic_epistemic_state": {
      "epistemic_state": "KNOWN",
      "entropy_score": 0.15,
      "contradiction_flag": false,
      "lineage_hash": "a1b2c3...64chars",
      "envelope_hash": "d4e5f6...64chars"
    }
  }
}
```

**Validation:** The `metadata` block **must** contain `actor`, `proposed_action`, `source_system`, and `dgic_epistemic_state`. Missing fields trigger immediate `KSMLSchemaViolation`.

---

## 6. SŪTRADHĀRA AGENT REGISTRY (Phase 7)

| Agent ID | Capability | Permissions |
|----------|-----------|-------------|
| `enforcement_gate_v1` | `enforcement_gate` | `READ_ONLY`, `NO_EXECUTION_RIGHTS`, `NO_SYSTEM_ACCESS` |

**Proof of boundary:** Before every invocation, `verify_agent_capabilities()` asserts that the agent holds `NO_EXECUTION_RIGHTS`. Failure raises `ControlPlaneHardFailure`.

---

## 7. INSIGHTBRIDGE TELEMETRY (Phase 5)

Every terminal enforcement decision emits structured telemetry via `emit_enforcement_telemetry()`:

```json
{
  "event_type": "insightbridge_enforcement_emission",
  "execution_id": "exec-abc123def456",
  "enforcement_decision": "ALLOW",
  "risk_score": 0.0,
  "confidence": 1.0,
  "trace_hash": "8b86fa098ee8e96d..."
}
```

**Coverage:** All exit paths in `submit_proposal()` — including ALLOW, DENY, hard failures, and execution_id mismatches — emit telemetry before returning. **No silent execution is possible.**

---

## 8. PHASE HISTORY

| Phase | What Changed | Key Files |
|-------|-------------|-----------|
| Phase 1–2 | Canonical `/evaluate_action` API with strict Pydantic schemas | `enforcement_schemas.py`, `main.py` |
| Phase 3 | Bucket decoupled — in-memory ledger removed, external API persistence only | `layer5_bucket.py`, `layer4_core.py` |
| Phase 4 | Execution ID boundary enforcement — mismatch = hard fail | `layer4_enforcement.py`, `layer4_core.py`, `sutradhara_control_plane.py` |
| Phase 5 | InsightBridge telemetry emission — no silent execution | `layer6_insightbridge.py`, `layer4_core.py` |
| Phase 6 | KSML input compliance — raw inputs rejected, strict schema enforced | `enforcement_schemas.py`, `sutradhara_control_plane.py` |
| Phase 7 | Sūtradhāra agent registration — capabilities proven before invocation | `sutradhara_control_plane.py` |
| Phase 8 | Clean Decision Contract — `executed` flag removed, strict enforcement dict payload | `layer4_core.py`, `enforcement_schemas.py`, `layer4_enforcement.py` |
| Phase 9 | Core Execution Ownership — `execute_action()` / `block_execution()` explicitly directed by Core | `layer4_core.py` |

---

## 9. FAILURE CASES

| Case | Trigger | System Response |
|------|---------|----------------|
| **Non-KSML input** | Raw dict or kwargs passed to `invoke_agent()` | `ControlPlaneHardFailure: NON_KSML_INPUT_DETACHED` |
| **Unregistered agent** | Unknown `source_system` string | `AgentVerificationError` — invocation blocked |
| **Agent lacks capability** | Missing `NO_EXECUTION_RIGHTS` | `ControlPlaneHardFailure` — boundary violation |
| **Execution ID mismatch** | Sarathi returns different `execution_id` | Hard `DENY` with structured failure reason + telemetry emission |
| **DGIC seal tampered** | `envelope_hash` does not match recomputed hash | Sarathi `ABSTAIN` → Core `ABSTAIN` with failure reason |
| **CRITICAL entropy** | `entropy_score >= 0.7` | Sarathi `DENY` — action denied as fail-safe |
| **AMBIGUOUS + elevated risk** | `epistemic_state = AMBIGUOUS` + `risk >= 0.3` | Sarathi `DENY` — cannot allow under epistemic uncertainty |
| **UNKNOWN epistemic state** | `epistemic_state = UNKNOWN` | Sarathi `ABSTAIN` → Core `ABSTAIN` — no grounded evidence |
| **High risk score** | `risk_score >= 0.7` | Sarathi `DENY` with structured failure reason |
| **Sarathi missing** | Failure in governance processing | Core throws `System Rejected` before enforcement |
| **Enforcement missing / Invalid** | Decision dict corrupted or non-dict | Core throws `Core Rejected: Invalid/Missing enforcement output` |
| **Enforcement hard failure** | Missing Sarathi decision or DGIC snapshot | `EnforcementHardFailure` raised, Core blocks action, Core returns `DENY` |
| **Control Plane ID corruption** | Core returns different `execution_id` than provisioned | `ControlPlaneHardFailure: EXECUTION_ID_CORRUPTION` |

---

## 10. PROOF

### Clean Decision Contract Output
```json
{
  "execution_id": "PROOF-001",
  "enforcement_decision": "ALLOW",
  "risk_score": 0.0,
  "confidence": 1.0,
  "trace_hash": "8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe",
  "failure_reason": null
}
```

### Test Suite
```
408 passed in 64s
```

Command: `python -m pytest tests/ --tb=short`

### Determinism Proof
Same `trace_hash` on replay confirms byte-identical determinism:
- Original: `8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe`
- Replayed: `8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe`
- Match: `True`

### Real Execution Ownership Proof
Core actively converts the zero-intelligence Gate response (`ALLOW`/`DENY`/`ABSTAIN`) into real-world mapping via explicitly triggering pipeline endpoints:
- **`ALLOW`:** Outputs `Actions: [EXECUTE_ACTION] triggered`
- **`DENY` / `ABSTAIN`:** Outputs `Actions: [BLOCK_EXECUTION] triggered`

### Sovereign Boundary Proof
- `CoreExecutionResult` contains **no** `executed` field — verified by schema inspection
- `ExecuteActionResponse` contains **no** `executed` field — verified by schema inspection
- Enforcement gate has `NO_EXECUTION_RIGHTS` — verified by registry assertion test
- All terminal paths emit InsightBridge telemetry — verified by 408 passing tests
- Non-KSML input is rejected — verified by `test_sutradhara_control_plane.py`
- Sūtradhāra → DGIC → Sarathi → Enforcement → Core shares strict `execution_id` continuity — mismatch abruptly halts execution

---

## 11. FILE MAP

### Core Pipeline
| File | Layer | Purpose |
|------|-------|---------|
| `sutradhara_control_plane.py` | L2 | Agent registry, KSML validation, execution_id provisioning |
| `layer1_sarathi.py` | L1 | Risk analysis, DGIC modifiers, deterministic governance decision |
| `layer3_dgic.py` | L3 | DGIC snapshot ingestion, seal verification, entropy classification |
| `layer4_core.py` | L4 | Core submission pipeline, enforcement orchestration |
| `layer4_enforcement.py` | L4 | Pure enforcement gate (pass-through, no intelligence) |
| `layer5_bucket.py` | L5 | External API persistence (zero local state) |
| `layer6_insightbridge.py` | L6 | Telemetry emission, signal aggregation |

### Signal Adapters
| File | Purpose |
|------|---------|
| `insightbridge_rules.py` | InsightBridge weighted signal calculation |
| `marine_rules.py` | Marine Intelligence signal weighting |
| `aiaic_rules.py` | AIAIC Agricultural Intelligence signal weighting |
| `c4s_rules.py` | C4S Strategic Simulation signal weighting |

### Schemas & Contracts
| File | Purpose |
|------|---------|
| `enforcement_schemas.py` | Pydantic models: `KSMLInput`, `EvaluateActionRequest`, `ExecuteActionResponse`, `CoreExecutionResult` |
| `contract_enforcement.py` | Contract enforcement rules |
