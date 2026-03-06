# Confidence Scaling Proof — Multi-Signal Weighted Confidence
**Version:** v1.0  
**Status:** FROZEN — Day 2 Integration Release  
**Date:** 2026-03-06

---

## 1. Purpose

This document proves that the aggregate confidence score produced by the enforcement
aggregator is:

1. **Deterministic** — same inputs always produce the same output
2. **Bounded** — aggregate confidence ∈ [0.0, 1.0]
3. **Non-probabilistic** — no statistical inference, no Bayesian combination, no variance
4. **Structurally conservative** — it does not claim higher certainty than individual signals

---

## 2. Per-Signal Confidence (Input)

Each signal's confidence score entering the aggregator is already the output of the
DGIC per-signal confidence scaling (see `dgic_integration_contract.md`):

```
c_per_signal = engine_confidence × dgic_confidence_multiplier
```

Where the multiplier depends on epistemic state:
- `KNOWN`:     × 1.0   (identity)
- `INFERRED`:  × (1.0 − entropy × 0.4)   ∈ [0.6, 1.0] for entropy ∈ [0, 1]
- `AMBIGUOUS`: × 0.5
- `UNKNOWN`:   × 0.0   (but signal is abstained; excluded from aggregation)

So c_per_signal ∈ [0.0, 1.0] is guaranteed by the DGIC adapter.

---

## 3. Aggregate Confidence Definition

```
        Σᵢ∈A  cᵢ
C_agg = ──────────
           |A|
```

Where A = { sᵢ : aᵢ = 0 } is the set of non-abstained signals.

This is a **simple arithmetic mean**, not a probabilistic combination.

---

## 4. Boundedness Proof

**Theorem:** C_agg ∈ [0.0, 1.0]

**Proof:**
```
∀i ∈ A: 0.0 ≤ cᵢ ≤ 1.0   [per DGIC adapter guarantee]

Lower bound:
  Σcᵢ ≥ 0   and |A| ≥ 1  ⟹  C_agg ≥ 0.0  ✓

Upper bound:
  Σcᵢ ≤ Σ 1.0 = |A|
  C_agg = Σcᵢ / |A| ≤ |A| / |A| = 1.0  ✓
```
QED. C_agg ∈ [0.0, 1.0]. ∎

---

## 5. Determinism Proof

**Theorem:** For identical input signals (same text, same DGICInputs), C_agg is identical.

**Proof chain:**
```
1. analyze_text(text) is deterministic [proven in determinism-proof.md, 150k runs]
2. adapt_dgic(dgic) is deterministic [pure function of frozen DGICInput]
3. apply_dgic_modifiers(base, adapter) is deterministic [pure function of both]
4. _score_single_signal() is deterministic [composition of above]
5. Iteration order is fixed (enumerate over sorted input list)
6. Arithmetic mean of a fixed ordered list is deterministic
7. Therefore C_agg is deterministic. ∎
```

---

## 6. Why Arithmetic Mean, Not Probability Combination

Common probabilistic confidence combination methods include:
- Noisy-OR: `1 − Π(1 − cᵢ)` — inflates composite confidence
- Fisher's method — requires p-values and statistical assumptions
- Dempster-Shafer — requires belief functions, not point estimates

All probabilistic methods are **forbidden** by the system constraint:
> "No probabilistic inference."

The arithmetic mean has the following desirable structural properties:

| Property | Arithmetic Mean | Noisy-OR |
|---|---|---|
| Bounded in [0,1] | ✅ | ✅ |
| Deterministic | ✅ | ✅ |
| Non-inflating (cannot exceed max individual confidence) | ✅ | ❌ |
| No statistical assumptions | ✅ | ❌ |
| Monotone in inputs | ✅ | ✅ |

The arithmetic mean is the uniquely appropriate choice under the no-probabilistic-inference constraint,
and it is structurally CONSERVATIVE — adding a low-confidence signal can only
decrease or maintain the aggregate confidence, preventing false certainty claims.

---

## 7. Interaction with Contradiction Penalty

The contradiction penalty operates on the **risk score**, not the confidence score.
They are independent:

```
R_agg = min(R_raw × P(D), 1.0)   ← penalty on risk score
C_agg = mean(cᵢ for i ∈ A)        ← no penalty on confidence
```

This is intentional: contradiction signals epistemic instability in DGIC, which is
properly expressed in confidence per signal (already scaled by the DGIC adapter).
Applying a second penalty on confidence at the aggregate level would double-count
the contradiction signal.

---

## 8. Edge Cases

| Scenario | C_agg | Rationale |
|---|---|---|
| Single signal, confidence=1.0 | 1.0 | Pass-through, |A|=1 |
| All signals AMBIGUOUS (c=0.45 each) | 0.45 | Mean of equal values = same value |
| Mix of KNOWN (1.0) and INFERRED (0.6) | 0.8 | Mean = (1.0+0.6)/2 |
| All signals abstained | 0.0 | |A|=0, returns ALL_SIGNALS_ABSTAINED |
| Single signal, zero engine confidence | 0.0 | Valid boundary |

---

## 9. Stability Guarantee

The confidence model is **sealed**:
- The arithmetic mean formula is not runtime-configurable.
- No caller-supplied weights are accepted.
- No per-category or per-state differential weighting.

Caller-supplied weights would create a vector for externally biasing the aggregate
confidence, which could be used to manufacture apparent certainty — a form of
epistemic contamination.
