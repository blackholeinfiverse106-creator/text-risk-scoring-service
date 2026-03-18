# Misuse Scenarios — Text Risk Scoring Service

**Document Purpose**: Enumerate all possible misuse cases and structural safeguards to prevent them.

---

## Misuse Category 1: Treated as Authority

### Scenario 1.1: Direct Action Execution
**Misuse**: Downstream system treats risk score as executable command
```python
# WRONG
response = risk_service.analyze(text)
if response["risk_category"] == "HIGH":
    delete_content()  # Direct action without review
```

**Impact**: System becomes de facto decision maker, violating authority boundaries

**Safeguard**: 
- `safety_metadata` explicitly denies authority
- Documentation requires Two-Key Rule
- Low confidence should block automated actions

**Detection**: Audit logs show action without policy layer

---

### Scenario 1.2: Score Threshold Misuse
**Misuse**: Using internal thresholds as policy without business logic
```python
# WRONG
if risk_score > 0.7:
    ban_user()  # Treating threshold as policy
```

**Impact**: Risk service thresholds become enforcement policy

**Safeguard**:
- Documentation states thresholds are heuristic, not policy
- Downstream must define own thresholds
- Confidence score must be checked

**Detection**: No policy layer between signal and action

---

### Scenario 1.3: Ignoring safety_metadata
**Misuse**: Downstream system ignores `is_decision: false` flag
```python
# WRONG
response = risk_service.analyze(text)
# Ignores safety_metadata
take_action(response["risk_category"])
```

**Impact**: Authority denial is ignored

**Safeguard**:
- Contract requires safety_metadata presence
- Integration protocol mandates checking
- Fail-safe: low confidence blocks action

**Detection**: Actions taken without safety_metadata validation

---

## Misuse Category 2: Used Without Enforcement Context

### Scenario 2.1: Missing Caller Context
**Misuse**: Service called without identifying caller or purpose
```python
# WRONG
analyze_text("some content")  # Who called? For what purpose?
```

**Impact**: No audit trail, no accountability, no context for interpretation

**Safeguard**:
- Require caller_id in request metadata
- Require use_case declaration
- Log all requests with context

**Detection**: Requests without caller identification

---

### Scenario 2.2: No Policy Layer
**Misuse**: Risk signal directly connected to enforcement without policy
```
Risk Service → Enforcement Action (NO POLICY LAYER)
```

**Impact**: Signal becomes decision

**Safeguard**:
- Documentation requires policy layer
- Two-Key Rule enforcement
- Audit trail must show policy decision

**Detection**: Direct signal-to-action mapping

---

### Scenario 2.3: Missing Human Review
**Misuse**: High-risk content auto-deleted without human review
```python
# WRONG
if risk_score > 0.9:
    auto_delete()  # No human review
```

**Impact**: False positives cause harm without recourse

**Safeguard**:
- Confidence threshold for automation
- High-risk + low-confidence → mandatory review
- Rate limiting on automated actions

**Detection**: High-risk actions without review logs

---

## Misuse Category 3: Cached Incorrectly

### Scenario 3.1: Stale Cache
**Misuse**: Caching risk scores indefinitely
```python
# WRONG
cache[text_hash] = risk_score  # No expiration
# Later: use stale score for new decision
```

**Impact**: Outdated risk assessments used for current decisions

**Safeguard**:
- Responses include timestamp
- Documentation forbids long-term caching
- Cache TTL must be short (< 1 hour recommended)

**Detection**: Cached scores used beyond reasonable timeframe

---

### Scenario 3.2: Context-Free Caching
**Misuse**: Caching score without context
```python
# WRONG
cache["kill"] = 0.95  # Same score for all contexts
```

**Impact**: "I will kill time" gets same score as "I will kill you"

**Safeguard**:
- System is context-agnostic by design
- Documentation warns against context-free caching
- Full text should be cache key, not keywords

**Detection**: Keyword-based cache keys

---

### Scenario 3.3: Cross-Domain Cache Reuse
**Misuse**: Using cached scores across different domains
```python
# WRONG
score_from_gaming_chat = cache["attack"]
use_for_news_article("attack")  # Different context
```

**Impact**: Domain-specific language misinterpreted

**Safeguard**:
- Documentation forbids cross-domain cache reuse
- Caller context should be part of cache key
- Short TTL limits damage

**Detection**: Cache hits across different caller_ids

---

## Misuse Category 4: Combined Improperly

### Scenario 4.1: Score Aggregation Without Confidence
**Misuse**: Averaging scores without considering confidence
```python
# WRONG
avg_score = (score1 + score2 + score3) / 3
if avg_score > 0.7:
    take_action()
```

**Impact**: Low-confidence signals pollute aggregate

**Safeguard**:
- Confidence score must be weighted
- Low confidence signals should be excluded
- Documentation provides aggregation guidelines

**Detection**: Aggregation without confidence weighting

---

### Scenario 4.2: Multi-Signal Misinterpretation
**Misuse**: Combining signals from different services incorrectly
```python
# WRONG
if risk_score > 0.5 AND spam_score > 0.5:
    delete()  # Treating both as decisions
```

**Impact**: Multiple signals treated as joint authority

**Safeguard**:
- Each signal must declare non-authority
- Policy layer must interpret combination
- Two-Key Rule applies to combination

**Detection**: Direct multi-signal to action mapping

---

### Scenario 4.3: Temporal Aggregation
**Misuse**: Aggregating scores over time without decay
```python
# WRONG
user_risk = sum(all_historical_scores)  # No time decay
if user_risk > threshold:
    ban_user()
```

**Impact**: Old behavior permanently affects user

**Safeguard**:
- Documentation forbids temporal aggregation
- If needed, must use time decay
- Historical scores should not auto-accumulate

**Detection**: Permanent risk accumulation

---

## Structural Safeguards Implemented

### 1. Required Context Fields

**Mandatory in Request** (to be implemented):
```json
{
  "text": "content to analyze",
  "context": {
    "caller_id": "moderation-bot-v2",
    "use_case": "user_content_review",
    "request_id": "uuid"
  }
}
```

**Purpose**: Audit trail, accountability, context tracking

---

### 2. Mandatory Caller Declarations

**Required Acknowledgement** (to be implemented):
```json
{
  "caller_acknowledgement": {
    "understands_signal_only": true,
    "has_policy_layer": true,
    "has_human_review": true
  }
}
```

**Purpose**: Explicit confirmation of proper integration

---

### 3. Fail-Closed Behavior

**Current Implementation**:
- Empty input → Error (not default "safe")
- Invalid input → Error (not default "safe")
- Low confidence → Explicit in response

**To Add**:
- Service unavailable → Downstream must queue for review
- Ambiguous result → Flag for human review
- Rate limit exceeded → Fail closed, not open

---

### 4. Deterministic Degradation

**Guaranteed Behavior**:
- Same input → Same output (always)
- Error conditions → Consistent error codes
- Degraded mode → Predictable behavior

**To Prove**:
- Stress test with repeated inputs
- Verify determinism under load
- Document degradation modes

---

## Abuse Resistance Guarantees

### 1. Repeatability Under Abuse

**Guarantee**: System produces same output regardless of:
- Request rate
- Caller identity
- Time of day
- Previous requests

**Test**: Hammer with identical requests, verify identical responses

---

### 2. No State Leakage

**Guarantee**: Request N does not affect request N+1

**Test**: Interleave different requests, verify independence

---

### 3. Resource Exhaustion Resistance

**Guarantee**: System degrades gracefully under load

**Test**: Stress test with excessive requests, verify fail-closed

---

## Misuse Detection Checklist

For downstream systems to self-audit:

- [ ] Do we check `safety_metadata.is_decision` before acting?
- [ ] Do we have a policy layer between signal and action?
- [ ] Do we require human review for high-risk + low-confidence?
- [ ] Do we log policy decisions separately from risk scores?
- [ ] Do we implement the Two-Key Rule for destructive actions?
- [ ] Do we have a circuit breaker for mass-enforcement?
- [ ] Do we cache with appropriate TTL (< 1 hour)?
- [ ] Do we include caller context in all requests?
- [ ] Do we weight confidence when aggregating scores?
- [ ] Do we fail closed when service is unavailable?

---

## Red Flags (Indicators of Misuse)

1. **Direct signal-to-action mapping** without policy layer
2. **Ignoring confidence scores** in decision logic
3. **Long-term caching** (> 1 hour) of risk scores
4. **Cross-domain cache reuse** without re-evaluation
5. **Temporal aggregation** without time decay
6. **Missing audit trails** for actions taken
7. **No human review** for high-risk decisions
8. **Treating thresholds as policy** without business logic
9. **Ignoring safety_metadata** in integration
10. **No circuit breaker** for mass-enforcement scenarios

---

## Enforcement Failure Modes

### Mode 1: Service Unavailable
**Behavior**: Return 503, downstream must queue for review
**NOT**: Assume safe and allow content

### Mode 2: Ambiguous Input
**Behavior**: Low confidence score, flag for review
**NOT**: Default to high or low risk

### Mode 3: Rate Limit Exceeded
**Behavior**: Return 429, downstream must throttle
**NOT**: Process with degraded accuracy

### Mode 4: Internal Error
**Behavior**: Return 500, downstream must fail closed
**NOT**: Assume safe and proceed

---

## Conclusion

This document enumerates all identified misuse scenarios and structural safeguards. Implementation of required context fields and mandatory caller declarations will further strengthen abuse resistance.

**Key Principle**: The system must be structurally resistant to misuse, not just documented against it.
