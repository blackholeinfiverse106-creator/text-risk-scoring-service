# Multi-Signal Aggregator Architecture

**Version:** v1.0  
**Date:** 2026-03-16  
**Status:** FROZEN — Day 4 Submission

---

## 1. Overview

The Multi-Signal Aggregator is the central signal fusion point for AI Being enforcement intelligence. It deterministically combines text risk, behavior anomaly, policy violation, and external detector signals into a single enforcement-grade output signal.

**It does NOT:**
- Execute enforcement actions
- Mutate incoming signals
- Introduce probabilistic decision making
- Claim authority over downstream actions

---

## 2. System Topology

```
                    ┌──────────────────────────────┐
                    │    Inbound Signal Sources     │
                    │  (text, behavior, policy,     │
                    │   external detectors)         │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  Core Enforcement Adapter     │
                    │  core_enforcement_adapter.py  │
                    │  • Schema validation          │
                    │  • DGIC envelope parsing      │
                    │  • Signal rejection            │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  Multi-Signal Aggregator      │
                    │  signal_aggregator.py          │
                    │  • Weighted mean (by type)    │
                    │  • Contradiction penalty       │
                    │  • Epistemic scaling           │
                    │  • Bounded [0.0, 1.0]         │
                    └──────────────┬───────────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                   │
    ┌────────────▼────┐ ┌─────────▼──────┐ ┌─────────▼──────────┐
    │ DGIC Enforcement│ │ InsightBridge  │ │ Core Orchestration │
    │ Bridge          │ │ Telemetry      │ │ Payload            │
    │ (epistemic      │ │ (structured    │ │ (CoreEnforcement   │
    │  envelope)      │ │  JSON events)  │ │  Payload)          │
    └─────────────────┘ └────────────────┘ └────────────────────┘
```

---

## 3. Signal Types & Weighting

| Signal Type | Weight | Rationale |
|---|---|---|
| `POLICY_VIOLATION_SIGNAL` | 1.5 | Hard rules — highest priority |
| `BEHAVIOR_ANOMALY_SIGNAL` | 1.2 | Behavioral context strongly correlates with risk |
| `TEXT_RISK_SIGNAL` | 1.0 | Standard textual analysis baseline |
| `EXTERNAL_DETECTOR_SIGNAL` | 0.8 | Third-party signals treated more cautiously |

---

## 4. Aggregation Algebra

1. **Per-signal scoring:** Each `UnifiedSignal` is passed through the DGIC adapter (`adapt_dgic` → `apply_dgic_modifiers`) to apply epistemic state scaling
2. **Effective weight:** `W_type × confidence_score` (after DGIC scaling)
3. **Weighted mean:** `Σ(risk_i × W_eff_i) / Σ(W_eff_i)` across non-abstained signals
4. **Contradiction penalty:** `score × (1.0 − D × 0.5)` where `D` = contradiction density
5. **Clamping:** Final score bounded to `[0.0, 1.0]`
6. **Risk category:** `LOW` (< 0.3) · `MEDIUM` (0.3–0.69) · `HIGH` (≥ 0.7)

---

## 5. DGIC Epistemic Envelope

The aggregated output is wrapped in a DGIC-compliant envelope:

| Field | Source |
|---|---|
| `epistemic_confidence` | Aggregate confidence |
| `signal_lineage` | SHA-256 of aggregation hash + evidence chain |
| `collapse_state` | `STABLE` / `DEGRADED` / `COLLAPSED` |
| `truth_boundary_reference` | Aggregation hash (immutable) |

**Collapse state derivation:**

| Condition | State |
|---|---|
| No warnings, no abstentions | `STABLE` |
| Any epistemic warning or partial abstention | `DEGRADED` |
| All signals abstained | `COLLAPSED` |

---

## 6. Module Map

| Module | Responsibility |
|---|---|
| `app/signal_aggregator.py` | Core aggregation engine |
| `app/dgic_enforcement_bridge.py` | DGIC envelope wrapping |
| `app/insightbridge_telemetry.py` | Telemetry event emission |
| `app/core_enforcement_adapter.py` | Core orchestration adapter + validation |
| `app/unified_schemas.py` | Pydantic request models |
| `app/dgic_adapter.py` | DGIC epistemic state mapping |
| `app/insightbridge_adapter.py` | InsightBridge v4 contract mapping |

---

## 7. Absolute Invariants

| Invariant | Enforcement |
|---|---|
| `safety_metadata.is_decision` = `false` | Re-asserted on every output path |
| `safety_metadata.authority` = `"NONE"` | Re-asserted on every output path |
| `safety_metadata.actionable` = `false` | Re-asserted on every output path |
| `AMBIGUOUS` never escalates to `HIGH` | Risk ceiling 0.69 structurally enforced |
| `collapse_state` never derives authority | Informational only |
| No ML, no randomness | All operations are algebraic |
