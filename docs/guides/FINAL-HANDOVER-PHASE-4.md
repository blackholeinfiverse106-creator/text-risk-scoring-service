# FINAL HANDOVER — Phase 4

**Service:** Text Risk Scoring Service  
**Version:** `v1.0.0-integration`  
**Date:** 2026-02-21  
**Status:** Integration-Ready ✓

---

## What This Service Does

Scores text content against 10 risk categories and returns a structured signal:
- `risk_score` in `[0.0, 1.0]`
- `risk_category`: LOW / MEDIUM / HIGH
- `safety_metadata`: permanently non-authority, non-decision, non-actionable

**What it does not do:** Take actions, make enforcement decisions, or accumulate state.

---

## Consuming This Service

### Minimal correct integration

```python
import requests

resp = requests.post("http://<host>/analyze", json={
    "text": user_submitted_text,
    "context": {"caller_id": "my-service", "use_case": "comment-moderation"}
})
data = resp.json()

if data["errors"]:
    # Engine error — do not act on score, log and route to review
    flag_for_review(data)

elif data["risk_category"] == "HIGH":
    route_to_human_review_queue(data)      # human decides

elif data["risk_category"] == "MEDIUM":
    soft_flag(data)                         # async review

# else: LOW — allow
```

### Forbidden patterns

```python
# NEVER: treat score as a decision
if risk_score > 0.7:
    ban_user()      # WRONG — no authority, no confidence in enforcement

# NEVER: average scores across requests
avg = (score_a + score_b) / 2   # WRONG — signals are independent

# NEVER: suppress human review on high confidence
if confidence > 0.9:
    auto_enforce()  # WRONG — confidence is keyword density, not certainty
```

---

## Architecture at a Glance

```
POST /analyze
     ├─ validate_input_contract()   ← blocks forbidden roles & injection
     ├─ analyze_text()              ← stateless, deterministic scoring
     ├─ validate_output_contract()  ← asserts safety_metadata invariants
     └─ Structured response (always)
```

No DB. No cache. No external calls. Zero env vars required.

---

## Certification Summary (Days 1–6)

| Day | Proof | Verdict |
|---|---|---|
| 1 | Determinism | 150k runs, 0 divergences |
| 2 | Concurrency & ReDoS | 500 threads, P99=17ms, 0 vulnerabilities |
| 3 | Misuse & Authority | 67 tests, 47 attack patterns — 100% blocked |
| 4 | Failure Tiers | 9/9 error paths, full trace lineage |
| 5 | Enforcement Simulation | Adapter — `action=None` structural invariant |
| 6 | Integration Readiness | Contracts v3 frozen, 14 invariants revalidated |

---

## Frozen Specifications

| Document | What's frozen |
|---|---|
| `contracts-v3.md` | Input/output schema + forbidden fields |
| `invariants-v2.md` | 14 scoring, authority, concurrency, observability invariants |
| `logging-schema-v1.md` | 9 event types, field stability contract |
| `fail-mode-matrix.md` | Fail-open/closed for every error code |

---

## Operational Notes

- **Startup:** No config required — constants baked into `app/engine.py`
- **Scaling:** Stateless — any number of instances, no coordination
- **Monitoring:** Alert on `event_type: unhandled_exception` or `INTERNAL_ERROR` (see `failure-tier-model-v2.md`)
- **Log parsing:** Use `event_type` field, not `message` string (see `logging-schema-v1.md`)
- **Caching:** Results may be cached by `(text, keyword_dict_version)` — never cache across keyword updates

---

## Handover Sign-off

All 6 phases complete. Repository is clean, tagged, and sealed.

```bash
# Run all proofs
python -m pytest tests/ decision-injection-tests/ escalation-tests/ -q
python error-propagation-proof.py
python trace-lineage-demo.py
```
