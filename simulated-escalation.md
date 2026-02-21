# Simulated Escalation Pipeline

A reference pipeline showing how risk signals flow from the engine to a human decision — with each stage's authority clearly bounded.

## Pipeline Stages

```
User Content
     │
     ▼
┌─────────────────────┐
│  1. analyze_text()  │  ← score-only, read-only, no authority
│  (app/engine.py)    │
└────────┬────────────┘
         │ risk_score, risk_category, confidence_score
         ▼
┌─────────────────────┐
│  2. EnforcementAdapter  │  ← applies policy, still read-only
│  mock_enforcement_       │  recommendation: ALLOW | FLAG | HOLD
│  adapter.py         │    action: always None
└────────┬────────────┘
         │ EnforcementRecommendation
         ▼
┌─────────────────────┐
│  3. Routing Layer   │  ← caller's responsibility
│  (your system)      │  ALLOW → pass through
│                     │  FLAG  → soft queue (low priority)
│                     │  HOLD  → human review queue
└────────┬────────────┘
         │ (for HOLD / FLAG)
         ▼
┌─────────────────────┐
│  4. Human Reviewer  │  ← ONLY stage with real authority
│  (policy team)      │  Reviews context + risk signal together
│                     │  Final decision: approve / reject / escalate
└─────────────────────┘
```

## Stage Responsibilities

| Stage | Authority | Can Block? | Reason |
|---|---|---|---|
| `analyze_text` | NONE | No | Score only; no write path |
| `EnforcementAdapter` | NONE | No | Recommendation only; `action=None` |
| Routing Layer | Limited | Route only | No final verdict power |
| Human Reviewer | FULL | Yes | Only stage with contextual judgment |

## Example Flow

```python
adapter = EnforcementAdapter()
rec = adapter.evaluate(submitted_text, correlation_id="REQ-42")

if rec.recommendation == "ALLOW":
    publish(submitted_text)

elif rec.recommendation == "FLAG":
    publish(submitted_text)          # publish but tag for async review
    soft_queue.add(rec)

elif rec.recommendation == "HOLD":
    hold_queue.add(rec)              # DO NOT publish until human clears
    notify_reviewer(rec)
```

## Key Invariants

- **No stage below Human Reviewer may take a final action**
- **Every HOLD must be traceable** via `correlation_id` through all stages
- **Score is never the sole basis** for any enforcement action
