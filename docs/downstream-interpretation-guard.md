# Downstream Interpretation Guard

**Generated:** 2026-02-21  
**Purpose:** Prevent the 5 most dangerous downstream misinterpretations of risk scores.

> This document is required reading for any team integrating the Text Risk Scoring Service into a product or enforcement pipeline.

---

## Misinterpretation 1 — "HIGH risk category means guilty"

### What people assume
A `risk_category: "HIGH"` response means the content is definitively harmful, the user is bad-faith, and enforcement action is warranted.

### Why this is wrong
`HIGH` means: *"multiple keywords associated with harm were detected."*  
It does NOT mean:
- The user intended harm
- The content is in violation of policy
- The context justifies action
- The text is unique (it could be a news article quoting harmful speech)

**Real consequence if uncorrected:** Users auto-banned for quoting news coverage, academic research, or historical text.

### Correct pattern
```
risk_category: "HIGH"
    → Queue for human review (do NOT auto-ban)
    → Policy layer evaluates context, user history, platform rules
    → Human reviewer makes enforcement decision
```

---

## Misinterpretation 2 — "Scores can be summed across requests"

### What people assume
Send 10 requests for a user's posts, sum or average the scores, and use the aggregate to make a holistic judgment.

### Why this is wrong
Each response is stateless. The score reflects **only the submitted text**, not the user's intent, history, or pattern.  
Summing scores:
- Double-counts repeated keywords (not additive risk)
- Ignores context changes between posts
- Creates false certainty from uncertain signals

**Real consequence if uncorrected:** A user who posts "I want to kill this bug in my code" 10 times gets flagged as high-risk by aggregation.

### Correct pattern
```
# WRONG
total_risk = sum(score for score in user_scores)
if total_risk > 5.0: ban(user)

# RIGHT
for score in user_scores:
    if score > 0.7:
        flag_for_review(post)   # flag the post, not the user
```

---

## Misinterpretation 3 — "The service can block content"

### What people assume
A `risk_score: 0.9` response gives the service authority to block, hide, or delete the content.

### Why this is wrong
The engine has **no write path**. It cannot:
- Block requests
- Delete content
- Suspend users
- Trigger webhooks

The `safety_metadata` field enforces this structurally:
```json
"safety_metadata": {
    "is_decision": false,    // ALWAYS false — immutable
    "authority":  "NONE",   // ALWAYS "NONE" — immutable
    "actionable": false      // ALWAYS false — immutable
}
```
If a consumer tries to pass `is_decision: true` to the contract validator, it raises `ContractViolation: INVALID_IS_DECISION`.

### Correct pattern
```
response = analyze_text(content)
if response["risk_score"] > 0.9:
    # WRONG: delete(content)
    # RIGHT:
    hide_pending_review(content)   # reversible
    notify_review_queue(content, response)
```

---

## Misinterpretation 4 — "confidence_score means certainty of harm"

### What people assume
`confidence_score: 0.95` means the service is 95% confident the content is harmful.

### Why this is wrong
`confidence_score` is derived from **keyword match density relative to text length**. It reflects:
- How many distinct categories matched
- How concentrated the matches are

It does NOT reflect:
- Probability of malicious intent
- Accuracy of the classification
- False-positive rate

**Real consequence if uncorrected:** A one-word text `"kill"` (context: gaming) scores `confidence: 0.5` — the same as a genuinely threatening message with one keyword.

### Correct pattern
Use confidence to gate **review priority**, not enforcement:
```
HIGH risk + HIGH confidence → Immediate review queue
HIGH risk + LOW confidence  → Low-priority review queue (context may explain)
LOW risk  + any confidence  → No review needed (with audit log)
```

---

## Misinterpretation 5 — "Scores can be cached indefinitely"

### What people assume
Once a piece of content scores `risk_score: 0.1`, that score is valid forever. Cache it and skip re-scoring.

### Why this is wrong
The keyword dictionary (`RISK_KEYWORDS`) evolves. A word that scored 0.0 today may match a new category tomorrow after a model update. Stale caches create:
- False negatives for newly dangerous terms
- Inconsistent behavior between cached and live paths
- Undetectable drift between cache and current risk model

### Correct pattern
```python
CACHE_TTL = 3600  # seconds — max 1 hour
cache_key = hashlib.sha256(
    f"{text}::{API_VERSION}".encode()
).hexdigest()

result = cache.get(cache_key, ttl=CACHE_TTL)
if result is None:
    result = analyze_text(text)
    cache.set(cache_key, result, ttl=CACHE_TTL)

# NEVER cache on text alone — always include API_VERSION in key
# NEVER cache error responses
if result.get("errors"):
    cache.delete(cache_key)
```

---

## Quick Reference: What the Service IS vs. IS NOT

| IS | IS NOT |
|----|--------|
| A heuristic keyword scanner | A classifier trained on intent |
| A signal for a policy layer | A policy layer itself |
| Stateless per-request | Session-aware or user-aware |
| A risk indicator | A verdict |
| One input to a human review | A replacement for human review |
| An audit data source | An enforcement mechanism |
