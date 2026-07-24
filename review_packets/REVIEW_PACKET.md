# Sovereign Core: Phase 6 REVIEW_PACKET

## 1. Entry Point
- **API Gateway**: `app/main.py` -> `POST /api/v1/sutradhara/invoke`
- **Orchestrator**: `app/sutradhara_control_plane.py` -> `invoke_agent()`

## 2. Runtime Flow
1. **API Ingress**: Validates `EvaluateActionRequest` KSML payload.
2. **DGIC**: Ingests snapshot, computes Epistemic envelope & boundaries.
3. **Intelligence**: Calculates baseline contextual risk & NLP analysis.
4. **RAJYA**: Checks risk against governance policy. Yields binary `EXECUTION_APPROVED`/`REJECT`.
5. **Sarathi**: Mints Cryptographic Enforcement Token (if RAJYA approves).
6. **Core Gate**: Validates token signature.
7. **Core Actuator**: Performs physical execution.
8. **Bucket (Async/Ledger)**: Stores Immutable Truth Event payload.
9. **InsightBridge (Async)**: Emits observability telemetry.

## 3. Core Execution Files
- `app/layer4_core.py`: Implementation of `SovereignCoreExecutionEngine` and `enforce_token` gating.
- `app/execution_controller.py`: The physical infrastructure actuator handling the actual execution.

## 4. Runtime Architecture
A linear, vertically integrated, multi-layered stack:
- **Layer 0**: ML Intelligence
- **Layer 1**: Sarathi Cryptographic Tokenization
- **Layer 2**: Sūtradhāra Control Plane
- **Layer 3**: DGIC Epistemic Guardrails
- **Layer 4**: Sovereign Core Actuation
- **Layer 5**: Persistent Bucket Integration
- **Layer 6**: InsightBridge Telemetry
- **Parallel Module**: RAJYA Policy Verification Engine

## 5. Integration Map
- Incoming API → REST
- Bucket Ledger → HTTP POST (Fail-Open configuration)
- External Models → Simulated API clients in Layer 0
- Telemetry → Simulated Kafka/Syslog Sink via InsightBridge

## 6. BCAB/BCAES Classification
*Detailed in `PHASE4_CANONICAL_REGISTRATION.md`.*
- All 8 primary layers strictly bounded to isolated Domains (Architecture, Intelligence, Security, Operations).
- Zero duplicate capabilities detected.

## 7. Live Payloads
**Initial Payload:**
```json
{
  "execution_id": "demo-exec-0cc2a0b0",
  "actor": "marine-intelligence-bot",
  "proposed_action": "Transfer highly classified structural data to Sector 4",
  "source_system": "MARINE_INTELLIGENCE"
}
```

## 8. Execution Logs (Extract)
```
[INFO] Sūtradhāra invocation requested
[INFO] DGIC snapshot ingested
[INFO] Enforecement verdict: ALLOW
[INFO] RAJYA APPROVED | execution_id=demo-exec-0cc2a0b0
[INFO] SARATHI TOKEN MINTED | signature=ce2dc26edccb1f6c...
[INFO] SARATHI GATE ALLOW
[INFO] CORE HANDOFF | rajya=EXECUTION_APPROVED | token_status=VALID → Core will execute
[INFO] Dispatching artifact to external bucket
```

## 9. Trace Evidence
**Canonical Trace Hash**: `aa33a1c5ee2e0ca0d280d24eda3ad3470e76e270181906f227268583c09a24a5`

## 10. Replay Evidence
Determinism holds true: Offline pipeline processing correctly regenerates the exact trace hash (`aa33a1c5ee2e0ca0d280d24eda3ad3470e76e270181906f227268583c09a24a5`) without triggering external infrastructure integrations.

## 11. Bucket Evidence
The truth artifact securely dispatched to standard canonical external bucket (mocked via `http://localhost:8001/bucket/artifact`). Network failures default to "Fail-Open" ensuring pipeline continuation.

## 12. InsightFlow Evidence
`InsightBridge enforcement decision telemetry emitted` logged perfectly to simulated event stream, maintaining total separation from control plane.

## 13. Failure Matrix
- **Network Outage (Bucket)** -> Fails OPEN. System proceeds.
- **RAJYA Policy Violation** -> RAJYA Returns `REJECT`. Token NOT minted. Execution `DENIED`.
- **Invalid Token Signature** -> Core Gate REJECT. Token NOT valid. Execution `DENIED`.
- **DGIC Epistemic Invalidation** -> Control Plane ABSTAIN. Pipeline halts. Execution `DENIED`.

## 14. Production Validation Report
*Detailed in `PHASE3_PRODUCTION_VALIDATION_PROOF.md`.* All tests `PASS`. Validated End-to-End Execution, Replay Determinism, Failure Injection, Dependency Resiliency, and Authority Boundation.

## 15. Dependency Map
- **Python**: 3.11+
- **Framework**: FastAPI / Pydantic (Control Plane)
- **Security**: hashlib, rsa (stubbed Cryptography)
- **External Network**: requests (Bucket API)

## 16. Authority Matrix
- **Policy**: RAJYA
- **Tokenization**: Sarathi
- **Execution**: Core Layer 4
- **Orchestration**: Sūtradhāra Layer 2
- **Risk Analysis**: Intelligence Layer 0
- *Proof in `PHASE5_CONSTITUTIONAL_VALIDATION_REPORT.md`*

## 17. Registry Map
Canonical BCAB registration completed and cleared of duplicate capability ownership.

## 18. Successor Guide
- Setup standard venv: `python -m venv venv`
- Install dependencies: `pip install -r requirements.txt`
- Check tests via script: `python validate_production.py`
- Run local simulation: `python demo_pipeline.py` (ensure `mock_bucket_service.py` is running simultaneously).
