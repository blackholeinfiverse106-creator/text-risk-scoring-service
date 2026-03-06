# Fail-Closed Mapping Specification
**Version:** v1.0  
**Phase:** v-insightbridge-ready  
**Date:** 2026-03-06

---

## 1. Goal

When upstream components (DGIC or the core network) produce invalid, corrupted, or fundamentally `UNKNOWN` inputs, the text-risk-scoring-service must behave deterministically.

**Strict Mandate:** If upstream is invalid, the service must **abstain**, not escalate. Default-deny logic on safety systems frequently produces false-positive enforcement actions. We do not have the authority to err on the side of "assuming high risk" when the input is malformed.

---

## 2. Invalid Upstream Scenarios

1. **Epistemic State = `UNKNOWN`**: The intelligence layer explicitly admits total uncertainty.
2. **Missing `evidence_hash`**: Upstream lost track of the hash lineage.
3. **Invalid Schema**: DGIC input is structurally broken, type-confused, or contains entropy `> 1.0`.
4. **All Signals Rejected**: In multi-signal contexts, every signal was individually discarded or abstained.

---

## 3. The Fail-Closed Abstention Sequence

When any invalid scenario is reached:
1. `risk_score` is forced to `0.0`.
2. `bounded_confidence` is forced to `0.0`.
3. `abstention_flag` is set to `True`.
4. `decision` remains `null`.
5. `authority` remains `"NONE"`.

### Why risk_score = 0.0?
A risk score of `0.0` combined with `abstention_flag = True` means "I have zero valid evidence to declare a risk." This hands the problem safely down to InsightBridge to decide what to do about the failure without accidentally tripping high-risk enforcement gates.

Escalating risk (e.g., arbitrarily setting `1.0` to block) would constitute the scoring service making a unilateral, un-evidenced downstream decision.

---

## 4. Contract Enforcement

The `enforcement_output_contract_v4.json` mathematically requires that if a message is sent out, the invariants MUST hold. If the service completely panics and crashes due to extreme corruption (e.g., memory exhaustion), it fails closed by sending *nothing*, breaking the circuit entirely, which InsightBridge will detect via timeout or missing messages.
