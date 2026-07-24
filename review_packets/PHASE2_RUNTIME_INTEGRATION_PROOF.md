# Phase 2: Runtime Integration Proof

This document provides evidence for the full runtime execution of the Sovereign Core pipeline, fulfilling the Phase 2 convergence mandate.

## Execution Summary
- **Execution ID**: `demo-exec-0cc2a0b0`
- **Trace Hash**: `5ec79ec53e79703186613c4a0d8e64828691b03ab8167dc9cde2546d926990bc`
- **Final Decision**: `ALLOW`
- **Risk Score**: `0.15`
- **Confidence**: `1.0`

---

## Runtime Hops & Contract Evidence

### 1. Request / Payload (Sūtradhāra Control Plane)
- **Input**: `EvaluateActionRequest` via `demo_pipeline.py`
  - Action: "Transfer highly classified structural data to Sector 4"
  - Actor: `marine-intelligence-bot`
  - Source System: `MARINE_INTELLIGENCE`
- **Output**: Request routed to DGIC Layer 3
- **Contract**: KSML structured schema (`SutradharaInvokeRequest`)
- **Evidence**: Validated by the Sūtradhāra API schema checker. 
  ```json
  { "event_type": "sutradhara_api_request", "execution_id": "demo-exec-0cc2a0b0" }
  ```

### 2. DGIC Snapshot & Intelligence
- **Input**: DGIC Epistemic Envelope (`epistemic_state: KNOWN`)
- **Output**: Validated epistemic properties & computed Intelligence Risk (`0.15`)
- **Contract**: `DGICEpistemicStateInput` contradiction logic
- **Evidence**: 
  ```json
  { "event_type": "dgic_snapshot_ingested", "epistemic_state": "KNOWN" }
  { "event_type": "analysis_complete", "score": 0.0, "category": "LOW" }
  ```

### 3. Governance Approval (RAJYA)
- **Input**: Risk evaluation data + Orchestrator's derived decision (`ALLOW`)
- **Output**: `EXECUTION_APPROVED`
- **Contract**: RAJYA canonical validation interface
- **Evidence**: 
  ```json
  { "event_type": "rajya_decision", "result": "EXECUTION_APPROVED", "rejection": "NONE" }
  ```

### 4. Enforcement Tokenization (Sarathi)
- **Input**: RAJYA verdict (`EXECUTION_APPROVED`) + Execution ID
- **Output**: Signed Cryptographic Enforcement Token (CET)
- **Contract**: Token must contain a valid cryptographic signature (`signature_hash`).
- **Evidence**: 
  ```json
  { "event_type": "sarathi_token_minted", "signature": "ce2dc26edccb1f6c..." }
  { "event_type": "sarathi_gate_allow" }
  ```

### 5. Physical Execution (Sovereign Core)
- **Input**: Action, Execution ID, and validated Enforcement Token.
- **Output**: Physical execution triggered via `app.execution_controller.execute_action()`
- **Contract**: Execution proceeds ONLY if `enforce_token()` gate evaluates as `VALID`
- **Evidence**: 
  ```json
  { "event_type": "core_action_executed", "action": "Transfer highly classified structural data to Sector 4" }
  ```

---

## 6. Truth Artifact (External Bucket Persistence)
Decoupled infrastructure (Phase 3 spec) requires an external persistent bucket. We successfully invoked an external bucket service running on port 8001.

**Evidence from `/bucket/artifacts`**:
```json
{
  "artifact_id": "demo-exec-0cc2a0b0",
  "source_module_id": "bhiv_enforcement_gate",
  "schema_version": "1.0.0",
  "artifact_type": "truth_event",
  "payload": {
    "decision": "ALLOW",
    "risk_score": 0.15,
    "confidence": 1.0,
    "trace_hash": "5ec79ec53e79703186613c4a0d8e64828691b03ab8167dc9cde2546d926990bc"
  },
  "artifact_hash": "487d386e4083f8803898a575451b94c3ad8dc458816967f6b5061a05aa66a52d"
}
```

---

## 7. Replay Artifact (Bucket Replay Validation)
The system fetches the Truth Artifact from the external bucket and deterministically re-evaluates it without invoking external agents to prove immutability and determinism.

**Evidence from `/api/v1/bucket/replay_all`**:
```json
{
  "bucket_id": "demo-exec-0cc2a0b0",
  "trace_hash": "5ec79ec53e79703186613c4a0d8e64828691b03ab8167dc9cde2546d926990bc",
  "original_decision": "ALLOW",
  "replayed_decision": "ALLOW",
  "match": true,
  "replay_proof_valid": true
}
```

---

## 8. Observability & Knowledge Contribution (InsightBridge)
InsightBridge asynchronously emits the telemetry to the broader Knowledge Sink.

**Evidence from Application Logs**:
```json
{
  "event_type": "insightbridge_enforcement_emission",
  "message": "InsightBridge enforcement decision telemetry emitted",
  "logger": "app.layer6_insightbridge"
}
```
