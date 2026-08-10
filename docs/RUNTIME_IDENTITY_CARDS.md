# Constitutional Runtime Identity Cards

This document outlines the strict Constitutional Runtime Identity and Certification for every participant owned by the Sovereign Core (`text-risk-scoring-service`). 
Every authority boundary is explicitly defined to guarantee no capability duplication or hidden integrations exist.

---

## 1. Sūtradhāra Control Plane
* **Constitutional Layer:** Layer 2
* **Permanent Identity:** `urn:bhiv:sovereign:sutradhara:v1`
* **Purpose:** Central orchestration engine. Routes pipeline execution, aggregates signals, delegates tasks, and maintains execution state.
* **Owner:** `text-risk-scoring-service`
* **Authority Owned:** Orchestration sequence, Pipeline routing, System-wide telemetry aggregation.
* **Authority Explicitly NOT Owned:** Intelligence analysis, Epistemic verification, Cryptographic token minting, Final governance validation, Task execution.
* **Adjacent Producers:** Upstream API Clients / Demo Scripts
* **Adjacent Consumers:** DGIC (Layer 3), Intelligence (Layer 0), KESHAV (Layer 2.5), Sarathi (Layer 1), RAJYA, CET (Layer 7), Core Execution (Layer 4), InsightBridge (Layer 6).
* **APIs:** `POST /api/v1/sutradhara/invoke`
* **Events Consumed:** KSML Input Traces
* **Events Emitted:** `sutradhara_api_request`, `sutradhara_decision_derived`, `core_handoff_proof`
* **SDK Contracts:** `KSMLInput`, `MandalaInvocationResult`
* **Registry Participation:** Integration Pending (Runtime, Capability, Execution)
* **Evidence Produced:** Orchestration sequence logs, Epistemic snapshots.
* **Replay Participation:** Full pipeline execution replay capability.
* **Observability Model:** InsightBridge Unified Telemetry Emitter.
* **Knowledge Contribution:** Aggregated execution state graphs.
* **Runtime Health Model:** Evaluated via `GET /health` endpoints.
* **Version Compatibility:** v1.0
* **Production Certification Status:** 🟢 CONVERGED

---

## 2. Intelligence Core
* **Constitutional Layer:** Layer 0
* **Permanent Identity:** `urn:bhiv:sovereign:intelligence:v1`
* **Purpose:** Analyzes context signals and applies NLP heuristics to compute deterministic risk scores and confidence baselines for textual data.
* **Owner:** `text-risk-scoring-service`
* **Authority Owned:** Text-risk scoring, NLP threat detection heuristics, Risk baseline calculation.
* **Authority Explicitly NOT Owned:** Epistemic evaluation (DGIC), Cryptographic enforcement sealing, Governance constraints, Action execution.
* **Adjacent Producers:** Sūtradhāra (Provides Context Signals)
* **Adjacent Consumers:** Sūtradhāra, Sarathi (Consumes derived risk score).
* **APIs:** Internal Python Module (`app/layer0_intelligence.py` -> `analyze_context()`)
* **Events Consumed:** Raw NLP Text Signals
* **Events Emitted:** `analysis_start`, `analysis_complete`
* **SDK Contracts:** `RiskIntelligence` (Dataclass)
* **Registry Participation:** N/A (Internal Module)
* **Evidence Produced:** Float metrics (`risk_score`, `confidence`).
* **Replay Participation:** Fully deterministic; identical inputs produce identical risk scores.
* **Observability Model:** Internal Logging (`app.layer0_intelligence`).
* **Knowledge Contribution:** Dynamic threat vectors and NLP context evaluations.
* **Runtime Health Model:** Inherits from Sūtradhāra.
* **Version Compatibility:** v1.0
* **Production Certification Status:** 🟢 CONVERGED

---

## 3. Sarathi Enforcement
* **Constitutional Layer:** Layer 1
* **Permanent Identity:** `urn:bhiv:sovereign:sarathi:v1`
* **Purpose:** Cryptographically seals the pipeline state by minting an unforgeable Sarathi Enforcement Token required for Core execution.
* **Owner:** `text-risk-scoring-service`
* **Authority Owned:** Trace Hash generation (SHA-256), Enforcement Token signing, Token signature validation.
* **Authority Explicitly NOT Owned:** Intelligence derivation, Governance policy definitions, Execution routing.
* **Adjacent Producers:** Sūtradhāra, Intelligence, DGIC (Indirectly)
* **Adjacent Consumers:** Sūtradhāra, Core Execution (Layer 4)
* **APIs:** Internal Python Module (`app/layer1_sarathi.py` -> `compute_trace_hash()`, `enforce_token()`)
* **Events Consumed:** Aggregate Risk Scores, Intelligence outputs, Epistemic State.
* **Events Emitted:** `sarathi_token_minted`, `sarathi_token_validated`, `sarathi_gate_allow`
* **SDK Contracts:** `SarathiEnforcementToken`
* **Registry Participation:** Integration Pending (Replay, Review)
* **Evidence Produced:** `trace_hash`, `signature_hash`.
* **Replay Participation:** Ensures identical state mappings produce identical cryptographic hashes.
* **Observability Model:** Cryptographic Token Lineage Tracking.
* **Knowledge Contribution:** Immutable execution envelope schemas.
* **Runtime Health Model:** Inherits from Sūtradhāra.
* **Version Compatibility:** v1.0
* **Production Certification Status:** 🟢 CONVERGED

---

## 4. RAJYA Validation Engine
* **Constitutional Layer:** Governance Gate
* **Permanent Identity:** `urn:bhiv:sovereign:rajya:v1`
* **Purpose:** The final absolute authority validation gate. Enforces strict trace continuity (e.g. from KESHAV) and cross-references Sarathi decisions before allowing Core handoff.
* **Owner:** `text-risk-scoring-service`
* **Authority Owned:** Final GO/NO-GO execution approval, Upstream trace continuity enforcement.
* **Authority Explicitly NOT Owned:** Intelligence processing, Token minting, System orchestration, Target execution.
* **Adjacent Producers:** Sūtradhāra, KESHAV Analytics (Layer 2.5)
* **Adjacent Consumers:** Sūtradhāra (Consumes the EXECUTION_APPROVED verdict to proceed)
* **APIs:** Internal Python Module (`app/rajya_validation_engine.py` -> `validate_execution_request()`, `consume()`)
* **Events Consumed:** `keshav_output`, `enforcement_verdict`, `sarathi_decision`
* **Events Emitted:** `rajya_keshav_consume`, `rajya_validation_start`, `rajya_decision`, `rajya_approved`
* **SDK Contracts:** `RajyaValidationResult`, `RajyaRejection`
* **Registry Participation:** Integration Pending
* **Evidence Produced:** Deterministic approval/rejection logic codes.
* **Replay Participation:** Strict rule validations.
* **Observability Model:** Immutable Validation Decision Logging.
* **Knowledge Contribution:** Sector Policy rules and Validation constraints.
* **Runtime Health Model:** Inherits from Sūtradhāra.
* **Version Compatibility:** v1.0
* **Production Certification Status:** 🟢 CONVERGED
