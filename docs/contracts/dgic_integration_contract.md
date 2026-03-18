# DGIC Integration Contract
**Version:** v1.0  
**Status:** FROZEN — Day 1 Integration Release  
**Date:** 2026-03-06  
**Supersedes:** N/A (first DGIC integration contract)

---

## 1. Purpose

This document defines the **sealed contract** governing the interface between the
Deterministic Graph Intelligence Core (DGIC) and the Text Risk Scoring Service adapter layer
(`app/dgic_adapter.py`).

It specifies:
- What DGIC is allowed to send
- What the adapter is allowed to do with those inputs
- What the adapter guarantees to produce
- What is explicitly forbidden

---

## 2. DGIC Input Contract

### Input Schema (`DGICInput`)

| Field | Type | Required | Constraints |
|---|---|---|---|
| `epistemic_state` | `EpistemicState` enum | **Yes** | Must be one of: `KNOWN`, `INFERRED`, `AMBIGUOUS`, `UNKNOWN` |
| `entropy_score` | `float` | **Yes** | `[0.0, 1.0]` inclusive. 0.0 = no entropy; 1.0 = max entropy |
| `contradiction_flag` | `bool` | **Yes** | `True` if DGIC detected internal evidence contradictions |
| `collapse_flag` | `bool` | **Yes** | `True` if DGIC collapsed a superposition; MUST NOT be used to derive authority |
| `evidence_hash` | `str` | **Yes** | Non-empty, opaque SHA-256 fingerprint of DGIC's evidence chain |

### Validation Error Codes

| Code | Meaning |
|---|---|
| `INVALID_DGIC_TYPE` | Input is not a `DGICInput` instance |
| `INVALID_EPISTEMIC_STATE` | `epistemic_state` is not a valid `EpistemicState` member |
| `INVALID_ENTROPY_TYPE` | `entropy_score` is not a numeric type |
| `INVALID_ENTROPY_RANGE` | `entropy_score` is outside `[0.0, 1.0]` |
| `INVALID_CONTRADICTION_FLAG` | `contradiction_flag` is not `bool` |
| `INVALID_COLLAPSE_FLAG` | `collapse_flag` is not `bool` |
| `INVALID_EVIDENCE_HASH` | `evidence_hash` is absent or empty |

---

## 3. Adapter Output Contract (`DGICAdapterResult`)

| Field | Type | Description |
|---|---|---|
| `scoring_mode` | `str` | One of: `NORMAL`, `CONFIDENCE_SCALED`, `RISK_BOUNDED`, `ABSTAIN` |
| `confidence_multiplier` | `float` | Factor applied to raw `confidence_score`. Always in `[0.0, 1.0]` |
| `risk_ceiling` | `float \| None` | Upper bound on `risk_score`. `None` = no ceiling |
| `epistemic_warning` | `bool` | `True` if epistemic state is `AMBIGUOUS` or `UNKNOWN` |
| `abstain` | `bool` | `True` if the system must suppress the risk signal entirely |
| `evidence_hash` | `str` | Passed through unmodified from `DGICInput.evidence_hash` |
| `epistemic_state` | `EpistemicState` | Original state retained for audit |

---

## 4. Epistemic State → Scoring Mode Mapping (FROZEN)

| Epistemic State | Scoring Mode | Confidence Multiplier | Risk Ceiling | Abstain | Warning |
|---|---|---|---|---|---|
| `KNOWN` | `NORMAL` | `1.0` | `None` | `False` | `False` |
| `INFERRED` | `CONFIDENCE_SCALED` | `1.0 − entropy × 0.4` | `None` | `False` | `False` |
| `AMBIGUOUS` | `RISK_BOUNDED` | `0.5` | `0.69` | `False` | `True` |
| `UNKNOWN` | `ABSTAIN` | `0.0` | `0.0` | `True` | `True` |

> [!IMPORTANT]
> **The `AMBIGUOUS` risk ceiling of `0.69`** is deliberate. It keeps the worst-case score
> in the `MEDIUM` zone. The system is **structurally incapable** of escalating an ambiguous
> DGIC signal to `HIGH`. Ambiguity is preserved, not resolved.

> [!IMPORTANT]
> **`contradiction_flag` and `collapse_flag`** do NOT alter the scoring mode.
> They are passed through in `dgic_metadata` for audit purposes only.
> No enforcement authority may be derived from either flag.

---

## 5. Modified Score Response Shape (`apply_dgic_modifiers` output)

All standard v3 contract fields are present. One additional sidecar field is added:

```json
{
  "risk_score":       0.45,
  "confidence_score": 0.40,
  "risk_category":    "MEDIUM",
  "trigger_reasons":  ["Detected fraud keyword: scam"],
  "processed_length": 12,
  "safety_metadata": {
    "is_decision": false,
    "authority":   "NONE",
    "actionable":  false
  },
  "errors": null,
  "dgic_metadata": {
    "epistemic_state":   "AMBIGUOUS",
    "scoring_mode":      "RISK_BOUNDED",
    "epistemic_warning": true,
    "evidence_hash":     "abc123..."
  }
}
```

**Abstention response** (`UNKNOWN` state):
```json
{
  "risk_score": 0.0, "confidence_score": 0.0, "risk_category": "LOW",
  "trigger_reasons": [], "processed_length": 0,
  "safety_metadata": { "is_decision": false, "authority": "NONE", "actionable": false },
  "errors": {
    "error_code": "EPISTEMIC_ABSTENTION",
    "message": "Epistemic abstention: no grounded evidence available. Risk signal suppressed by DGIC UNKNOWN state."
  },
  "dgic_metadata": {
    "epistemic_state": "UNKNOWN", "scoring_mode": "ABSTAIN",
    "epistemic_warning": true, "evidence_hash": "..."
  }
}
```

---

## 6. Absolute Invariants (Structurally Enforced)

| Invariant | Enforcement |
|---|---|
| `safety_metadata.is_decision` is **always** `false` | `apply_dgic_modifiers()` re-asserts after every path |
| `safety_metadata.authority` is **always** `"NONE"` | `apply_dgic_modifiers()` re-asserts after every path |
| `safety_metadata.actionable` is **always** `false` | `apply_dgic_modifiers()` re-asserts after every path |
| `AMBIGUOUS` state is **never collapsed** to a decision | `RISK_BOUNDED` mode emits a signal; no binary decision is made |
| `evidence_hash` is **never modified** | Passed through `DGICAdapterResult` and `dgic_metadata` verbatim |
| No enforcement authority derived from `collapse_flag` | Flag is logged only; excluded from scoring logic |

---

## 7. Forbidden Operations

The adapter **MUST NOT**:

| # | Forbidden Operation |
|---|---|
| F-1 | Modify the `epistemic_state` received from DGIC |
| F-2 | Derive `authority != "NONE"` from any DGIC field |
| F-3 | Collapse `AMBIGUOUS` state into a binary `HIGH` or `LOW` decision |
| F-4 | Set `is_decision = true` for any epistemic state |
| F-5 | Inspect `evidence_hash` content for scoring |
| F-6 | Use `collapse_flag` to escalate risk_score |
| F-7 | Introduce randomness, ML models, or probabilistic inference |
| F-8 | Return a risk_score > `risk_ceiling` when a ceiling is applied |

---

## 8. Stability Guarantees

| Element | Guarantee |
|---|---|
| `EpistemicState` enum values | Stable |
| `DGICInput` field names and types | Stable |
| `DGICAdapterResult` field names | Stable |
| Scoring mode mapping table | Stable (this document is the source of truth) |
| `AMBIGUOUS` risk ceiling (0.69) | Stable |
| `INFERRED` entropy scaling factor (0.4) | Stable |
| `dgic_metadata` field names | Stable |
| `dgic_metadata` values (content) | Unstable (informational) |
| Error messages in `EPISTEMIC_ABSTENTION` | Unstable (human-readable) |

---

## 9. Integration Notes (Day 1)

- The adapter is **library-only** in Day 1. `app/main.py` is unchanged.
- `dgic_metadata` is a sidecar field outside the frozen v3 API contract.
  It is returned by `apply_dgic_modifiers()` for library consumers.
- The existing `validate_output_contract()` applies to the base engine result only.
  Downstream API extension (v4) is a future day deliverable.
