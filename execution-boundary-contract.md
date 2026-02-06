# Execution Boundary Contract

**Integration Protocol for Enforcement Systems**

This document defines the strict protocol that any **Enforcement System** (e.g., Workflow Executor, Moderator Bot, Policy Engine) must adhere to when consuming signals from the **Text Risk Scoring Service**.

## 1. Non-Authority Acknowledgement

By integrating with this service, the Enforcement System acknowledges:
> "The Text Risk Scoring Service provides **signals**, not **decisions**. It possesses **zero execution authority**. All actions taken based on these signals are the sole responsibility of the Enforcement System."

## 2. Signal Consumption Rules

### 2.1 Score Interpretation
*   **Raw Scores (0.0 - 1.0):** MUST be treated as scalar inputs for a policy threshold, NEVER as absolute truth.
*   **Threshold Management:** The Enforcement System MUST define its own thresholds.
    *   *Violation:* Using the Scoring Service's internal thresholds as final policy without review.
*   **Confidence Dependency:** Signals with `confidence_score < 0.8` (or defined threshold) MUST NOT trigger automated enforcement actions to remove content.

### 2.2 Category Interpretation
*   "HIGH" risk category is a **tag**, not a convicting verdict.
*   IT DOES NOT mean "Illegal".
*   IT DOES NOT mean "Violates Policy".
*   IT MEANS "Features match high-risk patterns".

## 3. Structural Impossibility of Misuse (Fail-Safe Design)

The Enforcement System must implement the following safeguards:

### 3.1 The "Two-Key" Rule
Automated destructive actions (Ban, Delete) MUST require **two independent signals** or **human confirmation**.
*   *Exception:* Hard-coded hash matching of known illegal content (CSAM), which is outside the scope of heuristic scoring.

### 3.2 Feature Flags & Kill Switches
The integration MUST include a "zombie switch" to completely ignore risk scores if the Scoring Service behaves erratically (e.g., flagging 100% of content).

### 3.3 Rate Limiting Action
The Enforcement System MUST rate-limit *automated actions* to prevent "cascading censorship" in the event of a Scoring Service false-positive loop.

## 4. Ambiguity & Failure Modes

### 4.1 Fail Closed (Safety) vs. Fail Open (Availability)
*   **Ambiguity:** If the Scoring Service returns `risk_category: "UNKNOWN"` or `confidence_score` is low:
    *   **DEFAULT ACTION:** DO NOT ENFORCE. Flag for human review.
*   **Service Failure:** If the Scoring Service is unreachable or returns 500:
    *   **DEFAULT ACTION:** Assume "SAFE" or "QUEUE FOR REVIEW" depending on latency requirements. NEVER Assume "GUILTY".

### 4.2 Error Handling
*   `errors` field in response MUST be checked.
*   If `errors` is not null, the signal is INVALID.

## 5. Audit & Traceability

The Enforcement System MUST log:
1.  The `request_id` (if available) or input hash.
2.  The raw `risk_score` received.
3.  The `trigger_reasons` provided.
4.  The **Policy Rule** that mapped the score to an action.
    *   *Correct Log:* "Action: HIDE. Reason: Score 0.95 exceeded Policy Threshold 0.9."
    *   *Incorrect Log:* "Action: HIDE. Reason: Scorer said so."

## 6. Contract Verification

Verified Enforcement Systems must pass the following checks:
- [ ] Does it have a policy layer separate from the scoring layer?
- [ ] Does it stop acting when confidence is low?
- [ ] Does it have a circuit breaker for mass-enforcement?
- [ ] Does it log the *policy decision* distinct from the *risk score*?

## 7. Signed Waiver

*Integration with the Text Risk Scoring Service constitutes acceptance of this contracts' limitations on liability and authority.*
