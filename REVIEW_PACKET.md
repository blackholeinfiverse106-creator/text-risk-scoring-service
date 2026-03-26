# REVIEW_PACKET.md — BHIV Enforcement Gateway

**Author:** Rajaryan Verma  
**System:** Text Risk Scoring / Enforcement Gateway  
**Layers:** Layer 1 (Governance) + Layer 4 (Execution)  
**Date:** 2026-03-26

---

## 1. ENTRY POINT

**File:** `app/main.py`  
**Server:** FastAPI (`BHIV Enforcement Gateway`)

All enforcement actions enter via HTTP endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/enforce/evaluate_action` | POST | Canonical enforcement evaluation |
| `/api/v1/core/submit_proposal` | POST | Core execution gate (submit → evaluate → execute) |
| `/api/v1/bucket/entries` | GET | List bucket ledger entries |
| `/api/v1/bucket/replay/{trace_hash}` | POST | Replay-verify a specific decision |
| `/api/v1/bucket/replay_all` | POST | Replay-verify entire ledger |

---

## 2. CORE EXECUTION FLOW (3 files)

### File 1: `app/enforcement_gate.py` — Enforcement Entry
- Receives `EvaluateActionRequest` (action_id, actor, proposed_action, context_signals, dgic_epistemic_state, source_system)
- Ingests DGIC snapshot → verifies cryptographic seal → classifies entropy boundary
- Analyzes proposed action text for risk
- Aggregates context signals deterministically (InsightBridge / Marine / AIAIC / C4S adapters)
- Produces `EvaluateActionResponse` with decision: `ALLOW` / `DENY` / `ABSTAIN`
- Writes to in-memory ledger AND persistent bucket ledger
- Computes SHA-256 `trace_hash` for replay verification

### File 2: `app/core_execution_gate.py` — Decision Intake + Execution Layer
- Receives `CoreActionProposal` from any BHIV system
- Calls `enforcement_gate.evaluate_action()`
- Maps gate decision to Core output:
  - `ALLOW` → execute
  - `DENY` (high risk) → `BLOCK`
  - `DENY` (ambiguous) → `ESCALATE`
  - `ABSTAIN` (unknown state) → `REQUEST_MORE_DATA`
  - `ABSTAIN` (seal failure) → `BLOCK`
- Sets `executed = True` ONLY on `ALLOW`
- Returns `CoreExecutionResult` with `execution_id` = `proposal_id`

### File 3: `app/bucket_ledger.py` — Persistent Action Record
- Appends each decision to `data/enforcement_bucket.jsonl`
- Each entry contains:
  - `bucket_id` (UUID)
  - `action_id`
  - `input_snapshot_hash` (SHA-256 of ALL inputs)
  - `decision`, `risk_score`, `confidence`, `failure_reason`
  - `trace_hash` (deterministic replay key)
  - `trace_lineage` (previous `bucket_id` → current, or `GENESIS`)
  - `replay_proof` (SHA-256 of full entry for tamper detection)

---

## 3. LIVE FLOW

```
DGIC Epistemic State
      │
      ▼
 ingest_dgic_snapshot()          ← app/dgic_snapshot_consumer.py
 (seal verify, entropy classify, freeze snapshot)
      │
      ▼
 evaluate_action()               ← app/enforcement_gate.py
 (risk analysis + signal aggregation + deterministic decision)
      │
      ├── record_decision()      ← app/enforcement_ledger.py (in-memory)
      └── write_bucket_entry()   ← app/bucket_ledger.py (persistent JSONL)
      │
      ▼
 submit_proposal()               ← app/core_execution_gate.py
 (map gate decision → Core output → execute only on ALLOW)
      │
      ▼
 verify_bucket_entry()           ← app/replay_verifier.py
 (re-evaluate stored payload → prove byte-identical outcome)
```

### Real Execution Example

**Input:**
```json
{
  "proposal_id": "PROOF-001",
  "actor": "review-agent",
  "proposed_action": "Generate compliance report",
  "source_system": "MARINE_INTELLIGENCE",
  "dgic_epistemic_state": {
    "epistemic_state": "KNOWN",
    "entropy_score": 0.15,
    "contradiction_flag": false
  },
  "context_signals": [
    {"signal_id": "sig-1", "source": "MARINE_INTELLIGENCE", "signal_type": "weather_anomaly", "value": 0.4}
  ]
}
```

**Output:**
```json
{
  "proposal_id": "PROOF-001",
  "execution_decision": "ALLOW",
  "executed": true,
  "risk_score": 0.4,
  "confidence": 1.0,
  "failure_reason": null,
  "trace_hash": "8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe",
  "gate_decision": "ALLOW"
}
```

**Trace:**
- Ledger: `action_id=PROOF-001 decision=ALLOW trace_hash=8b86fa098ee8e96d...`
- Bucket: `bucket_id=84dd8d9f... lineage=GENESIS replay_proof=a1641cc65ef03c19...`
- Replay: `match=True replay_proof_valid=True original=ALLOW replayed=ALLOW`

---

## 4. WHAT YOU BUILT

| Phase | What Changed | Files |
|-------|-------------|-------|
| Phase 2 | Canonical `/evaluate_action` API with strict Pydantic schemas | `enforcement_schemas.py`, `enforcement_gate.py`, `main.py` |
| Phase 3 | Formal DGIC snapshot ingestion with seal verification, entropy classification, immutability freeze | `dgic_snapshot_consumer.py`, `enforcement_gate.py` |
| Phase 4 | InsightBridge signal weighted aggregation (security_alert 1.0, policy_violation 0.8, etc.) | `insightbridge_rules.py`, `enforcement_gate.py` |
| Phase 5 | Core execution gate: submit → evaluate → map → execute only on ALLOW. Added BLOCK/ESCALATE/REQUEST_MORE_DATA | `core_execution_gate.py`, `enforcement_schemas.py`, `main.py` |
| Phase 6 | Persistent bucket ledger (JSONL), input snapshot hashing, trace lineage chain, replay verification tool | `bucket_ledger.py`, `replay_verifier.py`, `enforcement_gate.py`, `main.py` |
| Phase 7 | Marine/AIAIC/C4S signal adapters with deterministic weighting | `marine_rules.py`, `aiaic_rules.py`, `c4s_rules.py`, `enforcement_gate.py` |

---

## 5. FAILURE CASES

| Case | Trigger | System Response |
|------|---------|----------------|
| **DGIC seal tampered** | `envelope_hash` does not match recomputed hash | `ABSTAIN` → Core maps to `BLOCK`. Logged as `DGIC_SEAL_VERIFICATION_FAILED` |
| **CRITICAL entropy** | `entropy_score >= 0.7` | `DENY` with reason `CRITICAL entropy boundary`. Core maps to `BLOCK` |
| **AMBIGUOUS epistemic state** | `epistemic_state = AMBIGUOUS` + medium risk | `DENY` with reason `AMBIGUOUS epistemic uncertainty`. Core maps to `ESCALATE` |
| **UNKNOWN epistemic state** | `epistemic_state = UNKNOWN` | `ABSTAIN` with reason `no grounded evidence`. Core maps to `REQUEST_MORE_DATA` |
| **High risk score** | `risk_score >= 0.7` | `DENY` with structured failure reason. Core maps to `BLOCK` |
| **Snapshot integrity violation** | Snapshot fields mutated during processing | `DGICSnapshotError` raised. Decision aborted |
| **Bucket replay proof invalid** | Stored entry data tampered after write | `replay_proof_valid = False` when replaying |
| **Invalid source system** | Unknown `source_system` string | Pydantic validation rejects request with 422 |

---

## 6. PROOF

### Execution Trace
```
=== CORE EXECUTION RESULT ===
{
  "proposal_id": "PROOF-001",
  "execution_decision": "ALLOW",
  "executed": true,
  "risk_score": 0.4,
  "confidence": 1.0,
  "failure_reason": null,
  "trace_hash": "8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe",
  "gate_decision": "ALLOW"
}

=== LEDGER ENTRIES: 1 ===
  action_id=PROOF-001 decision=ALLOW trace_hash=8b86fa098ee8e96d...

=== BUCKET ENTRIES: 1 ===
  bucket_id=84dd8d9f... action_id=PROOF-001 decision=ALLOW lineage=GENESIS replay_proof=a1641cc65ef03c19...

=== REPLAY VERIFICATION ===
  match=True
  replay_proof_valid=True
  original=ALLOW replayed=ALLOW
```

### Test Suite
```
395 passed in 25.02s
```

Command: `python -m pytest tests/ --tb=short`

### Determinism Proof
Same `trace_hash` on replay confirms byte-identical determinism:
- Original: `8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe`
- Replayed: `8b86fa098ee8e96df393042370e65cf5fe51734cdc6578d3501c3eba7bb90bbe`
- Match: `True`
