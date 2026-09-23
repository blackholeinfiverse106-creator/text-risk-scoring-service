# Sovereign Core ↔ Niyantran Kendra Integration Contract

This document provides the canonical API contract required to integrate the **Sovereign Core (text-risk-scoring-service)** with the **Niyantran Kendra Dashboard**.

## 1. Live State Streaming Endpoint
The Sovereign Core exposes a dedicated, read-only endpoint that streams the canonical execution state of all runtime invocations.

- **Endpoint:** `GET /api/v1/niyantran/traces`
- **Method:** `GET`
- **Response Format:** `application/json`
- **Authentication:** (Internal VPC / No Auth for current iteration)

## 2. Response Schema
The endpoint returns a JSON array of execution state objects. Each object represents the complete, immutable state of a single Sūtradhāra invocation, from inception to cryptographic ledgering.

### Example Payload
```json
[
  {
    "execution_id": "exec-4d84a2b1cfa5",
    "execution_status": "FAILED",
    "dgic_state": "KNOWN",
    "risk_score": 0.0,
    "confidence": 0.0,
    "rajya_verdict": "PENDING",
    "sarathi_status": "PENDING",
    "core_status": "PENDING",
    "bucket_persistence": false,
    "failure_reason": "DGIC snapshot rejected: DGIC_SEAL_VERIFICATION_FAILED...",
    "trace_hash": "baecfe00bacf96a1b1cfa52707db79d06354f77b7b0d2d0e78d928cd647fc566"
  },
  {
    "execution_id": "exec-99f8c12a4b3d",
    "execution_status": "COMPLETED",
    "dgic_state": "KNOWN",
    "risk_score": 0.15,
    "confidence": 1.0,
    "rajya_verdict": "EXECUTION_APPROVED",
    "sarathi_status": "VALID",
    "core_status": "ALLOW",
    "bucket_persistence": true,
    "failure_reason": null,
    "trace_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
]
```

## 3. Field Definitions

| Field | Type | Description |
| :--- | :--- | :--- |
| `execution_id` | `String` | The unique canonical identifier for the pipeline execution. |
| `execution_status` | `String` | The final status of the pipeline (`IN_PROGRESS`, `COMPLETED`, `DENIED_OR_FAILED`, `FAILED`, `CRASHED`). |
| `dgic_state` | `String` | The epistemic state of the intelligence snapshot (`KNOWN`, `INFERRED`, `AMBIGUOUS`, `UNKNOWN`). |
| `risk_score` | `Float` | The computed NLP threat risk score [0.0 - 1.0]. |
| `confidence` | `Float` | The system's confidence in the risk score [0.0 - 1.0]. |
| `rajya_verdict` | `String` | The absolute governance verdict from the RAJYA validation engine (e.g., `EXECUTION_APPROVED`, `DENY`, `PENDING`). |
| `sarathi_status` | `String` | The cryptographic status of the minted Enforcement Token (e.g., `VALID`, `INVALID`, `PENDING`). |
| `core_status` | `String` | The final execution output from the Core Execution layer (e.g., `ALLOW`, `DENY`, `PENDING`). |
| `bucket_persistence` | `Boolean` | `true` if the cryptographic artifact was successfully chained and stored in the live external Bucket Ledger. |
| `failure_reason` | `String | Null` | Detailed string describing the rejection/crash reason if the pipeline failed or was denied. |
| `trace_hash` | `String` | The SHA-256 cryptographic hash representing the canonical execution state. Used for replay verification. |

## 4. Integration Guidelines for Niyantran Kendra
1. **Observational Boundary:** Niyantran Kendra is strictly an observational control plane. This endpoint is read-only. The dashboard MUST NOT attempt to mutate execution state or inject parallel governance authority.
2. **Polling Frequency:** The dashboard should poll this endpoint at a reasonable interval (e.g., every 3-5 seconds) to maintain live state synchronization.
3. **Trace Limiting:** The endpoint automatically maintains an in-memory sliding window of the most recent executions to prevent payload bloat.
