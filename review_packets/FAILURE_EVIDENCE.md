# Phase 5: Hardening - Failure Evidence & Validation

## Objective
Validate the behavior of the Sūtradhāra Soveign Core runtime when subsystems face unavailability, mismatch, or malicious spoofing conditions.

## 1. Failure Evidence

| Condition | Description | System Response | Outcome |
|-----------|-------------|-----------------|---------|
| **DGIC Unavailable / Seal Broken** | DGIC network down, or envelope hash tampered. | `DGICSnapshotError: Cryptographic seal broken: envelope_hash does not match payload hash. ENVELOPE TAMPERED.` | The Control Plane safely caught the DGIC fault and explicitly coerced the evaluation to an `ABSTAIN` (or block), ensuring the pipeline did not advance to intelligence or execution. |
| **RAJYA Unavailable** | RAJYA validation engine raises exception / offline. | `Exception propagated: RAJYA is down` | Unhandled network exceptions in Sūtradhāra inherently propagate to the fast-api boundary resulting in an API 500 error. The execution fails closed (no token is minted, and Core is never reached). |
| **Core Unavailable** | `execute_core_mandala` faults. | `Exception propagated: Core execution failed` | The action execution itself fails, but the ledger writes have a "fail-open" try/except. The pipeline halts but the rejection is cleanly captured. |
| **Trace Mismatch** | Execution ID mismatch during Enforcement/RAJYA steps. | `EnforcementHardFailure` or `RAJYA_EXECUTION_ID_MISMATCH` | Detected immediately. The pipeline emits an `EnforcementDecision.DENY` directly to telemetry and terminates. |
| **Contract Mismatch** | KSML validation fails (e.g. missing `actor`). | `ValidationError - 1 validation error for KSMLInput` | Pydantic aggressively denies entry at the perimeter API boundary before any pipeline code is executed. |
| **Replay Validation** | Trace validation against the `Bucket`. | External HTTP timeout due to unavailable Ledger API. | `MaxRetryError` logged in `layer5_bucket.py`, but pipeline "fails open" locally (by architectural design) to prevent execution blockage from observability outages. |

## 2. Fixes Applied
- **Fail-Closed Gateways:** Ensure that any uncaught exceptions during Sūtradhāra evaluation explicitly default to blocking the action. The Sūtradhāra FastAPI top-level boundary handles unhandled exceptions.
- **Strict Hash Verification:** The `KSMLInput` passes through the `compute_envelope_hash` function inside DGIC strictly verifying payload integrity. The mock test initially bypassed it, so we strictly fixed the `prove_hardening.py` inputs to provide a legitimate cryptographic seal.

## 3. Remaining Risks
- **Observability Fail-Open:** Currently, Layer 5 Bucket `write_execution_record` is designed to log an error and silently continue if the external Bucket API is unreachable. This was an explicit architectural policy but it poses a risk of unaudited executions if the API experiences extended downtime.
- **Synchronous Bottlenecks:** RAJYA acts as a synchronous HTTP/function gateway. If the system is under heavy load, RAJYA timeout could cause spurious execution blocks.
