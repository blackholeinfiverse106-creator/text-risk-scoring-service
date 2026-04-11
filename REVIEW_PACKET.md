# REVIEW_PACKET.md — BHIV Sovereign Enforcement Ecosystem

**Author:** Rajaryan Verma  
**System:** Text Risk Scoring / Sovereign Enforcement Gateway  
**Architecture:** 7-Layer Sovereign Decomposition (with RAJYA Validation Engine)  
**Date:** 2026-04-11 (Updated — RAJYA Integration)

---

## 1. ARCHITECTURE OVERVIEW

The BHIV Enforcement Ecosystem is a **7-layer sovereign architecture** where each layer has immutable authority boundaries. No layer may exceed its jurisdiction. The system enforces a **zero-intelligence, deterministic pass-through** enforcement model with **RAJYA** as the sole pre-execution authority gate.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Sūtradhāra Control Plane                         │
│  (Agent Registry + KSML Input Gate + Execution ID Provisioning)
│  File: sutradhara_control_plane.py                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Intelligence Engine                              │
│  (Text risk analysis + Context signal aggregation)         │
│  File: layer0_intelligence.py                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Sarathi Governance Engine                        │
│  (Risk Analysis + DGIC Modifiers + Deterministic Decision) │
│  File: layer1_sarathi.py                                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: DGIC (Deterministic Graph Intelligence Core)     │
│  (Snapshot Ingestion + Seal Verification + Entropy Bounds)  │
│  File: layer3_dgic.py                                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 4a: Enforcement Gate                                │
│  (Pure gate — validates Sarathi + DGIC + execution_id)     │
│  File: layer4_enforcement.py                               │
├─────────────────────────────────────────────────────────────┤
│  ★ RAJYA — Final Authority Validation Engine ★             │
│  (Sole pre-execution gate. No execution without approval.) │
│  File: rajya_validation_engine.py                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 4b: Core Execution Pipeline                         │
│  (Pure execution — acts ONLY on RAJYA verdict)             │
│  File: layer4_core.py                                      │
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
| **Core Execution Ownership** | Core executes `execute_action()` or `block_execution()` based ONLY on RAJYA verdict. Core performs zero validation. |
| **RAJYA Authority Gate** | RAJYA is the sole pre-execution gate. No execution without `EXECUTION_APPROVED`. No intelligence, no governance — pure validation. |
| **Enforcement Gate Passivity** | Enforcement purely gates execution; it does not trigger actions, store data, or orchestrate traces. |
| **Agent Registration** | All agents must be registered with explicit `NO_EXECUTION_RIGHTS`. |

---

## 2. ENTRY POINT

**File:** `app/main.py`  
**Server:** FastAPI (`BHIV Enforcement Gateway`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/enforce/evaluate_action` | POST | Canonical enforcement evaluation |
| `/api/v1/core/invoke_mandala` | POST | Core execution gate (Authority-based Mandala invocation) |
| `/api/v1/bucket/entries` | GET | List bucket entries (external API) |
| `/api/v1/bucket/replay/{trace_hash}` | POST | Replay-verify a specific decision |
| `/api/v1/bucket/replay_all` | POST | Replay-verify entire ledger |

---

## 3. CORE EXECUTION FLOW

### Before RAJYA (Old Architecture)

```
  Sarathi → Enforcement → Core (Core validated enforcement + made decisions)
```

### After RAJYA (Current Architecture)

```
  Sarathi → Enforcement → ★ RAJYA ★ → Core (Core executes ONLY on RAJYA approval)
```

### Sūtradhāra Control Plane → Full Pipeline

```
  KSMLInput
       │
       ▼
  invoke_agent()                     ← sutradhara_control_plane.py
  ├── Validate KSMLInput schema (reject non-KSML)
  ├── verify_agent_capabilities()    (prove NO_EXECUTION_RIGHTS)
  ├── verify_agent()                 (SourceSystem enum match)
  ├── provision_execution_id()       (canonical ID for full pipeline)
  └── Unpack metadata → invoke_mandala()
       │
       ▼
  invoke_mandala()                   ← sutradhara_control_plane.py
  ├── Build EvaluateActionRequest
  ├── DGIC snapshot ingestion        ← layer3_dgic.py (seal verify + freeze)
  ├── compute_intelligence()         ← layer0_intelligence.py (risk + signals)
  ├── Sarathi evaluate_action()      ← layer1_sarathi.py (ALLOW/DENY/ABSTAIN)
  ├── EXECUTION ID GUARD             (mismatch = hard DENY, short-circuit)
  ├── enforce()                      ← layer4_enforcement.py (pure gate)
  │    ├── Validate Sarathi decision exists
  │    ├── Validate execution_id match
  │    ├── Validate DGIC snapshot present
  │    └── Return Dict {execution_id, enforcement_decision, confidence}
  │
  ├── ★ RAJYA VALIDATION ★           ← rajya_validation_engine.py
  │    ├── [LOG] RAJYA VALIDATION START
  │    ├── Rule 1: Sarathi authority missing? → REJECT
  │    ├── Rule 1: Enforcement authority missing? → REJECT
  │    ├── Rule 2: execution_id mismatch? → REJECT
  │    ├── Rule 3: Sarathi != ALLOW? → REJECT
  │    ├── Rule 4: Enforcement != ALLOW? → REJECT
  │    ├── [LOG] RAJYA DECISION (APPROVED or REJECT)
  │    └── Return EXECUTION_APPROVED or REJECT
  │
  ├── [LOG] CORE HANDOFF (only on APPROVED)
  │
  ├── execute_core_mandala()         ← layer4_core.py (PURE EXECUTION)
  │    ├── [LOG] CORE ENTRY (rajya_result logged)
  │    ├── if EXECUTION_APPROVED → execute_action()
  │    │    └── [LOG] CORE EXECUTED
  │    ├── else → block_execution()
  │    │    └── [LOG] CORE BLOCKED
  │    ├── write_execution_record()   ← layer5_bucket.py
  │    ├── [LOG] CORE EXIT
  │    └── Return MandalaInvocationResult
  │
  ├── emit_enforcement_telemetry()   ← layer6_insightbridge.py
  └── Return MandalaInvocationResult
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

**Coverage:** All exit paths in `invoke_mandala()` — including ALLOW, DENY, hard failures, and execution_id mismatches — emit telemetry before returning. **No silent execution is possible.**

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
| **Phase 10** | **RAJYA Validation Engine — sole pre-execution authority gate between Enforcement and Core** | `rajya_validation_engine.py`, `sutradhara_control_plane.py`, `layer4_core.py` |
| **Phase 10a** | **Core stripped of ALL validation — receives only RAJYA verdict, no Sarathi/Enforcement checks** | `layer4_core.py` |
| **Phase 10b** | **Structured proof logging — RAJYA start/decision + Core entry/executed/blocked/exit** | `rajya_validation_engine.py`, `sutradhara_control_plane.py`, `layer4_core.py` |
| **Phase 10c** | **Failure case validation — 12 tests proving all rejections stop at RAJYA, Core never fires** | `test_rajya_failure_cases.py` |

---

## 9. FAILURE CASES

### Pre-RAJYA Failures (short-circuit before RAJYA)

| Case | Trigger | System Response |
|------|---------|----------------|
| **Non-KSML input** | Raw dict or kwargs passed to `invoke_agent()` | `ControlPlaneHardFailure: NON_KSML_INPUT_DETACHED` |
| **Unregistered agent** | Unknown `source_system` string | `AgentVerificationError` — invocation blocked |
| **Agent lacks capability** | Missing `NO_EXECUTION_RIGHTS` | `ControlPlaneHardFailure` — boundary violation |
| **DGIC seal tampered** | `envelope_hash` mismatch | `DGICSnapshotError` → ABSTAIN, pipeline returns before enforcement |
| **Sarathi missing** | `evaluate_action()` returns None | Hard DENY before enforcement/RAJYA, Core never reached |
| **Execution ID mismatch (pre-enforcement)** | Sarathi returns different `execution_id` | Hard DENY, short-circuit before enforcement/RAJYA |
| **Enforcement hard failure** | Missing Sarathi decision or DGIC snapshot | `EnforcementHardFailure` → DENY, RAJYA/Core never reached |

### RAJYA Rejection Cases (Core never executes)

| Case | RAJYA Code | Trigger | Proof |
|------|-----------|---------|-------|
| **Missing Sarathi authority** | `RAJYA_SARATHI_AUTHORITY_MISSING` | `sarathi_decision` is None | `execute_action()` never called |
| **Missing Enforcement authority** | `RAJYA_ENFORCEMENT_AUTHORITY_MISSING` | `enforcement_verdict` is None or not a dict | `execute_action()` never called |
| **Execution ID mismatch** | `RAJYA_EXECUTION_ID_MISMATCH` | Pipeline exec_id ≠ Sarathi exec_id | `execute_action()` never called |
| **Sarathi DENY** | `RAJYA_SARATHI_NOT_ALLOW` | Sarathi decision is DENY or ABSTAIN | `execute_action()` never called |
| **Enforcement DENY** | `RAJYA_ENFORCEMENT_NOT_ALLOW` | Enforcement decision is DENY or ABSTAIN | `execute_action()` never called |

### Post-RAJYA

| Case | Trigger | System Response |
|------|---------|----------------|
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
443 passed in 43.31s
```

Command: `python -m pytest tests/ --tb=short`

### RAJYA Execution Trace Logs (ALLOW path)
```
INFO  RAJYA VALIDATION START | execution_id=exec-001 | sarathi_decision=ALLOW
INFO  RAJYA APPROVED | execution_id=exec-001
INFO  RAJYA DECISION | execution_id=exec-001 | result=EXECUTION_APPROVED | rejection=NONE
INFO  CORE HANDOFF | execution_id=exec-001 | rajya=EXECUTION_APPROVED → Core will execute
INFO  CORE ENTRY | execution_id=exec-001 | rajya_result=EXECUTION_APPROVED
INFO  CORE EXECUTED | execution_id=exec-001 | rajya=EXECUTION_APPROVED
INFO  CORE EXIT | execution_id=exec-001 | decision=ALLOW | rajya=EXECUTION_APPROVED
```

### RAJYA Execution Trace Logs (DENY path — Core never fires)
```
INFO  RAJYA VALIDATION START | execution_id=exec-002 | sarathi_decision=DENY
INFO  RAJYA REJECT: RAJYA_SARATHI_NOT_ALLOW | execution_id=exec-002
INFO  RAJYA DECISION | execution_id=exec-002 | result=REJECT | rejection=RAJYA_SARATHI_NOT_ALLOW
WARN  RAJYA rejected execution | execution_id=exec-002 | code=RAJYA_SARATHI_NOT_ALLOW
→ Core ENTRY never logged. Core EXECUTED never logged. Execution blocked at RAJYA.
```

### RAJYA Validation Proof

| Failure Case | RAJYA Stops? | Core Executes? | Test File |
|-------------|-------------|---------------|----------|
| Sarathi missing | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| Sarathi DENY | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| Sarathi ABSTAIN | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| Enforcement DENY | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| Enforcement ABSTAIN | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| Enforcement missing | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| execution_id mismatch | ✅ REJECT | ❌ Never | `test_rajya_failure_cases.py` |
| ALL valid (ALLOW) | ✅ APPROVED | ✅ Executes | `test_rajya_failure_cases.py` |

### Determinism Proof
Same `trace_hash` on replay confirms byte-identical determinism:
- Original: `8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe`
- Replayed: `8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe`
- Match: `True`

### Core Execution Ownership Proof (Post-RAJYA)
Core no longer validates Sarathi, Enforcement, or any authority decision.
Core receives `rajya_result: RajyaValidationResult` and acts on it:
- **`EXECUTION_APPROVED`:** `execute_action()` triggered
- **`REJECT`:** `block_execution()` triggered (only reached if RAJYA passes through to Core — currently impossible since Sūtradhāra short-circuits)

### Sovereign Boundary Proof
- `MandalaInvocationResult` contains **no** `executed` field — verified by schema inspection
- Core contains **zero validation logic** — receives RAJYA verdict only
- RAJYA is the **sole pre-execution gate** — no code path bypasses it
- Enforcement gate has `NO_EXECUTION_RIGHTS` — verified by registry assertion test
- All terminal paths emit InsightBridge telemetry — verified by 443 passing tests
- Non-KSML input is rejected — verified by `test_sutradhara_control_plane.py`
- Sūtradhāra → DGIC → Intelligence → Sarathi → Enforcement → RAJYA → Core shares strict `execution_id` continuity

---

## 11. FILE MAP

### Core Pipeline
| File | Layer | Purpose |
|------|-------|---------|
| `sutradhara_control_plane.py` | L2 | Agent registry, KSML validation, execution_id provisioning, RAJYA integration |
| `layer0_intelligence.py` | L0 | Text risk analysis, context signal aggregation |
| `layer1_sarathi.py` | L1 | Risk analysis, DGIC modifiers, deterministic governance decision |
| `layer3_dgic.py` | L3 | DGIC snapshot ingestion, seal verification, entropy classification |
| `layer4_enforcement.py` | L4a | Pure enforcement gate (pass-through, no intelligence) |
| `rajya_validation_engine.py` | ★ RAJYA | **Sole pre-execution authority gate** — validates Sarathi + Enforcement + execution_id |
| `layer4_core.py` | L4b | **Pure execution** — acts ONLY on RAJYA verdict, zero validation |
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
| `enforcement_schemas.py` | Pydantic models: `KSMLInput`, `EvaluateActionRequest`, `ExecuteActionResponse`, `MandalaInvocationResult` |
| `contract_enforcement.py` | Contract enforcement rules |

### RAJYA Test Coverage
| File | Tests | Purpose |
|------|-------|---------|
| `test_rajya_validation_engine.py` | 23 | Unit tests: all 4 REJECT paths, APPROVED path, rule priority, enum/dataclass integrity |
| `test_rajya_failure_cases.py` | 12 | Failure case validation: proves Core never executes on RAJYA rejection |
