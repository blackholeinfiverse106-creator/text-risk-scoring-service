# Release Notes — v1.0.0-integration

**Tag:** `v1.0.0-integration`  
**Date:** 2026-02-21  
**Status:** Pre-integration release candidate

---

## What This Release Certifies

This tag marks the completion of a 6-day robustness proof program. The service is certified across all six dimensions:

| Day | Theme | Verdict |
|---|---|---|
| Day 1 | Runtime Determinism | 150,000 runs — 0 divergences |
| Day 2 | Concurrency & Resources | 500 concurrent, P99=17ms, 0 ReDoS risks |
| Day 3 | Misuse & Authority | 67 tests, 47 attack patterns — all blocked |
| Day 4 | Failure Tier Formalization | 9 error paths, full trace lineage proven |
| Day 5 | Enforcement Simulation | Adapter verified — `action=None` structural invariant holds |
| Day 6 | Integration Readiness | Contracts frozen, invariants revalidated |

---

## Frozen Artifacts (v3 API Contract)

| Artifact | Status |
|---|---|
| `contracts-v3.md` | **FROZEN** — integration contract |
| `invariants-v2.md` | **FROZEN** — 14 invariants revalidated |
| `logging-schema-v1.md` | **FROZEN** — log schema contract |
| `failure-tier-model-v2.md` | **FROZEN** — failure tier model |

---

## Run All Proofs

```bash
python -m pytest tests/ decision-injection-tests/ escalation-tests/ -q
python error-propagation-proof.py
python trace-lineage-demo.py
python mock_enforcement_adapter.py
```

Expected: all tests pass, all scripts exit 0.

---

## Known Limitations (Not Blockers)

- Score is keyword-density heuristic, not an ML probability
- No rate limiting in core engine (handled by infra layer)
- `trigger_reasons` ordering is informational, not contractually stable
