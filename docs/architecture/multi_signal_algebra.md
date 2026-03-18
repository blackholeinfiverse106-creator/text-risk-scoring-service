# Multi-Signal Aggregation Algebra
**Version:** v1.0  
**Status:** FROZEN — Day 2 Integration Release  
**Date:** 2026-03-06

---

## 1. Purpose

This document formalises the algebra governing how N independent risk signals are combined
into a single aggregate enforcement-grade score.

**Invariants that the algebra preserves (unconditionally):**
- Aggregate score ∈ [0.0, 1.0]
- Contradiction cannot silently increase the aggregate
- Abstained signals contribute zero mass to the aggregate
- Authority is never derived from the aggregation itself

---

## 2. Signal Space

Let S = {s₁, s₂, …, sₙ} be a set of N signals where each sᵢ is a tuple:

```
sᵢ = (rᵢ, cᵢ, eᵢ, dᵢ, aᵢ)

  rᵢ  ∈ [0.0, 1.0]   — risk score after DGIC modifier application
  cᵢ  ∈ [0.0, 1.0]   — confidence score after DGIC modifier application
  eᵢ  ∈ EpistemicState — {KNOWN, INFERRED, AMBIGUOUS, UNKNOWN}
  dᵢ  ∈ {0, 1}        — contradiction_flag (boolean, integer encoding)
  aᵢ  ∈ {0, 1}        — abstained (1 if epistemic state = UNKNOWN)
```

---

## 3. Active Signal Partition

```
A = { sᵢ ∈ S : aᵢ = 0 }   — Active signals (not abstained)
B = { sᵢ ∈ S : aᵢ = 1 }   — Abstained signals
```

If A = ∅ (all signals abstained): aggregate = 0.0, errors = ALL_SIGNALS_ABSTAINED.

---

## 4. Weighted Mean Aggregation

The raw aggregate score is computed as the **confidence-weighted arithmetic mean**
of the active risk scores:

```
         Σᵢ∈A  ( rᵢ × cᵢ )
R_raw = ──────────────────────
              Σᵢ∈A  cᵢ
```

**Edge case:** If Σcᵢ = 0 (all active signals have zero confidence):

```
         Σᵢ∈A rᵢ
R_raw = ──────────
           |A|
```

**Properties:**
- R_raw ∈ [0.0, max(rᵢ)] — the mean cannot exceed the maximum individual score
- R_raw is monotonically non-decreasing in the individual rᵢ values
- Higher-confidence signals contribute proportionally more to the aggregate
- Abstained signals (aᵢ=1) contribute zero mass

---

## 5. Contradiction Density

```
         Σᵢ∈S  dᵢ
D = ──────────────────
            N
```

D ∈ [0.0, 1.0]. Contradiction density is computed over **all** signals (including abstained),
because contradictions are a property of the DGIC intelligence layer, not a scoring artefact.

---

## 6. Contradiction Penalty

```
P = 1.0 - D × CONTRADICTION_PENALTY_FACTOR    (FACTOR = 0.5)

R_penalised = R_raw × P
```

**Bounds:**
- D = 0.0 → P = 1.0     → R_penalised = R_raw        (no contradiction, no penalty)
- D = 0.5 → P = 0.75    → R_penalised = 0.75 × R_raw
- D = 1.0 → P = 0.5     → R_penalised = 0.5 × R_raw  (all contradictory, halved)

**Invariant:** P ∈ [0.5, 1.0] ⊂ (0, 1] — the penalty never negates the score,
and never amplifies it. Risk cannot silently increase due to contradiction.

**Formal guarantee:** ∀D ∈ [0,1]: R_penalised ≤ R_raw

---

## 7. Global Score Ceiling

```
R_aggregate = min(R_penalised, MAX_AGGREGATE_SCORE)    (MAX = 1.0)
```

This caps the aggregate to the valid score domain, preventing floating-point
accumulation from pushing the score above 1.0.

---

## 8. Risk Category Derivation

```
         ⎧ "LOW"    if R_aggregate < 0.3
r_cat =  ⎨ "MEDIUM" if 0.3 ≤ R_aggregate < 0.7
         ⎩ "HIGH"   if R_aggregate ≥ 0.7
```

Thresholds mirror `engine.py` exactly — no additional calibration layer.

---

## 9. Aggregate Confidence

```
        Σᵢ∈A  cᵢ
C_agg = ──────────
           |A|
```

Simple arithmetic mean of active confidences. No probabilistic combination.
No variance, no standard error. This is a structural average — it represents
"what the active signals, on average, say about their own certainty."

---

## 10. Complete Aggregation Function

```
aggregate(S):
  A = { sᵢ : aᵢ = 0 }
  if |A| = 0: return abstention_response()

  D       = Σdᵢ / N
  R_raw   = Σ(rᵢ × cᵢ) / Σcᵢ   [or simple mean if Σcᵢ = 0]
  P       = clamp(1.0 - D × 0.5, 0.0, 1.0)
  R_agg   = min(R_raw × P, 1.0)
  r_cat   = category(R_agg)
  C_agg   = mean({ cᵢ : aᵢ = 0 })
  return AggregatedSignal(R_agg, C_agg, r_cat, ...)
```

---

## 11. Monotonicity Properties

| Property | Statement |
|---|---|
| **Risk ceiling** | R_agg ≤ 1.0 always |
| **Contradiction monotonicity** | ↑D → ↓R_agg (contradiction reduces, never inflates) |
| **Confidence weighting** | Higher-confidence signals dominate the mean |
| **Abstention isolation** | aᵢ=1 signals contribute zero to R_raw |
| **Non-negative** | R_agg ≥ 0.0 always |

---

## 12. Authority Invariants (Outside the Algebra)

The aggregation algebra produces a score, never a decision.

```
safety_metadata = { is_decision: false, authority: "NONE", actionable: false }
```

These are structurally re-asserted after every computation path.
No algebraic operation can modify them.
