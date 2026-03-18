# Epistemic Enforcement Behavior Matrix
**Version:** v1.0  
**Status:** FROZEN — Day 1 Integration Release  
**Date:** 2026-03-06  
**Scope:** Text Risk Scoring Service + DGIC Integration Layer

---

## Purpose

This matrix defines the **complete, deterministic enforcement behaviour** of the integrated
system for each DGIC epistemic state. It is the authoritative reference for anyone consuming
the adapter output or building downstream enforcement logic.

> [!IMPORTANT]
> This matrix does NOT grant enforcement authority to the Text Risk Scoring Service.
> The service remains a **non-decision, non-authority scoring primitive** under all states.
> Enforcement decisions remain the exclusive responsibility of the consuming system.

---

## Full Behavior Matrix

| Epistemic State | Scoring Mode | Risk Score Effect | Confidence Effect | Risk Ceiling | Flags Emitted | Forbidden Actions |
|---|---|---|---|---|---|---|
| `KNOWN` | `NORMAL` | Unmodified (full engine output) | Unmodified (`× 1.0`) | None | None | Do not treat score as enforcement decision |
| `INFERRED` | `CONFIDENCE_SCALED` | Unmodified | Scaled: `conf × (1.0 − entropy × 0.4)` | None | None | Do not infer certainty from raw confidence |
| `AMBIGUOUS` | `RISK_BOUNDED` | Clamped to ≤ 0.69 (MEDIUM max) | Halved: `conf × 0.5` | **0.69** | `epistemic_warning: true` | Do NOT collapse to HIGH; do NOT treat as LOW |
| `UNKNOWN` | `ABSTAIN` | Forced to **0.0** | Forced to **0.0** | **0.0** | `epistemic_warning: true` | Do NOT emit risk signal; do NOT escalate |

---

## Row-by-Row Specification

### State: `KNOWN`

```
epistemic_state:    KNOWN
scoring_mode:       NORMAL
confidence_mult:    1.0 (identity)
risk_ceiling:       None
abstain:            False
epistemic_warning:  False
```

**What happens:**  
The engine result is passed through without modification. DGIC has high-confidence, grounded
evidence. The full raw score is trustworthy within the scoring model's precision bounds.

**Downstream guidance:**  
Treat confidence and risk scores at face value. Normal policy thresholds apply.

**Forbidden:**  
Treat this signal as a direct enforcement command. The score is information, not a decision.

---

### State: `INFERRED`

```
epistemic_state:    INFERRED
scoring_mode:       CONFIDENCE_SCALED
confidence_mult:    1.0 − (entropy_score × 0.4)   → range [0.6, 1.0] for entropy ∈ [0, 1]
risk_ceiling:       None
abstain:            False
epistemic_warning:  False
```

**What happens:**  
Risk score remains unmodified. Confidence is scaled down proportional to DGIC's entropy signal.
High entropy (uncertain inference) → lower confidence score. The risk score still reflects
keyword presence objectively; only the epistemic certainty marker is adjusted.

**Downstream guidance:**  
Weigh confidence score carefully. A HIGH risk_score with low confidence under INFERRED state
warrants additional human review rather than automated escalation.

**Examples:**

| entropy_score | confidence_mult | raw_conf | scaled_conf |
|---|---|---|---|
| 0.0 | 1.00 | 0.8 | 0.80 |
| 0.5 | 0.80 | 0.8 | 0.64 |
| 1.0 | 0.60 | 0.8 | 0.48 |

**Forbidden:**  
Use the unscaled confidence score as-is when `epistemic_state = INFERRED`.

---

### State: `AMBIGUOUS`

```
epistemic_state:    AMBIGUOUS
scoring_mode:       RISK_BOUNDED
confidence_mult:    0.5
risk_ceiling:       0.69
abstain:            False
epistemic_warning:  True
```

**What happens:**  
Risk score is hard-capped at 0.69 regardless of raw engine output. This keeps the worst-case
category at `MEDIUM`. Confidence is halved. The `epistemic_warning` flag is set.  

The adapter **does NOT collapse the ambiguity** — it does not choose `HIGH` or `LOW`.
It emits a bounded signal that says: "some risk indicators exist, but the epistemic
basis for escalation is insufficient."

**Downstream guidance:**  
Treat an `AMBIGUOUS` + `RISK_BOUNDED` signal as a **flag for human review**, not an
automated trigger. The `epistemic_warning` in `dgic_metadata` must be surfaced to
any downstream decision-making system.

**Why 0.69 as the ceiling?**  
At 0.69, the system is structurally incapable of emitting `HIGH` category under ambiguity.
The boundary between MEDIUM and HIGH is 0.70. The 0.01 margin is intentional.

**Forbidden:**
- Escalate an `AMBIGUOUS` signal to HIGH by overriding the ceiling externally
- Treat `epistemic_warning: true` as permission to enforce
- Collapse ambiguity by averaging with other signals without preserving the warning

---

### State: `UNKNOWN`

```
epistemic_state:    UNKNOWN
scoring_mode:       ABSTAIN
confidence_mult:    0.0
risk_ceiling:       0.0
abstain:            True
epistemic_warning:  True
```

**What happens:**  
Full abstention. `risk_score = 0.0`, `confidence_score = 0.0`, `risk_category = "LOW"`.
`errors.error_code = "EPISTEMIC_ABSTENTION"`. The system emits **no risk signal** because
there is no grounded epistemic basis for assessment.

The trigger_reasons list is cleared. The processed text was scored by the engine,
but that score is considered epistemically ungounded and is suppressed.

**Downstream guidance:**  
`EPISTEMIC_ABSTENTION` is not a "safe" ruling — it is the **absence of a ruling**.
Downstream systems must handle this state explicitly. Treat it as: "the scoring system
cannot assess this input with epistemic grounding; escalate to human review or hold."

**Forbidden:**
- Treat `risk_score = 0.0` under ABSTAIN as a "safe" `LOW` ruling
- Ignore the `errors.error_code = "EPISTEMIC_ABSTENTION"` field
- Proceed with automated enforcement pipeline on abstained signals

---

## Authority Boundary — All States

| Property | Value across ALL states |
|---|---|
| `safety_metadata.is_decision` | `false` — **always** |
| `safety_metadata.authority` | `"NONE"` — **always** |
| `safety_metadata.actionable` | `false` — **always** |

These are structurally re-asserted by `apply_dgic_modifiers()` after every path.
No DGIC field can change these values. This is not configurable.

---

## Flag Reference

| Flag | Field Location | Meaning |
|---|---|---|
| `epistemic_warning` | `dgic_metadata.epistemic_warning` | Signal has reduced epistemic grounding |
| `EPISTEMIC_ABSTENTION` | `errors.error_code` | System abstained; no risk signal emitted |
| `scoring_mode` | `dgic_metadata.scoring_mode` | How scores were modified by adapter |
| `evidence_hash` | `dgic_metadata.evidence_hash` | DGIC evidence audit trail token |

---

## Enforcement Pipeline Guidance

```
DGIC Output → DGICInput → adapt_dgic() → DGICAdapterResult
                                              │
              ┌───────────────────────────────┘
              │
              ▼
         analyze_text(text) → base engine result
              │
              ▼
         apply_dgic_modifiers(base_result, adapter_result)
              │
              ▼
         Modified result with dgic_metadata
              │
              ├─ abstain=True?  → Surface EPISTEMIC_ABSTENTION to human review queue
              ├─ epistemic_warning=True?  → Do NOT auto-enforce; queue for review
              ├─ scoring_mode=INFERRED?   → Require elevated confidence threshold
              └─ scoring_mode=NORMAL?     → Apply standard policy thresholds
```

> [!WARNING]
> The integrated service sits **between** Intelligence Core and Execution Gate.
> It is a signal layer, not a decision gate. The Execution Gate must implement its own
> enforcement thresholds and must not treat any score from this service as a direct command.
