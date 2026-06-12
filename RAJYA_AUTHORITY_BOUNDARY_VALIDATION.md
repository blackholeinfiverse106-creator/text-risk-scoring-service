# RAJYA Authority Boundary Validation

## Objective
Validate that the integration of RAJYA into the Sovereign Core runtime does not result in authority drift. The boundary between governance (RAJYA/Sarathi), orchestration (Sūtradhāra), deterministic epistemic evaluation (DGIC), and execution (Core) remains completely isolated and enforced at runtime.

---

## 1. Authority Ownership

### What RAJYA Owns
- **Final Enforcement Gate Verification:** Validating that all required authorities (Sarathi/DGIC) have explicitly approved the execution before it reaches the execution layer.
- **Structural Authorization Checks:** Validating the existence and exact format of `sarathi_decision`, `enforcement_verdict`, and `sarathi_execution_id`.
- **Pipeline Identifier Match:** Ensuring the `execution_id` provided by the downstream enforcement layers identically matches the original upstream request.

### What RAJYA Does Not Own
- **Decision Derivation:** RAJYA does NOT evaluate risk scores, entropy boundaries, or contextual signals to derive the `ALLOW`, `DENY`, or `ABSTAIN` verdicts.
- **Epistemic State:** RAJYA does NOT parse or consume the `DGICEpistemicStateInput`.
- **Action Execution:** RAJYA does NOT execute the action. It solely returns an `EXECUTION_APPROVED` or `REJECT` state to the orchestrator.
- **Token Minting:** RAJYA does NOT mint the enforcement token. It provides the approval that Sarathi uses to subsequently mint the token.

---

## 2. Influence Boundaries

### What RAJYA May Influence
- **Execution Proceed/Halt State:** RAJYA has absolute veto power over execution. If RAJYA returns `REJECT`, the orchestrator immediately halts the pipeline, emitting a `DENY` to downstream components without invoking the execution layers.
- **Orchestration Workflow Progression:** The orchestrator waits on the synchronous return of `validate_execution_request` before deciding whether to advance to Sarathi token minting.

### What RAJYA May Not Influence
- **Telemetry and Observability Payloads:** RAJYA cannot alter the trace hashes, execution records, or telemetry envelopes logged to the Bucket ledger or emitted via `emit_enforcement_telemetry`.
- **DGIC Modifiers and Risk Scores:** RAJYA cannot modify the computed risk metrics passed through the pipeline.
- **Sarathi Logic:** RAJYA cannot alter Sarathi's internal evaluation rules or its cryptographic signature generation.

---

## 3. Strict Boundary Verifications

### ❌ RAJYA Does NOT Become Orchestration Authority
RAJYA does not dictate the flow of the pipeline. It is invoked purely as a synchronous function by the Sūtradhāra Control Plane. Sūtradhāra controls the pipeline sequence:
`DGIC Ingestion -> Intelligence Computation -> Policy Derivation -> Enforcement Eval -> RAJYA -> Sarathi Mint -> Execute -> Observability`.
RAJYA is merely a stop-check in this sequence.

### ❌ RAJYA Does NOT Become Observability Authority
RAJYA emits standard logs for its pass/fail verification results, but it DOES NOT construct or emit the official `EnforcementTelemetryEvent`. The true execution record and bucket telemetry are written exclusively by Layer 4 (Core) and Layer 5 (Bucket).

### ❌ RAJYA Does NOT Become Trace Authority
The `trace_hash` (the immutable deterministic execution hash) is generated entirely within the Sūtradhāra orchestration layer and passed cleanly through the pipeline. RAJYA verifies the pipeline identifier (`execution_id`) but has no power to alter or generate the cryptographic `trace_hash`.

### ✅ RAJYA Remains an Authority Participant
RAJYA successfully acts as the penultimate gateway. It serves as the formal "Senate" validating the signatures, while leaving actual governance to Sarathi, computation to Intelligence, truth to Bucket, and execution to Core. The authority boundaries remain exactly intact.
