# State Definition – Deterministic Policy Learning Engine

This document defines the concept of **state** used by the deterministic
policy learning engine that extends the Text Risk Scoring Service.

The objective of this definition is to ensure that policy learning remains
**deterministic, auditable, replayable, and explainable**.

---

## 1. Definition of State

In this system, **state** represents the complete and explicit configuration
that governs how risk and confidence are interpreted at a specific point
in the system’s evolution.

State answers the following question:

> *Given the same input and the same state, will the system behave identically?*

The answer must always be **yes**.

---

## 2. What State Is Not

To preserve determinism and auditability, the state explicitly **does not include**:

- Raw input text
- User identity or personal data
- Historical input samples
- Runtime timestamps
- Random values
- Execution environment metadata

State is **not memory of past data**.  
State is a **snapshot of policy configuration**.

---

## 3. Components of the State

The state consists of a **minimal, explicit, and serializable** set of parameters.

---

### 3.1 Risk Configuration Parameters

These parameters define how risk scoring is performed:

- Keyword category weights
- Per-category score saturation caps
- Risk classification thresholds (LOW / MEDIUM / HIGH)
- Global risk normalization limits

These parameters may evolve over time **only through controlled policy updates**.

---

### 3.2 Policy Version Identifier

Each state includes a unique, monotonically increasing identifier:

- `policy_version`

This enables:
- Auditability of historical decisions
- Deterministic replay of outcomes
- Traceability of policy evolution

Once created, a policy version is **immutable**.

---

### 3.3 Confidence Model Parameters

State also includes parameters that influence confidence estimation, such as:

- Confidence decay rates
- Minimum and maximum confidence bounds
- Ambiguity or adversarial penalties

These parameters affect **confidence interpretation**, not raw risk scoring.

---

## 4. State Immutability and Versioning

A fundamental rule of the system is:

> **State is immutable once created.**

When learning occurs:
- A **new state** is derived from the previous state
- The previous state remains unchanged
- The policy version is incremented

This ensures:
- Full auditability
- Deterministic replay
- No retroactive mutation of decisions

---

## 5. State Serialization and Replayability

The state must be:

- Fully serializable (e.g., JSON-compatible)
- Persistable to storage
- Reloadable without information loss

Given:
- The same serialized state
- The same input text

The system must always produce the **same output**.

This property is essential for debugging, compliance, and trust.

---

## 6. Determinism Guarantee

The system guarantees:

- No randomness in state values
- No time-dependent state transitions
- No environment-dependent behavior

All state transitions are:
- Rule-based
- Explicit
- Logged
- Reproducible

---

## 7. Design Rationale

This strict definition of state ensures that:

- Learning remains transparent
- Policy evolution is explainable
- Risk interpretation is stable
- Errors can be traced to a specific policy version

By constraining what state can contain, the system avoids
uncontrolled drift and opaque behavior.

---

## 8. Summary

In summary:

- State represents **policy configuration**, not historical data
- State is immutable and versioned
- Learning creates new states without mutating past ones
- Determinism and replayability are preserved by design

This definition forms the foundation of the deterministic
policy learning engine.