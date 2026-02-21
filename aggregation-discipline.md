# Aggregation Discipline

Rules for combining risk signals across multiple inputs.

## The Problem

```python
# WRONG: Averaging signals implies the service tracks history
scores = [analyze_text(t)["risk_score"] for t in texts]
aggregate = sum(scores) / len(scores)  # meaningless — each signal is independent
```

Each call to `analyze_text` is stateless and independent. There is no shared context between calls.

## Correct Patterns

### Pattern 1 — Worst-Signal Routing
Use the highest risk signal to determine routing. Do not soften with averages.

```python
signals = [adapter.evaluate(t) for t in message_batch]
worst   = max(signals, key=lambda r: r.risk_score)
if worst.recommendation == "HOLD":
    route_to_human_review(worst)
```

### Pattern 2 — All-Must-Pass Gate
For moderation pipelines: any HOLD means the batch is held.

```python
if any(r.recommendation == "HOLD" for r in signals):
    hold_entire_batch()
```

### Pattern 3 — Per-Signal Independence
Never treat sequential signals as a trend. A user's prior LOW score grants no leniency.

```python
# NEVER:
if prior_score < 0.3 and current_score < 0.5:
    auto_allow()   # WRONG — temporal correlation, no state basis

# CORRECT:
rec = adapter.evaluate(current_text)   # each signal stands alone
```

## Rules

| Rule | Rationale |
|---|---|
| Never average scores | Averages reduce signal fidelity; worst-case matters |
| Never track history | Service is stateless — prior calls are independent |
| Never use score as probability | Scores are keyword-density heuristics, not probabilities |
| Human review required at MEDIUM/HIGH | Policy layer must be human-gated |
