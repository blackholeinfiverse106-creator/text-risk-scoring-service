# Aggregation Replay Proof
**Date:** 2026-03-06T11:27:11Z  
**Status:** ✅ CERTIFIED  
**Total Calls:** 10000  
**Total Divergences:** 0  
**Result:** ZERO DIVERGENCE — DETERMINISM CERTIFIED

---

## Configuration

| Parameter | Value |
|---|---|
| Corpus size | 20 fixed multi-signal test cases |
| Iterations per case | 500 |
| Total aggregation calls | 10000 |
| Hash function | SHA-256 over JSON-serialised AggregatedSignal (sorted keys) |
| CONTRADICTION_PENALTY_FACTOR | 0.5 |
| MAX_AGGREGATE_SCORE | 1.0 |

---

## Case Results

| Label | Sigs | Active | Agg Score | Category | Confidence | Contra D | Penalty | Diverg | Status |
|---|---|---|---|---|---|---|---|---|---|
| `two_known_safe` | 2 | 2 | `0.00` | `LOW` | `1.00` | `0.00` | `1.000` | 0 | PASS  |
| `two_known_high` | 2 | 2 | `0.69` | `MEDIUM` | `0.90` | `0.00` | `1.000` | 0 | PASS  |
| `known_inferred_no_contra` | 2 | 2 | `0.48` | `MEDIUM` | `0.72` | `0.00` | `1.000` | 0 | PASS  |
| `known_inferred_high_entropy` | 2 | 2 | `0.60` | `MEDIUM` | `0.82` | `0.00` | `1.000` | 0 | PASS  |
| `ambiguous_known` | 2 | 2 | `0.29` | `LOW` | `0.45` | `0.00` | `1.000` | 0 | PASS ⚠️ |
| `two_ambiguous` | 2 | 2 | `0.60` | `MEDIUM` | `0.40` | `0.00` | `1.000` | 0 | PASS ⚠️ |
| `unknown_plus_known` | 2 | 1 | `0.40` | `MEDIUM` | `0.80` | `0.00` | `1.000` | 0 | PASS ⚠️ |
| `all_unknown` | 2 | 0 | `0.00` | `LOW` | `0.00` | `0.00` | `1.000` | 0 | PASS ⚠️🚫 |
| `three_known_mixed` | 3 | 3 | `0.25` | `LOW` | `0.87` | `0.00` | `1.000` | 0 | PASS  |
| `three_with_contradictions` | 3 | 3 | `0.28` | `LOW` | `0.95` | `0.67` | `0.667` | 0 | PASS  |
| `max_contradiction_density` | 3 | 3 | `0.30` | `MEDIUM` | `0.93` | `1.00` | `0.500` | 0 | PASS  |
| `four_diverse_states` | 4 | 3 | `0.21` | `LOW` | `0.77` | `0.00` | `1.000` | 0 | PASS ⚠️ |
| `self_harm_inferred` | 2 | 2 | `0.51` | `MEDIUM` | `0.83` | `0.00` | `1.000` | 0 | PASS  |
| `cybercrime_known` | 2 | 2 | `0.60` | `MEDIUM` | `1.00` | `0.00` | `1.000` | 0 | PASS  |
| `extremism_mixed_contra` | 2 | 2 | `0.45` | `MEDIUM` | `0.94` | `0.50` | `0.750` | 0 | PASS  |
| `sexual_ambiguous` | 2 | 2 | `0.60` | `MEDIUM` | `0.50` | `0.00` | `1.000` | 0 | PASS ⚠️ |
| `whitespace_signals` | 2 | 2 | `0.00` | `LOW` | `0.00` | `0.00` | `1.000` | 0 | PASS  |
| `max_length_text` | 2 | 2 | `0.31` | `MEDIUM` | `0.55` | `0.00` | `1.000` | 0 | PASS  |
| `single_signal_safe` | 1 | 1 | `0.00` | `LOW` | `1.00` | `0.00` | `1.000` | 0 | PASS  |
| `single_signal_ambiguous_high` | 1 | 1 | `0.69` | `MEDIUM` | `0.40` | `0.00` | `1.000` | 0 | PASS ⚠️ |

---

## Proof Methodology

```
For each (label, signals) in corpus (N=20 cases):
    baseline     = aggregate_signals(signals)
    baseline_hash = SHA256(json.dumps(asdict(baseline), sort_keys=True))

    for i in range(500):
        current      = aggregate_signals(signals)
        current_hash = SHA256(json.dumps(asdict(current), sort_keys=True))
        assert current_hash == baseline_hash
```

Both the engine (`analyze_text`) and DGIC adapter (`adapt_dgic`, `apply_dgic_modifiers`)
have been independently certified as deterministic. The aggregation algebra is a pure
function of those deterministic inputs, so the composite pipeline is deterministic.

> The multi-signal aggregator is **deterministic** across all 10000 calls.  
> Authority boundaries confirmed: `is_decision=False`, `authority="NONE"`, `actionable=False`  
> on all 20 corpus cases.

**Phase Tag:** `v-aggregation-sealed`
