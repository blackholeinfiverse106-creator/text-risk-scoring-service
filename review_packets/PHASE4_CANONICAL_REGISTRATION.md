# Phase 4: BCAB / BCAES Canonical Registration

This document serves as the official Business Capability Architecture Ecosystem (BCAES) canonical registry for all Sovereign Core components. Every component has been evaluated against the BCAB Classification Test to ensure no duplicate capability ownership exists across the boundaries.

---

## 1. Sūtradhāra Control Plane (Layer 2)
- **Name**: Sūtradhāra Control Plane
- **Primary Classification**: Platform Service
- **Domain**: Architecture Ecosystem
- **Capability**: Agent Invocation & Pipeline Orchestration
- **Platform Service**: Enforcement Gateway API
- **Owner**: Rajaryan Verma (Sovereign Core Lead)
- **Purpose**: Securely routes valid agent requests, provisions Execution IDs, and orchestrates the sequence of intelligence, governance, and execution layers inline.
- **Inputs**: KSML Structured Signals (`SutradharaInvokeRequest`)
- **Outputs**: `MandalaInvocationResult`
- **Dependencies**: DGIC, Intelligence, RAJYA, Sarathi, Core, Bucket, InsightBridge
- **Consumers**: Upstream Application Agents (e.g., MARINE_INTELLIGENCE)
- **Interface Contract**: KSML Validation Schema
- **Authority Owned**: Pipeline Routing, Agent Registration Verification
- **Authority NOT Owned**: Cryptographic token minting, Final governance decision, Physical execution
- **Status**: Production-Ready
- **BCAB Classification Test**: Architecture Domain → Orchestration Capability → Enforcement Gateway → Sovereign Core Product → Ecosystem Program

---

## 2. DGIC Epistemic Adapter (Layer 3)
- **Name**: DGIC Epistemic Envelope & Adapter
- **Primary Classification**: Platform Service
- **Domain**: Intelligence Ecosystem
- **Capability**: Epistemic Envelope Integrity & Grounding
- **Platform Service**: Epistemic Verifier
- **Owner**: Pritesh Patra (DGIC Integration)
- **Purpose**: Extracts, cryptographically verifies, and maps external signal state constraints into internal epistemic states. Calculates Entropy Boundaries.
- **Inputs**: DGIC Cryptographic Envelope Payload
- **Outputs**: `DGICAdapterResult`, `EntropyBoundary`
- **Dependencies**: External Epistemic Lineage Hashes
- **Consumers**: Sūtradhāra Orchestrator, Intelligence Engine
- **Interface Contract**: DGIC Input Validation Schema
- **Authority Owned**: Epistemic state normalization, Entropy validation, Envelope integrity
- **Authority NOT Owned**: Risk scoring, Governance enforcement
- **Status**: Production-Ready
- **BCAB Classification Test**: Intelligence Domain → Epistemic Grounding Capability → Epistemic Verifier → Sovereign Core Product → Ecosystem Program

---

## 3. Intelligence Risk Engine (Layer 0)
- **Name**: Core Intelligence Risk Engine
- **Primary Classification**: Platform Service
- **Domain**: Intelligence Ecosystem
- **Capability**: Contextual Risk Scoring & Threat Analysis
- **Platform Service**: Risk Intelligence
- **Owner**: Sovereign Core ML Team
- **Purpose**: Computes baseline computational risk scores and epistemic confidences based on parsed NLP inputs and surrounding context signals.
- **Inputs**: Raw Text Action, Context Signals, `DGICAdapterResult`
- **Outputs**: `IntelligenceOutput` (final_risk, confidence)
- **Dependencies**: Validated Epistemic State
- **Consumers**: Sūtradhāra (Decision Derivation logic)
- **Interface Contract**: Internal Intelligence Input Schema
- **Authority Owned**: Threat quantification algorithm, NLP sentiment modeling
- **Authority NOT Owned**: Business policy evaluation, Action gating
- **Status**: Production-Ready
- **BCAB Classification Test**: Intelligence Domain → Threat Analysis Capability → Risk Intelligence → Sovereign Core Product → Ecosystem Program

---

## 4. RAJYA Validation Engine
- **Name**: RAJYA Validation Engine
- **Primary Classification**: Platform Service
- **Domain**: Governance Ecosystem
- **Capability**: Canonical Policy Enforcement
- **Platform Service**: RAJYA Core
- **Owner**: Sovereign Core Policy Team
- **Purpose**: Serves as the ultimate canonical authority on whether a core execution is permitted based on predefined constitutional governance boundaries.
- **Inputs**: Execution ID, Sūtradhāra Derived Decision, Context
- **Outputs**: `RajyaValidationResult` (`EXECUTION_APPROVED` or `REJECT`)
- **Dependencies**: None
- **Consumers**: Sūtradhāra Orchestrator
- **Interface Contract**: `RajyaValidationRequest`
- **Authority Owned**: Constitutional policy evaluation, Final governance approval
- **Authority NOT Owned**: Cryptographic Token signing, Physical actuator execution
- **Status**: Production-Ready
- **BCAB Classification Test**: Governance Domain → Policy Enforcement Capability → RAJYA Core → Sovereign Core Product → Ecosystem Program

---

## 5. Sarathi Governance Tokenization (Layer 1)
- **Name**: Sarathi Governance Tokenization
- **Primary Classification**: Platform Service
- **Domain**: Security Ecosystem
- **Capability**: Cryptographic Action Authorization
- **Platform Service**: Token Mint & Gate
- **Owner**: Hemanth (Sarathi & Enforcement)
- **Purpose**: Issues cryptographic enforcement tokens directly dependent on RAJYA approval, and acts as the impenetrable execution gatekeeper pre-actuation.
- **Inputs**: RAJYA Verdict, Execution ID, Trace Hash Timestamp
- **Outputs**: Signed `SarathiEnforcementToken`
- **Dependencies**: RAJYA output verdict
- **Consumers**: Sūtradhāra (Mint), Core Execution (Gate Verification)
- **Interface Contract**: Cryptographic Token Schema, SHA-256 Signature Verification
- **Authority Owned**: Execution Token issuance, Pre-execution Cryptographic Gate Blocking
- **Authority NOT Owned**: Intelligence generation, Policy rulesets, Physical execution
- **Status**: Production-Ready
- **BCAB Classification Test**: Security Domain → Action Authorization Capability → Token Mint & Gate → Sovereign Core Product → Ecosystem Program

---

## 6. Core Execution Infrastructure (Layer 4)
- **Name**: Sovereign Core Execution Engine
- **Primary Classification**: Platform Service
- **Domain**: Operations Ecosystem
- **Capability**: Physical Action Actuation
- **Platform Service**: Execution Controller
- **Owner**: Raj Prajapati (Core Runtime / Execution Infra)
- **Purpose**: The absolute lowest layer that guarantees the physical execution of the approved action on external infrastructure, entirely devoid of business logic.
- **Inputs**: Validated `SarathiEnforcementToken`, Execution Context
- **Outputs**: Final `MandalaInvocationResult`, Physical side-effects
- **Dependencies**: Sarathi Enforcement Gate (MUST PASS)
- **Consumers**: Sūtradhāra Orchestrator
- **Interface Contract**: Execution Gate payload
- **Authority Owned**: Infrastructure Actuation, Downstream REST integration
- **Authority NOT Owned**: Token signature validation (relies on Sarathi API), Observability routing
- **Status**: Production-Ready
- **BCAB Classification Test**: Operations Domain → Actuation Capability → Execution Controller → Sovereign Core Product → Ecosystem Program

---

## 7. Persistent Bucket Adapter (Layer 5)
- **Name**: Persistent Bucket Adapter
- **Primary Classification**: Platform Service
- **Domain**: Architecture Ecosystem
- **Capability**: Immutable Ledger Record Storage
- **Platform Service**: Storage Adapter
- **Owner**: Infrastructure Owner (Persistent Bucket)
- **Purpose**: Prepares and dispatches the canonical execution truth artifact to the external, decoupled persistence ledger, adopting a strict fail-open policy. Validates offline deterministic replay.
- **Inputs**: Trace Hash, Enforcement Decision, Execution Payload, DGIC Snapshot
- **Outputs**: Formatted REST payload / `Artifact Hash`
- **Dependencies**: External Bucket REST Service
- **Consumers**: Core Execution Engine
- **Interface Contract**: Bucket REST API Canonical Schema (`Truth Artifact` format)
- **Authority Owned**: Payload formatting and asynchronous network dispatch for ledger persistence
- **Authority NOT Owned**: Physical database clustering, Data-at-rest encryption
- **Status**: Production-Ready
- **BCAB Classification Test**: Architecture Domain → Ledger Storage Capability → Storage Adapter → Sovereign Core Product → Ecosystem Program

---

## 8. InsightBridge Telemetry (Layer 6)
- **Name**: InsightBridge Telemetry
- **Primary Classification**: Platform Service
- **Domain**: Intelligence Ecosystem
- **Capability**: Observability & Knowledge Streaming
- **Platform Service**: Telemetry Bus
- **Owner**: Vijay Dhawan (InsightFlow Validation)
- **Purpose**: Formats and asynchronously pushes rich enforcement event telemetry into the global enterprise knowledge sink.
- **Inputs**: Execution ID, Decision, Risk Score, Trace Hash
- **Outputs**: Formatted Telemetry Dictionary
- **Dependencies**: Upstream Core output
- **Consumers**: External Enterprise Knowledge Graphs, Monitoring Tools
- **Interface Contract**: InsightBridge standard telemetry format
- **Authority Owned**: Global enterprise visibility, Standardized Observability routing
- **Authority NOT Owned**: Execution gating, Canonical immutable ledger storage
- **Status**: Production-Ready
- **BCAB Classification Test**: Intelligence Domain → Observability Capability → Telemetry Bus → Sovereign Core Product → Ecosystem Program

---

## BCAES Duplication Audit Result
**Verdict: CLEAN.**
A thorough analysis confirms there is ZERO duplicate capability ownership.
- The pipeline delegates strictly linear authority.
- RAJYA exclusively owns policy.
- Sarathi exclusively owns cryptographic tokenization.
- The Core exclusively owns physical actuation.
- Intelligence exclusively owns risk scoring.
- Sūtradhāra exclusively owns orchestration.
- No parallel implementations exist, ensuring absolute adherence to constitutional boundaries defined by the BCAB.
