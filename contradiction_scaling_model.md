# Contradiction Scaling Model
**Date:** 2026-03-09
**Status:** ✅ CERTIFIED
**Phase Tag:** `v-chaos-certified`

---

## 1. Overview
This document formalizes the numerical model by which Contradiction (as signaled by `contradiction_flag=True` in the DGIC epistemic envelope) influences overall confidence. The system ensures that multi-signal aggregations correctly penalize confidence based on the *density* of contradictory signals, preserving epistemic uncertainty rather than resolving it forcefully.

## 2. The Penalty Model
The `enforcement_aggregator.py` calculates a **Contradiction Penalty** dynamically during signal fusion.

```python
# The aggregation algorithm snippet:
contradiction_ratio = contradictions / total_signals
contradiction_penalty = contradiction_ratio * 0.5
final_confidence = final_confidence * (1.0 - contradiction_penalty)
```

### 2.1 Variables
- `total_signals`: The number of discrete text chunks/signals analyzed in one API call.
- `contradictions`: The number of those signals explicitly flagged with `contradiction_flag=True`.
- `contradiction_ratio`: Ranging from `0.0` (zero contradiction) to `1.0` (all signals contradict).
- `contradiction_penalty`: Ranging from `0.0` to `0.5`, penalizing total confidence by up to 50%.

## 3. Propagation of Ambiguity
The model enforces that structural contradictions within an epistemic state inherently damage confidence:
1. **0% Contradiction (None):** Confidence penalty = 0%. Output confidence remains structurally sound.
2. **50% Contradiction:** Confidence penalty = 25%. Meaning a `HIGH` risk score with `0.8` raw confidence reduces its confidence to `0.6`.
3. **100% Contradiction (Total Confusion):** Confidence penalty = 50%. Even a perfectly confident signal drops to `0.5`, mathematically preventing high-confidence automation when the epistemic context is broken.

## 4. Bounded Risk
Separately, when the `epistemic_state` of *any* given signal yields `AMBIGUOUS`, its execution is limited. `AMBIGUOUS` directly applies a Risk Ceiling of `0.69`, trapping the risk artificially inside the `MEDIUM` bucket regardless of engine sentiment. This guarantees `AMBIGUOUS` inputs can never automatically trigger `HIGH` severity escalations downstream.
