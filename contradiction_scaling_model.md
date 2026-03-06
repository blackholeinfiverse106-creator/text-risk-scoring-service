# Contradiction Density Scaling Model
**Version:** v1.0  
**Status:** FROZEN — Day 2 Integration Release  
**Date:** 2026-03-06

---

## 1. Problem Statement

When multiple signals are aggregated, some will carry `contradiction_flag=True` from DGIC,
indicating that the upstream intelligence core detected internal evidence contradictions
while producing that signal.

**The rule:** Risk cannot silently increase when signals conflict.

If contradiction flags are ignored, a naive sum or mean aggregator could still produce
a high aggregate score from contradictory evidence — effectively laundering contradictions
into apparent certainty. This is a form of epistemic contamination.

---

## 2. Contradiction Density Definition

```
         # signals with contradiction_flag = True
D = ─────────────────────────────────────────────────
                    N  (total signals)
```

- D ∈ [0.0, 1.0]
- D = 0.0 → no contradictions in any signal
- D = 1.0 → every signal is marked contradictory by DGIC
- Computed over **all** N signals, including abstained ones

Abstracting contradiction density over all signals (not just active ones) is intentional:
a DGIC contradiction in an abstained signal still indicates epistemic instability in the
upstream intelligence chain — this must be visible in the aggregate even when the
abstained signal contributes zero risk mass.

---

## 3. Penalty Function

```
P(D) = 1.0 - D × CONTRADICTION_PENALTY_FACTOR
```

Where `CONTRADICTION_PENALTY_FACTOR = 0.5` (constant, not configurable).

The aggregate score is penalised multiplicatively:

```
R_penalised = R_raw × P(D)
```

**Formal constraint:** P is clamped to [0.0, 1.0] before application.

---

## 4. Penalty Value Table

| D (density) | P(D) | Effect on R_raw |
|---|---|---|
| 0.00 | 1.000 | No penalty — full score passes through |
| 0.10 | 0.950 | -5% |
| 0.25 | 0.875 | -12.5% |
| 0.50 | 0.750 | -25% |
| 0.75 | 0.625 | -37.5% |
| 1.00 | 0.500 | -50% — maximum penalty |

At maximum contradiction density (all signals contradictory), the aggregate is **halved**.
This is the **worst-case penalty** — it does not zero the score, because:
1. The text content may still exhibit genuine risk keywords (objective scoring).
2. Zeroing would be an enforcement decision — which this system cannot make.

---

## 5. Monotonicity Proof

**Theorem:** ∀D₁, D₂ ∈ [0,1]: D₁ ≤ D₂ ⟹ P(D₁) ≥ P(D₂)

**Proof:**
```
P(D) = 1.0 - D × 0.5
dP/dD = -0.5  < 0   (strictly decreasing)
```

Therefore P is monotonically decreasing in D.
Since R_penalised = R_raw × P(D), and R_raw is fixed:
increasing D monotonically decreases R_penalised — never increases it. ∎

**Corollary:** Contradiction can only reduce or preserve the aggregate score, never inflate it.

---

## 6. Interaction with Epistemic States

Contradiction density operates at the **aggregation layer**, independent of the epistemic
state mapping applied per-signal. The interaction is:

| Epistemic State | contradict flag=True | Combined Effect |
|---|---|---|
| `KNOWN` | Possible | Score passes through (NORMAL), but density penalty applied at aggregate |
| `INFERRED` | Possible | Confidence already scaled down, penalty also applied |
| `AMBIGUOUS` | Possible | Score already capped at 0.69; density penalty reduces further |
| `UNKNOWN` | Possible | Signal abstains (score=0); still counted in density numerator |

> [!IMPORTANT]
> `contradiction_flag` and `EpistemicState.AMBIGUOUS` are independent concepts.  
> A signal can be `KNOWN` with `contradiction_flag=True` — DGIC resolved the contradiction
> but flagged it. A signal can be `AMBIGUOUS` with `contradiction_flag=False` — the ambiguity
> may stem from insufficient evidence rather than internal conflict.

---

## 7. What the Penalty Does NOT Do

| Forbidden Operation | Reason |
|---|---|
| Set aggregate = 0.0 on contradiction | That would be an enforcement decision |
| Escalate score on low contradiction | Risk monotonicity must hold |
| Differentiate between signal sources | All signals are treated symmetrically |
| Apply different penalty per epistemic state | Penalty is purely density-based |

---

## 8. Design Rationale

The `CONTRADICTION_PENALTY_FACTOR = 0.5` was selected such that:
- At D=1.0, the system still emits a non-zero signal if risk keywords exist
- The penalty is large enough to be meaningful in downstream policy thresholds
- The formula is simple enough to be independently verified by auditors

The factor is a **sealed constant** — it cannot be configured at runtime or per-caller.
Caller-supplied penalty factors would create an authority-derivation vector.
