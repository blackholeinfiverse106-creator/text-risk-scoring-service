# Fail-Closed Mapping Proof
**Date:** 2026-03-09
**Status:** ✅ CERTIFIED
**Phase Tag:** `v-insightbridge-ready`

---

## 1. Objective
To guarantee that when the Text Risk Scoring Service receives fundamentally broken, missing, or epistemically ungrounded (`UNKNOWN`) intelligence from the DGIC, it fails closed rather than failing open or escalating erroneously.

## 2. Abstraction Boundaries
The scoring engine evaluates the text independently, but its outputs are gated by the `dgic_adapter` and subsequently serialized for the consumer by the `insightbridge_adapter`. The system guarantees failure safety via the following cascade:

1. **Epistemic Mapping Failure:** If DGIC sends an `UNKNOWN` state, the adapter returns `scoring_mode = "ABSTAIN"`.
2. **Signal Zeroing:** The `apply_dgic_modifiers` pipeline intercepts the "ABSTAIN" mode. It forcefully zeros the `risk_score` and `confidence_score`, downgrades the category to `LOW`, and mutates the error block to include `EPISTEMIC_ABSTENTION`.
3. **Contract Serialization:** `insightbridge_adapter.map_to_insightbridge_contract` detects this specific epistemic-rooted error and enforces `abstention_flag = True`, guaranteeing `risk_score = 0.0`.

## 3. The Mapping Model

| Upstream Failure Mode | DGIC Status | Engine Action | Internal Result | InsightBridge Artifact |
|---|---|---|---|---|
| Complete nonsense/missing data | rejected by strictly typed schema validation | Fast-fail (Exception) | - | No signal emitted |
| No grounded context | `EpistemicState.UNKNOWN` | Execute & Intercept | `risk_score=0.0`, `error=EPISTEMIC_ABSTENTION` | `abstention_flag=True`, `risk_score=0.0` |

## 4. Conclusion
The service behaves as a deterministic, fail-closed enforcement layer. Any ambiguity regarding the legitimacy or context of the input resolves into explicit abstention, guaranteeing that consumer pipelines (like InsightBridge) will not take inappropriate enforcement action based on bad data.
