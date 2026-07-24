# BHIV Enforcement Gateway - API Integration Guide

This document provides a comprehensive integration guide for the **BHIV Enforcement Gateway**, detailing all endpoints, their interactions, execution flow, and exact payload formats passing through all phases of the pipeline.

---

## 1. End-to-End Pipeline Overview (Where it Starts and Ends)

The system operates as a multi-layered enforcement pipeline that receives intelligence signals, aggregates them, runs them through a control plane, secures governance approval, and strictly enforces execution.

### Execution Flow:
1. **Signal Collection (Layer 0 & 3):** An external system sends text or signals to `/analyze` or `/api/v1/dgic/ingest` for base analysis and Epistemic (DGIC) modifications.
2. **Signal Aggregation (Layer 6):** Multiple signals are compiled and aggregated deterministically via `/api/v1/aggregate/unified` to produce a single risk profile without hallucinating authority.
3. **Control Plane Invocation (Layer 2):** The actor formally proposes an action through the Sūtradhāra edge via `/api/v1/sutradhara/invoke`. Sūtradhāra authenticates the agent and initiates the KSML payload.
4. **Rajya Validation (Layer 1):** The proposed action is sent to `/api/v1/rajya/validate`. Rajya makes the executive governance decision (e.g., `EXECUTION_APPROVED`).
5. **Sarathi Token Generation & Enforcement (Layer 1 & 4):** 
   - A deterministic Sarathi Enforcement Token is minted upon Rajya's approval.
   - The token is submitted to `/sarathi/enforce`. 
   - If valid, Sarathi acts as a pure gate, permitting core execution (ALLOW) and minting a JWT for secure downstream communication.
6. **Execution & Ledger (Layer 5):** Core executes the action and immutably logs the decision trace in the bucket ledger. Bucket endpoints (`/api/v1/bucket/entries`) can be used to audit or replay the trace hash.

---

## 2. Signal Analysis & Ingestion

### 2.1 Basic Text Analysis
**Endpoint:** `POST /analyze`
**Purpose:** Base layer text analysis without epistemic weighting. Applies contract enforcement (Layer 0).

**Request Payload (`InputSchema`):**
```json
{
  "text": "The proposed action text to analyze for risk."
}
```

**Response Payload (`OutputSchema`):**
```json
{
  "risk_score": 0.15,
  "risk_category": "LOW",
  "trigger_reasons": [],
  "confidence_score": 0.85,
  "processed_length": 45,
  "safety_metadata": {
    "is_decision": false,
    "authority": "NONE",
    "actionable": false
  }
}
```

### 2.2 DGIC Ingestion
**Endpoint:** `POST /api/v1/dgic/ingest`
**Purpose:** Analyzes text but immediately applies Epistemic (DGIC) modifiers based on the provided epistemic envelope.

**Request Payload (`DGICIngestRequest`):**
```json
{
  "text": "Deploy secondary thrusters.",
  "dgic_envelope": {
    "version": "schema_v1",
    "payload": {
      "epistemic_state": "KNOWN",
      "entropy_score": 0.1,
      "contradiction_flag": false
    },
    "collapse_flag": false,
    "lineage_hash": "64-character-sha256-hash-here...",
    "evidence_hash": "64-character-sha256-hash-here..."
  }
}
```

**Response Payload:** Returns `OutputSchema` but with risk and confidence scores algorithmically modified by the DGIC engine (e.g., abstaining if epistemic state is UNKNOWN).

---

## 3. Signal Aggregation (InsightBridge Layer 6)

### 3.1 Unified Signal Aggregation
**Endpoint:** `POST /api/v1/aggregate/unified`
**Purpose:** Aggregates multiple unified signals across different types (Text, Behavior, Policy, External) into a single deterministic enforcement-grade signal.

**Request Payload (`UnifiedAggregateRequest`):**
```json
{
  "signals": [
    {
      "signal_id": "sig-001",
      "signal_type": "TEXT_RISK_SIGNAL",
      "base_risk_score": 0.6,
      "base_confidence_score": 0.9,
      "dgic_envelope": {
        "version": "schema_v1",
        "payload": {
          "epistemic_state": "KNOWN",
          "entropy_score": 0.2,
          "contradiction_flag": false
        },
        "collapse_flag": false,
        "lineage_hash": "64-character-sha256-hash",
        "evidence_hash": "64-character-sha256-hash"
      }
    }
  ]
}
```

**Response Payload (InsightBridge Contract):**
```json
{
  "aggregate_risk_score": 0.6,
  "aggregate_risk_category": "MEDIUM",
  "aggregate_confidence": 0.9,
  "signal_count": 1,
  "active_signal_count": 1,
  "epistemic_confidence": 0.9,
  "signal_lineage": "64-character-sha256-hash",
  "collapse_state": "OPEN",
  "truth_boundary_reference": "ref-hash",
  "telemetry_signal_id": "exec-abc123def456-telemetry",
  "telemetry_timestamp": "2026-07-17T12:00:00Z",
  "safety_metadata": {
    "is_decision": false,
    "authority": "NONE",
    "actionable": false
  },
  "dgic_envelope": {
    "epistemic_confidence": 0.9,
    "signal_lineage": "64-character-sha256-hash",
    "collapse_state": "OPEN",
    "truth_boundary_reference": "ref-hash"
  },
  "telemetry": {
    "signal_id": "exec-abc123def456-telemetry",
    "timestamp": "2026-07-17T12:00:00Z"
  }
}
```

---

## 4. Control Plane (Sūtradhāra Layer 2)

**Endpoint:** `POST /api/v1/sutradhara/invoke`
**Purpose:** The exclusive operational entry-point for all BHIV agents. Authenticates the agent registration, transforms payload into KSML Canonical Envelope, and delegates to Sarathi Governance.

**Request Payload (`SutradharaInvokeRequest`):**
```json
{
  "execution_id": "exec-1234567890ab",
  "actor": "AI_BEING_01",
  "proposed_action": "Modify system configuration file.",
  "source_system": "AI_BEING",
  "context_signals": [
    {
      "signal_id": "ctx-1",
      "signal_type": "threat",
      "value": 0.1,
      "source": "marine_intel"
    }
  ],
  "dgic_epistemic_state": {
    "epistemic_state": "KNOWN",
    "entropy_score": 0.05,
    "contradiction_flag": false,
    "lineage_hash": "64-character-sha256-hash",
    "envelope_hash": "64-character-sha256-hash"
  }
}
```

**Response Payload (`MandalaInvocationResult`):**
```json
{
  "execution_id": "exec-1234567890ab",
  "enforcement_decision": "ALLOW",
  "risk_score": 0.15,
  "confidence": 0.95,
  "trace_hash": "64-character-deterministic-replay-hash",
  "failure_reason": null
}
```
*Note: If the agent is unauthorized or a hard block occurs, `enforcement_decision` will be `DENY` with a populated `failure_reason`.*

---

## 5. Governance Validation (Rajya Layer 1)

**Endpoint:** `POST /api/v1/rajya/validate`
**Purpose:** Validates the execution request and strictly determines if execution is approved based on Rajya governance rules.

**Request Payload (`RajyaValidationRequest`):**
```json
{
  "execution_id": "exec-1234567890ab",
  "sarathi_decision": "ALLOW",
  "sarathi_execution_id": "exec-1234567890ab",
  "enforcement_verdict": {}
}
```

**Response Payload:**
```json
{
  "status": "EXECUTION_APPROVED"
}
```
*(If rejected, returns `{"status": "REJECT", "rejection_code": "...", "rejection_reason": "..."}`)*

---

## 6. Enforcement Gate & Minting (Sarathi Layer 1 & 4)

### 6.1 Token Enforcement
**Endpoint:** `POST /sarathi/enforce`
**Purpose:** Pure Gate Layer. Sarathi evaluates the deterministic token generated from Rajya's approval. If valid, allows execution and mints a secure JWT.

**Request Payload (`EnforceRequest`):**
```json
{
  "token": {
    "execution_id": "exec-1234567890ab",
    "rajya_verdict": "EXECUTION_APPROVED",
    "token_status": "VALID",
    "timestamp": "2026-07-17T12:00:00Z",
    "signature_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "pipeline_execution_id": "exec-1234567890ab",
  "trace_id": "trace-987",
  "cet_hash": "cet-abc-123"
}
```

**Response Payload:**
```json
{
  "status": "ALLOW",
  "jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
*Note: If token is tampered with, expired, or missing, it returns HTTP 403 with `{"status": "BLOCK", "error": "...", "code": "..."}`.*

### 6.2 Token Validation Check
**Endpoint:** `GET /sarathi/validate-token`
**Purpose:** Utility endpoint to independently verify a token's structural validity.

**Query Parameters:**
- `execution_id`
- `rajya_verdict`
- `token_status`
- `timestamp`
- `signature_hash`
- `pipeline_execution_id` (Optional)

**Response Payload:**
```json
{
  "is_valid": true
}
```

---

## 7. Ledger & Traceability (Bucket Layer 5)

Core executes the action if the Sarathi Gate returns ALLOW, subsequently writing an immutable trace into the bucket ledger.

### 7.1 List Bucket Entries
**Endpoint:** `GET /api/v1/bucket/entries`
**Purpose:** List all recorded enforcement bucket entries.

**Response Payload:**
```json
[
  {
    "execution_id": "exec-1234567890ab",
    "decision": "ALLOW",
    "risk_score": 0.15,
    "confidence": 0.95,
    "timestamp": "2026-07-17T12:05:00.123456",
    "trace_hash": "64-character-deterministic-hash",
    "failure_reason": null
  }
]
```

### 7.2 Replay Trace Hash
**Endpoint:** `POST /api/v1/bucket/replay/{trace_hash}`
**Purpose:** Deterministically replay a specific bucket entry via its trace hash to verify input immutability and decision correctness.

**Response Payload (`ReplayResult`):**
```json
{
  "execution_id": "exec-1234567890ab",
  "trace_hash": "64-character-deterministic-hash",
  "match": true,
  "original_decision": "ALLOW",
  "recomputed_decision": "ALLOW",
  "divergence_reason": null
}
```

### 7.3 Replay All
**Endpoint:** `POST /api/v1/bucket/replay_all`
**Purpose:** Replays and verifies ALL bucket entries in the ledger to prove systemic integrity.

**Response Payload:**
```json
{
  "total": 1,
  "passed": 1,
  "failed": 0,
  "results": [
     // List of ReplayResult objects
  ]
}
```

---

## Appendix: Security Invariants
- **No Unstructured Payloads:** All REST requests map 1:1 with strictly validated Pydantic schema models.
- **Deterministic Identity:** Trace hashes (`trace_hash`) provide deterministic serialization over input values, effectively preventing input mutations.
- **Authority Boundary:** Modules (`/analyze`, `/aggregate`) strictly produce mathematical algebraic profiles (`safety_metadata.is_decision = false`) without deriving execution authority. Only `Rajya` issues verdicts, and `Sarathi` acts as a blind enforcement gate over them.
