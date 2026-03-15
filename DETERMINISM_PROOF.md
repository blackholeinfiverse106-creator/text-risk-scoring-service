# Determinism Proof — Multi-Signal Aggregator

**Version:** v1.0  
**Date:** 2026-03-16  
**Verdict:** ✅ PROVEN — Zero divergence across all scenarios

---

## 1. Proof Methodology

The multi-signal aggregator was subjected to **deterministic replay testing** — the same inputs
are fed through the aggregation pipeline N times, and the semantic output hash is compared
against a baseline. Any divergence constitutes a proof failure.

**Hash function:** SHA-256 over all semantically deterministic output fields:
- `aggregate_risk_score`, `aggregate_confidence`, `aggregate_risk_category`
- `signal_count`, `active_signal_count`, `abstained_signal_count`
- `contradiction_count`, `contradiction_density`, `contradiction_penalty_applied`
- `epistemic_warning`, `any_abstained`, `all_abstained`, `aggregation_hash`

**Excluded from hash:** Timestamps, log output, telemetry emission timing.

---

## 2. Replay Results

### Day 3 Automated Replay (`test_deterministic_signal_replay.py`)

| Scenario | Iterations | Divergences | Verdict |
|---|---|---|---|
| Single signal | 1,000 | 0 | ✅ PASS |
| Mixed 4 types | 1,000 | 0 | ✅ PASS |
| All contradicting | 1,000 | 0 | ✅ PASS |
| Partial abstention | 1,000 | 0 | ✅ PASS |
| All abstained | 1,000 | 0 | ✅ PASS |
| High volume (10 signals) | 1,000 | 0 | ✅ PASS |
| Ambiguous + entropy | 1,000 | 0 | ✅ PASS |
| **Total** | **7,000** | **0** | **✅ PROVEN** |

### Day 1 Engine Replay (`replay_harness.py`)

The underlying text engine was previously proven deterministic across 150,000 runs (10,000 iterations × 15 test cases). See `replay_proof_report.md`.

---

## 3. Structural Determinism Guarantees

The aggregator is deterministic by construction:

| Property | Mechanism |
|---|---|
| No randomness | No `random`, no sampling, no ML inference |
| No floating-point instability | All intermediate results are `round()`-ed to fixed precision |
| No ordering sensitivity | Signals processed in input order (caller-controlled) |
| No external state | No database, no cache, no network calls |
| No mutable shared state | All dataclasses are `frozen=True` |
| Deterministic hashing | SHA-256 over JSON with `sort_keys=True` |
| Deterministic DGIC mapping | Frozen lookup table, no branching on mutable state |

---

## 4. What Could Break Determinism (and doesn't)

| Potential Risk | Mitigation |
|---|---|
| Float precision drift | All scores clamped with `round()` to 2–6 decimal places |
| Dict ordering | All hash inputs serialised with `json.dumps(sort_keys=True)` |
| Thread-level reordering | Aggregator is stateless — no shared mutable state |
| Contradiction flag mutation | `DGICPayload` is `frozen=True` — cannot be modified post-creation |
| DGIC envelope tampering | Cryptographic seal verification via `compute_envelope_hash()` |

---

## 5. Reproducing the Proof

```bash
# Run the deterministic replay (7,000 executions)
python -m pytest tests/test_deterministic_signal_replay.py -v

# Run the original engine replay (150,000 executions)
python replay_harness.py
```

Both must exit with code 0 and report zero divergences.

---

## 6. Conclusion

The multi-signal aggregator produces **identical outputs for identical inputs** across all tested scenarios. This is guaranteed by structural design: no randomness, no mutable state, no external dependencies, no floating-point drift. The proof covers 7,000 aggregation executions across 7 diverse input configurations including contradictions, abstentions, mixed signal types, and high-volume streams.
