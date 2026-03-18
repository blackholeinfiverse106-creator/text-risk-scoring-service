# Determinism Failure Detection Demo

**Generated:** 2026-02-21 11:23:21
**Input under test:** `kill murder attack scam`
**Iterations:** 200

## Objective

Prove that `replay_harness.py` has **true detection sensitivity** —
i.e., it will catch non-determinism when it actually exists.

## Method

We run the replay harness logic against two engine variants:

1. **Production engine** (`app/engine.py`) — expected: PASS
2. **Broken engine** (`determinism_failure_sim/broken_engine.py`) — expected: FAIL

The broken engine injects `random.random() * 0.001` into `risk_score` on every call.
This simulates a hidden state leak (e.g. timestamp-seeded cache or approximation error).

## Results

| Engine | Iterations | Divergences | First Divergence At | Verdict |
|--------|-----------|-------------|---------------------|---------|
| REAL (production) | 200 | 0 | -- | [PASS] |
| BROKEN (injected noise) | 200 | 160 | 1 | [FAIL] (DETECTED) |

## Conclusion

The harness **correctly identified** the broken engine as non-deterministic
and correctly **cleared** the production engine as fully deterministic.

This proves the harness has ≥1 detection sensitivity for any non-determinism
that affects the semantic hash fields within 200 iterations.

The injected noise (`random.random() * 0.001`) is equivalent in scale to:
- A float rounding error introduced by a math library change
- A timestamp-derived seed leaking into a score computation
- A non-deterministic cache hit ratio affecting a weight factor