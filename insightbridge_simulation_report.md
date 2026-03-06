# InsightBridge Integration Simulation Report
**Date:** 2026-03-06T11:08:12Z  
**Phase:** v-insightbridge-ready  
**Status:** ✅ CERTIFIED  

---

## Consumer Statistics

| Metric | Count |
|---|---|
| Valid Signals Ingested | 6 |
| Rejected (Schema Failure) | 3 |
| Rejected (Invariant/Authority Breach) | 0 |
| Downstream Actions (BLOCKs) Derived | 0 |
| Downstream Abstentions Handled | 1 |

---

## Separation of Concerns Proven

InsightBridge explicitly implements the decision logic (e.g., `IF risk >= 0.7 AND conf > 0.8 THEN BLOCK`). The Text Risk Scoring Service outputs only deterministic risk metrics under extreme non-authority constraints (`decision=null`, `authority="NONE"`).

As demonstrated in this simulation, any attempt by the scoring service to mutate its contract to claim authority (`decision="BLOCK"`) is immediately structurally rejected by the InsightBridge schema and invariant checks.

## Simulation Ledger

| `enforcement_signal_id` | `risk_score` | `confidence` | InsightBridge Action Log |
|---|---|---|---|
| `4d4a1529dc35379d...` | `0.0` | `1.0` | PASS (Low/Medium Risk -> InsightBridge Pass) |
| `574589a92bad79ca...` | `0.8` | `0.8` | QUEUE_HUMAN_REVIEW (High Risk, Low/Mod Confidence -> Downstream Review) |
| `8ede6bbd2dea0ae7...` | `0.6` | `0.8` | PASS (Low/Medium Risk -> InsightBridge Pass) |
| `f788ca888d6e6986...` | `0.2` | `0.25` | PASS (Low/Medium Risk -> InsightBridge Pass) |
| `e37efbc5f11c5715...` | `0.3` | `1.0` | PASS (Low/Medium Risk -> InsightBridge Pass) |
| `6e1f66de8bce7e81...` | `0.0` | `0.0` | PASS (Upstream Abstained -> InsightBridge Fail-Open Fallback) |
| `6df73d31a817f1cb...` | `0.4` | `0.8` | REJECTED (Schema/Invariant): 'BLOCK' is not of type 'null' |
| `6df73d31a817f1cb...` | `0.4` | `0.8` | REJECTED (Schema/Invariant): 'NONE' was expected |
| `2141dbab6f36d01b...` | `0.0` | `1.0` | REJECTED (Schema/Invariant): 'epistemic_source_hash' is a required property |


**Phase Tag:** `v-insightbridge-ready`
