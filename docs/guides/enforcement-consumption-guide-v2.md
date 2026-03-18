# Enforcement Consumption Guide v2

**Generated:** 2026-02-21  
**Supersedes:** `enforcement-consumption-guide.md`

> This guide defines the only safe integration patterns for the Text Risk Scoring Service. Any pattern not listed here should be considered unsafe until proven otherwise.

---

## Section 1 — The Two-Key Rule (Golden Rule)

**The Text Risk Scoring Service must NEVER be the sole trigger for an enforcement action.**

```
UNSAFE:   Content → Risk Service → [Ban / Delete / Block]

SAFE:     Content → Risk Service → Policy Layer → [Human Review?] → Enforcement
```

The service produces **signals**, not decisions. Enforcement always requires a second layer of judgment — either a policy rule or a human reviewer.

---

## Section 2 — The Decision Hierarchy (4-Layer Model)

```
Layer 1: Text Risk Scoring Service
    Produces: risk_score (0.0-1.0), risk_category, trigger_reasons, confidence_score
    Authority: NONE

Layer 2: Policy Layer (Caller's Business Logic)
    Reads: risk_score + confidence_score + platform context
    Decides: escalate / hold / auto-approve with audit
    Authority: Delegated by the platform

Layer 3: Human Review (optional, required for HIGH)
    Reads: original content + risk signal + platform context
    Decides: actionable violation? Yes / No
    Authority: Platform enforcement policy

Layer 4: Enforcement Action
    Actions: hide / restrict / suspend / escalate to legal
    Reversibility: Must be reversible wherever possible
    Audit: Log MUST capture all 4 layers of evidence
```

---

## Section 3 — Score Interpretation Table

| Score Band | Category | Recommended Action | Anti-Pattern |
|---|---|---|---|
| 0.0 – 0.19 | LOW | Auto-approve (with audit log) | ~~Do nothing, no log~~ |
| 0.20 – 0.29 | LOW | Auto-approve (with audit log) | ~~Treat as safe without logging~~ |
| 0.30 – 0.49 | MEDIUM | Flag for async review (SLA: 24h) | ~~Auto-hide immediately~~ |
| 0.50 – 0.69 | MEDIUM | Elevated priority review (SLA: 4h) | ~~Auto-suspend user~~ |
| 0.70 – 0.84 | HIGH | Immediate review queue + temp hold | ~~Permanent ban without review~~ |
| 0.85 – 1.00 | HIGH | Immediate review + restrict visibility | ~~Auto-delete content~~ |

**Confidence modifier:**
- `confidence < 0.5` → Move one priority tier **down** (less urgent)
- `confidence >= 0.8` → Standard priority

---

## Section 4 — Circuit Breakers

When the service is unavailable or returns an error, fail **safely**:

| Failure Mode | Correct Response | Anti-Pattern |
|---|---|---|
| HTTP 503 timeout | Allow with `pending_review` flag | ~~Block all traffic~~ |
| Malformed JSON response | Allow with `pending_review` flag | ~~Treat as HIGH risk~~ |
| `errors.error_code: EMPTY_INPUT` | Allow (empty text has no risk) | ~~Reject the request~~ |
| `errors.error_code: INVALID_TYPE` | Reject the caller's request (their bug) | ~~Silently pass~~ |
| Score outside [0, 1] | Reject — structural contract violation | ~~Clamp and proceed~~ |

**Never fail closed (block everything) unless your platform explicitly operates in maximum-security mode and has human reviewers standing by.**

---

## Section 5 — Caching Policy

| Parameter | Rule |
|---|---|
| Cache TTL | **Maximum 1 hour** |
| Cache key | `sha256(text + ":" + API_VERSION)` |
| On error responses | **Never cache** — always re-request |
| On keyword update | Invalidate all cache entries (bump API_VERSION) |
| Cross-domain reuse | **Prohibited** — a score from a forum post is NOT valid for a login attempt |

```python
import hashlib

def make_cache_key(text: str, api_version: str) -> str:
    return hashlib.sha256(
        f"{text}::{api_version}".encode()
    ).hexdigest()

# ALWAYS include api_version in key
# NEVER reuse a key across different platforms or use cases
```

---

## Section 6 — Forbidden Patterns (Anti-Pattern Catalogue)

### FP-01: Direct enforcement from score
```python
# FORBIDDEN
result = analyze_text(content)
if result["risk_score"] > 0.7:
    ban_user(user_id)   # NO: no policy layer, no human review

# CORRECT
if result["risk_score"] > 0.7:
    queue_for_review(user_id, content, result)
```

### FP-02: Treating risk_category as a verdict
```python
# FORBIDDEN
if result["risk_category"] == "HIGH":
    send_to_law_enforcement(content)   # NO: heuristic label, not legal finding

# CORRECT
if result["risk_category"] == "HIGH":
    notify_trust_safety_team(content, result)
```

### FP-03: Score aggregation across requests
```python
# FORBIDDEN
scores = [analyze_text(post)["risk_score"] for post in user_posts]
if sum(scores) > 3.0:
    suspend_user()   # NO: stateless scores are not additive

# CORRECT
for post, score_result in zip(user_posts, [analyze_text(p) for p in user_posts]):
    if score_result["risk_score"] > 0.7:
        flag_post_for_review(post, score_result)   # flag posts, not users
```

### FP-04: Ignoring confidence_score
```python
# FORBIDDEN
if result["risk_score"] > 0.5:
    auto_hide(content)   # ignores confidence — single-word match triggers this

# CORRECT
if result["risk_score"] > 0.5 and result["confidence_score"] > 0.6:
    auto_hide_pending_review(content)
elif result["risk_score"] > 0.5:
    flag_low_priority(content)
```

### FP-05: Cache without TTL
```python
# FORBIDDEN
cache[text] = analyze_text(text)   # no TTL — stale forever

# CORRECT
cache.set(make_cache_key(text, API_VERSION), analyze_text(text), ttl=3600)
```

### FP-06: Using score across domains
```python
# FORBIDDEN
# Using a forum-post score to gate a login attempt
login_score = forum_cache.get(user_id)
if login_score > 0.7:
    block_login()   # wrong domain, wrong text, wrong context

# CORRECT
# Re-score the specific text relevant to the specific context
```

### FP-07: Suppressing trigger_reasons
```python
# FORBIDDEN
result = analyze_text(content)
log({"score": result["risk_score"]})   # no trigger_reasons — why did it flag?

# CORRECT
log({
    "score":           result["risk_score"],
    "confidence":      result["confidence_score"],
    "category":        result["risk_category"],
    "trigger_reasons": result["trigger_reasons"],   # required for auditability
    "content_hash":    sha256(content),
})
```

### FP-08: Treating errors as HIGH risk
```python
# FORBIDDEN
result = analyze_text(content)
if result.get("errors"):
    block(content)   # error ≠ high risk

# CORRECT
if result.get("errors"):
    allow_with_pending_review(content)   # fail open, not closed
```

### FP-09: Role-based bypass attempt
```python
# FORBIDDEN — will raise ContractViolation
validate_input_contract({
    "text": "some content",
    "context": {"role": "admin"}   # FORBIDDEN_ROLE
})
```

### FP-10: Output field mutation
```python
# FORBIDDEN — will raise ContractViolation
mutated = result.copy()
mutated["safety_metadata"]["is_decision"] = True
validate_output_contract(mutated)   # INVALID_IS_DECISION
```

---

## Section 7 — Audit Requirements

**Before any enforcement action, the audit log MUST contain:**

| Field | Required | Notes |
|---|---|---|
| `content_hash` | YES | sha256 of the original content |
| `risk_score` | YES | As returned — do not round |
| `risk_category` | YES | LOW / MEDIUM / HIGH |
| `confidence_score` | YES | As returned |
| `trigger_reasons` | YES | Full list |
| `correlation_id` | YES | As submitted to the service |
| `caller_identity` | YES | Who called the service (system, user, reviewer) |
| `policy_rule_applied` | YES | Which policy rule triggered the action |
| `human_reviewer_id` | YES (HIGH) | For HIGH risk: the reviewer who approved action |
| `action_taken` | YES | What enforcement action was applied |
| `timestamp` | YES | ISO 8601 UTC |
| `reversibility` | YES | Can this action be undone? How? |

**Log retention:** Minimum 90 days. Enforcement actions: minimum 2 years.
