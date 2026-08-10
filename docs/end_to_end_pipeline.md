# End-to-End Pipeline Demonstration

This document explains the runtime sequence and the end-to-end execution pipeline of the Text Risk Scoring Service, exactly as modeled in the `demo_pipeline.py` script. The demonstration illustrates how an incoming execution payload propagates strictly through the architectural layers of the system—from invocation to final cryptographic verification.

## 1. Invocation (Sūtradhāra Control Plane)
The lifecycle begins when a payload is POSTed to the Control Plane at `/api/v1/sutradhara/invoke`.
* **Action:** The caller requests an operation (e.g., `'Transfer highly classified structural data to Sector 4'`).
* **Validation:** The Control Plane validates the payload schema (verifying required fields like `execution_id`, `actor`, `proposed_action`).
* **Routing:** It acts as the grand orchestrator, routing the payload strictly downstream to the Intelligence Core and DGIC.

## 2. Ingestion & Epistemic Verification (Layer 3 - DGIC)
Before any intelligence evaluation can occur, the Data Governance and Intelligence Contract (DGIC) acts as a strict boundary.
* **Epistemic State:** DGIC verifies the epistemic state (e.g., `KNOWN`, `AMBIGUOUS`, `UNKNOWN`).
* **Contradiction Flag:** It checks the contradiction flag to ensure the input data is structurally and logically sound.
* **Cryptographic Envelope:** It rigorously validates the computed SHA-256 envelope hash against the lineage hash and payload to prevent tampering.

## 3. Intelligence Analysis (Layer 0 - Intelligence Core)
Once the data is proven sound by DGIC, the Intelligence Core performs the actual analysis.
* **Signal Scanning:** It scans the context signals for threats (e.g., `security_threat` with a `value` of `0.15`).
* **Heuristics & Scoring:** Applies NLP heuristics, computes entropy, and evaluates contextual risk parameters.
* **Risk Baseline:** Generates the initial Risk Score (e.g., `0.15`) and a Confidence Metric (e.g., `1.0`).

## 4. Token Minting (Layer 1 - Sarathi Enforcement)
With the risk score computed, Sarathi takes over to enforce the decision cryptographically.
* **Data Gathering:** It bundles the risk scores, confidence metrics, and intelligence data.
* **Trace Hash:** It generates a permanent SHA-256 `trace_hash` representing the entire state and preliminary verdict.
* **Token Signature:** It mints and cryptographically signs a Sarathi Enforcement Token. The execution cannot proceed without this valid signature.

## 4.5. Analytics & Root Cause (Layer 2.5 - KESHAV)
Before the absolute final governance check, the pipeline delegates to KESHAV for analytics.
* **Mock Adapter Phase:** Because we don't naturally evaluate tasks in this project, we map our trace to a mock dependency graph to interface with the Analytics Engine.
* **Network Call:** Sūtradhāra pings the live KESHAV endpoint (`https://keshav-cia7.onrender.com/analyze`).
* **Consumption:** The `keshav_output` is generated and strictly passed into the RAJYA engine via `rajya.consume(keshav_output, trace_id)` to prove trace continuity.

## 5. Governance Constraints (Rajya Validation Engine)
Once Sarathi has sealed the execution state, the payload hits the absolute final governance checkpoint—the Rajya Engine.
* **Double-Lock Consensus Check:** It inspects both the original intention (`sarathi_decision`) and Sarathi's sealed output (`enforcement_verdict`).
* **Authorization Check:** It ensures the `actor` is permitted and the cryptographic IDs perfectly match.
* **Verdict:** Outputs a deterministic governance verdict (`EXECUTION_APPROVED` or rejection). Core Execution will not run without this final approval.

## 6. CET Validator (Shadow Execution)
Before final execution, the pipeline consults the external CET Engine for a mathematical audit.
* **Mock Adapter Phase:** Because the current CET engine is strictly restricted to financial schemas, Sūtradhāra disguises our text-risk payloads into a "TransferFunds" transaction template.
* **Network Call:** The disguised payload is POSTed to the external CET validator `https://sl-validator-cet.onrender.com/validate`.
* **Canonical Hash Extraction:** The CET returns a mathematically derived `cet_hash` proving the transaction was audited, which we inject into our telemetry for canonical proof.

## 7. Execution (Layer 4 - Core Execution)
The Core Layer is the final, dumb execution point. It makes no decisions of its own; it simply obeys Sarathi.
* **Verification:** Core evaluates the cryptographic signature of the Sarathi Enforcement Token. If invalid or missing, it triggers a `SarathiHardBlockError`.
* **Handoff:** If the token signature is valid, authorization is GRANTED.
* **Final Execution:** The requested payload action is finally executed by the execution controller.

## 8. Cryptographic Ledgering (Layer 5 - Bucket Ledger)
Following execution, the system maintains a sovereign record.
* **Final Verdict Logged:** The `trace_hash`, decision (e.g., `ALLOW`), and risk score are packaged into a final artifact.
* **External Storage:** In a full production environment, this payload is sent over the network to the strictly decoupled Bucket Service (`http://localhost:8000/bucket/artifact`) where the hash provides an immutable audit trail.

## Pipeline Architecture Diagram

```mermaid
sequenceDiagram
    participant Client as API Client / Demo Script
    participant Sutradhara as Control Plane (Layer 2)
    participant DGIC as DGIC Contract (Layer 3)
    participant Intel as Intelligence Core (Layer 0)
    participant Sarathi as Sarathi Enforcement (Layer 1)
    participant Keshav as KESHAV Analytics (Layer 2.5)
    participant Rajya as Rajya Validation Engine
    participant CET as CET Validator (Layer 7)
    participant Core as Core Execution (Layer 4)
    participant Bridge as InsightBridge (Layer 6)
    participant Bucket as Bucket Ledger (Layer 5)

    Client->>Sutradhara: 1. POST /api/v1/sutradhara/invoke
    activate Sutradhara
    Sutradhara->>DGIC: 2. Ingest Snapshot & Epistemic Verification
    activate DGIC
    DGIC-->>Sutradhara: Verification Passed
    deactivate DGIC
    
    Sutradhara->>Intel: 3. Analyze Risk & Confidence
    activate Intel
    Intel-->>Sutradhara: Risk Score (0.15)
    deactivate Intel
    
    Sutradhara->>Sarathi: 4. Mint Cryptographic Enforcement Token
    activate Sarathi
    Sarathi-->>Sutradhara: Signed Token + Trace Hash
    deactivate Sarathi
    
    Sutradhara->>Keshav: 5. Root Cause & Analytics
    activate Keshav
    Keshav-->>Sutradhara: keshav_output
    deactivate Keshav
    
    Sutradhara->>Rajya: 6. Consume KESHAV & Validate Governance
    activate Rajya
    Rajya-->>Sutradhara: EXECUTION_APPROVED
    deactivate Rajya
    
    Sutradhara->>CET: 7. Shadow Validate (Mock Adapter)
    activate CET
    CET-->>Sutradhara: Canonical cet_hash
    deactivate CET
    
    Sutradhara->>Core: 8. Hand off Execution & Token
    activate Core
    Core->>Core: Verify Token Signature
    Core->>Core: Execute Requested Action
    
    Core->>Bucket: 9. Ledger Final Verdict & Trace Hash
    activate Bucket
    Bucket-->>Core: Artifact Stored / Fail Open
    deactivate Bucket
    
    Core-->>Sutradhara: Execution Complete
    deactivate Core
    
    Sutradhara->>Bridge: 10. Broadcast Final Telemetry Event
    activate Bridge
    Bridge-->>Sutradhara: 200 OK (Observability Sync)
    deactivate Bridge
    
    Sutradhara-->>Client: 11. Final Verdict (JSON Response)
    deactivate Sutradhara
```
