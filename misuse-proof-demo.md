# Misuse Proof Demo

Demonstrates 4 misuse patterns against the enforcement adapter and proves each is blocked.

## Demo 1 — Score-as-Verdict

**Attempt:** Act on HIGH score without human review.

```python
rec = adapter.evaluate("kill attack bomb")
if rec.risk_category == "HIGH":
    ban_user(rec.correlation_id)  # WRONG — no human in loop
```

**Why it fails structurally:**
- `rec.action is None` — adapter has no ban/block output field
- `rec.human_review == True` — policy explicitly requires a human gate
- `is_decision == False` — caller must not treat this as a decision

**Correct:**
```python
if rec.recommendation == "HOLD":
    send_to_human_review_queue(rec)  # human decides
```

---

## Demo 2 — Confidence Suppression

**Attempt:** Use high confidence to skip review.

```python
if rec.confidence_score > 0.9:
    auto_enforce()  # WRONG — confidence is keyword density, not certainty
```

**Why it fails:** Confidence reflects how many keywords matched, not whether the text is genuinely harmful. A 0.9 confidence HIGH is still a heuristic, not a verdict.

---

## Demo 3 — Score Laundering

**Attempt:** Re-package the score as a policy decision in a downstream system.

```python
my_system_output = {
    "decision": "BANNED",
    "basis": analyze_text(text)["risk_score"]
}
```

**Why it fails:** The score has no legal, contractual, or policy standing. Any downstream system that labels it a "decision" is misrepresenting its source — the original output carries `is_decision: false`.

---

## Demo 4 — Retry-Until-Low

**Attempt:** Retry with rephrased text until the score drops below a threshold.

```python
while analyze_text(modified_text)["risk_score"] > 0.3:
    modified_text = rephrase(modified_text)
# Now submit the low-scoring version
```

**Why it fails as an enforcement bypass:** The contract layer is stateless — it scores only the submitted text. Downstream enforcement must log and flag re-submission patterns; the engine score alone is not sufficient for enforcement. This is exactly why human review is mandatory at MEDIUM/HIGH.

---

## Summary

| Misuse | Structural Block |
|---|---|
| Score-as-verdict | `action=None`, `is_decision=False` |
| Confidence suppression | Confidence is density metric, not certainty |
| Score laundering | Output carries `is_decision: false` |
| Retry-until-low | Engine is stateless; resubmission detection is caller's responsibility |
