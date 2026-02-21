# Invariants v2 — Final Revalidation

**Version:** v2  
**Date:** 2026-02-21  
**Supersedes:** `scoring-invariants.md`

All invariants have been revalidated across Days 1–5 proofs.

---

## Scoring Invariants

| # | Invariant | Formal | Proven By |
|---|---|---|---|
| I-1 | **Boundedness** | `0.0 ≤ risk_score ≤ 1.0` always | `replay_harness.py` (150k runs), `resource_boundary_analysis.py` |
| I-2 | **Determinism** | `S(T)` is identical for any identical `T` across time and processes | `replay_harness.py`, `cross_process_test.py` |
| I-3 | **Statelessness** | `S(T)_t == S(T)_{t+Δ}` regardless of prior calls | `thread_safety_proof.py` (200 threads) |
| I-4 | **Category Consistency** | `score < 0.3 → LOW`, `0.3 ≤ score < 0.7 → MEDIUM`, `score ≥ 0.7 → HIGH` | `error-propagation-proof.py`, engine invariant correction |
| I-5 | **Category Cap** | No single category contributes more than `0.6` to the total | `regex_attack_profile.py`, engine `MAX_CATEGORY_SCORE` constant |
| I-6 | **Error Safety** | All error paths return `errors != null` and `is_decision: false` | `error-propagation-proof.py` (9/9 paths) |

## Authority Invariants

| # | Invariant | Formal | Proven By |
|---|---|---|---|
| A-1 | **Non-authority** | `safety_metadata.authority == "NONE"` always | `validate_output_contract()`, `test_output_mutation.py` |
| A-2 | **Non-decision** | `safety_metadata.is_decision == false` always | All 26 escalation tests |
| A-3 | **Non-actionable** | `safety_metadata.actionable == false` always | `test_output_mutation.py` |
| A-4 | **Role rejection** | Forbidden roles blocked at input layer | `decision-injection-tests/` (41 tests) |
| A-5 | **Injection rejection** | Decision injection blocked structurally | `decision-injection-tests/` (41 tests) |

## Concurrency Invariants

| # | Invariant | Proven By |
|---|---|---|
| C-1 | Thread safety: no shared mutable state | `thread_safety_proof.py` (200 threads, 0 divergences) |
| C-2 | No ReDoS vulnerability in any keyword pattern | `regex_attack_profile.py` (181 patterns, 0 risks) |
| C-3 | Memory bounded per request | `resource_boundary_analysis.py` (<78KB worst case) |

## Observability Invariants

| # | Invariant | Proven By |
|---|---|---|
| O-1 | Every request carries a `correlation_id` in all log entries | `trace-lineage-demo.py` (3 requests, 0 bleed) |
| O-2 | Score is fully reconstructible from log stream alone | `tests/test_log_replay.py` |

---

## Revalidation Status

All 14 invariants verified against Days 1–5 proof outputs.  
**No invariant regressions detected.**
