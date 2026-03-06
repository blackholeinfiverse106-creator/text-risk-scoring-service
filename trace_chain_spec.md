# Enforcement Signal Traceability Specification
**Version:** v1.0  
**Phase:** v-insightbridge-ready  
**Date:** 2026-03-06

---

## 1. Goal

InsightBridge must be able to forensically trace any enforcement decision it makes back to the raw intelligence that justified it. The Text Risk Scoring Service acts as a deterministic transformation layer in this chain, and must preserve cryptographic lineage.

---

## 2. The Chain of Evidence

The traceability chain consists of two cryptographic hashes:

1. **`epistemic_source_hash`** (Input Lineage)
2. **`enforcement_signal_id`** (Output Identity)

### 2.1 `epistemic_source_hash`
- **Origin:** DGIC (Intelligence Core).
- **Contents:** The SHA-256 hash of the raw text and contextual metadata that DGIC analyzed.
- **Scoring Service Obligation:** Unmodified **passthrough**. The `app/dgic_adapter.py` receives this as `evidence_hash` and embeds it directly into the output signal. The scoring service MUST NOT attempt to unwrap or recalculate this hash.

### 2.2 `enforcement_signal_id`
- **Origin:** Text Risk Scoring Service.
- **Contents:** The SHA-256 hash of the fully aggregated and scored output signal (the V4 Contract payload), sorted algebraically.
- **Scoring Service Obligation:** Computes this deterministically per `app/enforcement_aggregator.py` using `_compute_aggregation_hash` or a similar final-output hasher. By hashing the combined risk score, confidence, and epistemic source hash, the `enforcement_signal_id` tightly couples the risk assessment to the evidence that produced it.

---

## 3. InsightBridge Audit Verification

When an auditor (human or automated) challenges an InsightBridge enforcement action, the ledger query works backwards:

1. **Challenge:** Why was this request blocked?
2. **InsightBridge Log:** "Blocked due to Enforcement Signal ID: `a1b2c3d4...`"
3. **Scoring Service Log:** Signal ID `a1b2c3d4...` was output `X` with source hash `e5f6g7h8...`
4. **DGIC Log:** Source hash `e5f6g7h8...` corresponds to text payload `"kill attack bomb"` analyzed at `timestamp`.

Because all transformations are deterministic and hash-chained, any tampering at any layer (DGIC modifying the text post-facto, Scoring Service injecting risk, InsightBridge inventing a signal) immediately breaks the hash chain and is visible to the auditor. 
