# Enforcement Consumption Guide
## How to Safely Consume Risk Signals

**Audience**: Downstream enforcement systems (InsightBridge, Workflow Executor, Moderation Bots)  
**Purpose**: Define safe consumption patterns and forbidden practices

---

## Executive Summary

**This service provides SIGNALS, not DECISIONS.**

Your enforcement system must:
- ✅ Treat outputs as advisory signals
- ✅ Apply your own policy layer
- ✅ Implement human review for high-risk decisions
- ✅ Check confidence scores before automation
- ✅ Maintain audit trails separate from risk scores

Your enforcement system must NOT:
- ❌ Treat risk scores as executable commands
- ❌ Use this as the sole basis for consequential actions
- ❌ Ignore safety_metadata warnings
- ❌ Cache indefinitely without re-evaluation
- ❌ Assume semantic understanding of content

---

## Integration Architecture

### Correct Architecture ✅

```
User Content
    ↓
Risk Scoring Service (THIS SYSTEM)
    ↓ [Signal: risk_score, confidence, safety_metadata]
Policy Layer (YOUR RESPONSIBILITY)
    ↓ [Decision: based on business rules + risk signal]
Human Review (YOUR RESPONSIBILITY)
    ↓ [Approval: for high-risk decisions]
Enforcement Action (YOUR RESPONSIBILITY)
    ↓ [Action: delete, ban, flag, etc.]
Audit Trail (YOUR RESPONSIBILITY)
```

### Incorrect Architecture ❌

```
User Content
    ↓
Risk Scoring Service
    ↓ [Signal treated as decision]
Enforcement Action (DIRECT - WRONG!)
```

---

## What Enforcement MAY Rely On

### 1. Deterministic Scoring ✅

**Guarantee**: Same input → Same output (always)

**You can rely on**:
- Consistent risk scores for identical content
- Reproducible results for testing
- Cacheable responses (with appropriate TTL)

**Example**:
```python
# Safe: Cache with short TTL
cache_key = hash(text)
cached = cache.get(cache_key, ttl=3600)  # 1 hour max
if not cached:
    cached = risk_service.analyze(text)
    cache.set(cache_key, cached, ttl=3600)
```

---

### 2. Bounded Outputs ✅

**Guarantee**: All outputs within defined ranges

**You can rely on**:
- `risk_score`: 0.0 ≤ score ≤ 1.0
- `confidence_score`: 0.0 ≤ confidence ≤ 1.0
- `risk_category`: One of ["LOW", "MEDIUM", "HIGH"]
- `safety_metadata`: Always present with fixed values

**Example**:
```python
# Safe: Use score in threshold logic
response = risk_service.analyze(text)
if response["risk_score"] > YOUR_POLICY_THRESHOLD:
    if response["confidence_score"] > 0.8:
        queue_for_review()
    else:
        flag_as_ambiguous()
```

---

### 3. Explicit Trigger Reasons ✅

**Guarantee**: Explainable keyword matches

**You can rely on**:
- List of detected keywords
- Category of each match
- Transparent reasoning

**Example**:
```python
# Safe: Use trigger reasons for audit trail
response = risk_service.analyze(text)
audit_log = {
    "risk_score": response["risk_score"],
    "triggers": response["trigger_reasons"],
    "policy_decision": your_policy_decision,
    "action_taken": your_action
}
```

---

### 4. Structured Errors ✅

**Guarantee**: Consistent error format

**You can rely on**:
- `errors` field present in all responses
- Specific error codes (EMPTY_INPUT, INVALID_TYPE, etc.)
- Deterministic error behavior

**Example**:
```python
# Safe: Handle errors gracefully
response = risk_service.analyze(text)
if response["errors"]:
    if response["errors"]["error_code"] == "EMPTY_INPUT":
        return "Content is empty, no risk assessment needed"
    else:
        queue_for_manual_review("Risk service error")
```

---

### 5. Safety Metadata ✅

**Guarantee**: Non-authority declaration in every response

**You can rely on**:
- `is_decision`: Always False
- `authority`: Always "NONE"
- `actionable`: Always False

**Example**:
```python
# Safe: Verify signal-only nature
response = risk_service.analyze(text)
assert response["safety_metadata"]["is_decision"] is False
# Now apply your own decision logic
```

---

## What Enforcement MUST NEVER Infer

### 1. Semantic Understanding ❌

**This system CANNOT understand context**

**Do NOT infer**:
- Intent ("I will kill time" vs "I will kill you")
- Sarcasm ("Great, just great" as negative)
- Cultural context (domain-specific language)
- Tone (angry vs. playful)

**Example of WRONG inference**:
```python
# WRONG: Assuming semantic understanding
if "kill" in text:
    # System detected "kill" but doesn't know if it's
    # "kill time", "killer deal", or actual threat
    ban_user()  # WRONG - no context understanding
```

**Correct approach**:
```python
# CORRECT: Use as one signal among many
response = risk_service.analyze(text)
if response["risk_score"] > 0.7:
    # Combine with other signals
    if user_history_clean() and first_offense():
        warn_user()
    else:
        queue_for_human_review()
```

---

### 2. Legal or Policy Compliance ❌

**This system CANNOT determine legal violations**

**Do NOT infer**:
- Legal compliance (GDPR, COPPA, etc.)
- Terms of Service violations
- Community guidelines adherence
- Regulatory requirements

**Example of WRONG inference**:
```python
# WRONG: Treating as legal determination
if risk_category == "HIGH":
    report_to_authorities()  # WRONG - not legal advice
```

**Correct approach**:
```python
# CORRECT: Use as input to legal review
if risk_category == "HIGH":
    flag_for_legal_team_review()
    # Legal team makes actual determination
```

---

### 3. User Intent or Character ❌

**This system CANNOT assess users**

**Do NOT infer**:
- User is "dangerous"
- User is "malicious"
- User intent
- User character

**Example of WRONG inference**:
```python
# WRONG: Inferring user character
if risk_score > 0.9:
    label_user_as_dangerous()  # WRONG - assessing content, not user
```

**Correct approach**:
```python
# CORRECT: Assess content, not user
if risk_score > 0.9:
    flag_content_for_review()
    # Separate system assesses user behavior patterns
```

---

### 4. Absolute Truth ❌

**This system CAN produce false positives/negatives**

**Do NOT infer**:
- Score is "ground truth"
- HIGH = definitely dangerous
- LOW = definitely safe
- System is infallible

**Example of WRONG inference**:
```python
# WRONG: Treating as absolute truth
if risk_category == "LOW":
    approve_without_review()  # WRONG - could be false negative
```

**Correct approach**:
```python
# CORRECT: Use confidence + policy
if risk_category == "LOW" and confidence_score > 0.9:
    auto_approve()
elif risk_category == "LOW" and confidence_score < 0.8:
    sample_for_review()  # Catch false negatives
```

---

### 5. Future Behavior ❌

**This system CANNOT predict future actions**

**Do NOT infer**:
- User will commit violence
- User will violate rules again
- Content will cause harm
- Predictive risk assessment

**Example of WRONG inference**:
```python
# WRONG: Predictive inference
if "kill" in text:
    preemptively_ban_user()  # WRONG - not predictive
```

**Correct approach**:
```python
# CORRECT: Assess current content only
if risk_score > threshold:
    flag_current_content()
    # Separate system tracks patterns over time
```

---

## Safe Consumption Patterns

### Pattern 1: Two-Key Rule ✅

**Principle**: Destructive actions require two independent signals

```python
def should_delete_content(text, user_id):
    # Signal 1: Risk score
    risk_response = risk_service.analyze(text)
    
    # Signal 2: User history
    user_violations = get_user_violation_count(user_id)
    
    # Both signals required
    if risk_response["risk_score"] > 0.9 and user_violations > 3:
        if risk_response["confidence_score"] > 0.8:
            return True
    
    return False
```

---

### Pattern 2: Confidence-Gated Automation ✅

**Principle**: Only automate high-confidence decisions

```python
def process_content(text):
    response = risk_service.analyze(text)
    
    if response["confidence_score"] > 0.9:
        # High confidence: can automate
        if response["risk_score"] > 0.9:
            auto_flag()
        elif response["risk_score"] < 0.3:
            auto_approve()
    else:
        # Low confidence: always review
        queue_for_human_review()
```

---

### Pattern 3: Policy Layer Separation ✅

**Principle**: Separate signal from decision

```python
class PolicyEngine:
    def __init__(self, risk_service):
        self.risk_service = risk_service
        self.thresholds = load_business_thresholds()
    
    def evaluate(self, text, context):
        # Get signal
        signal = self.risk_service.analyze(text)
        
        # Apply policy
        decision = self.apply_policy(signal, context)
        
        # Audit separately
        self.audit(signal, decision, context)
        
        return decision
    
    def apply_policy(self, signal, context):
        # YOUR business logic here
        # Not the risk service's responsibility
        pass
```

---

### Pattern 4: Human-in-the-Loop ✅

**Principle**: High-stakes decisions require human review

```python
def moderate_content(text, stakes="high"):
    response = risk_service.analyze(text)
    
    if stakes == "high":
        # High stakes: always human review
        return queue_for_human_review(response)
    
    elif response["risk_score"] > 0.7:
        # Medium stakes, high risk: human review
        return queue_for_human_review(response)
    
    elif response["confidence_score"] < 0.8:
        # Low confidence: human review
        return queue_for_human_review(response)
    
    else:
        # Low stakes, low risk, high confidence: can automate
        return auto_process(response)
```

---

### Pattern 5: Circuit Breaker ✅

**Principle**: Prevent mass-enforcement cascades

```python
class EnforcementCircuitBreaker:
    def __init__(self, max_actions_per_minute=10):
        self.max_actions = max_actions_per_minute
        self.action_count = 0
        self.window_start = time.time()
    
    def can_take_action(self):
        # Reset window if needed
        if time.time() - self.window_start > 60:
            self.action_count = 0
            self.window_start = time.time()
        
        # Check limit
        if self.action_count >= self.max_actions:
            alert_admin("Circuit breaker triggered")
            return False
        
        self.action_count += 1
        return True
    
    def enforce(self, text):
        response = risk_service.analyze(text)
        
        if response["risk_score"] > 0.9:
            if self.can_take_action():
                take_enforcement_action()
            else:
                queue_for_later_review()
```

---

## Forbidden Patterns

### Anti-Pattern 1: Direct Execution ❌

```python
# WRONG: Direct signal-to-action
response = risk_service.analyze(text)
if response["risk_category"] == "HIGH":
    delete_content()  # NO POLICY LAYER
```

---

### Anti-Pattern 2: Ignoring Confidence ❌

```python
# WRONG: Ignoring confidence score
response = risk_service.analyze(text)
if response["risk_score"] > 0.7:
    ban_user()  # Didn't check confidence
```

---

### Anti-Pattern 3: Indefinite Caching ❌

```python
# WRONG: Caching forever
cache[text_hash] = risk_score  # No TTL
# Later: use stale score
```

---

### Anti-Pattern 4: Cross-Domain Reuse ❌

```python
# WRONG: Using gaming chat scores for news
gaming_score = cache["attack_in_gaming"]
use_for_news_article("attack")  # Different context
```

---

### Anti-Pattern 5: Blind Aggregation ❌

```python
# WRONG: Aggregating without confidence
avg = (score1 + score2 + score3) / 3  # Ignores confidence
if avg > 0.7:
    take_action()
```

---

## Integration Checklist

Before deploying your enforcement system:

### Required ✅
- [ ] Policy layer separate from risk scoring
- [ ] Human review for high-stakes decisions
- [ ] Confidence threshold for automation
- [ ] Two-Key Rule for destructive actions
- [ ] Circuit breaker for mass-enforcement
- [ ] Audit trail (signal + policy + action)
- [ ] Error handling (service unavailable)
- [ ] Cache with appropriate TTL (< 1 hour)
- [ ] Verify safety_metadata before acting
- [ ] Appeals process for users

### Forbidden ❌
- [ ] Direct signal-to-action mapping
- [ ] Ignoring confidence scores
- [ ] Treating as legal/policy compliance
- [ ] Inferring user intent or character
- [ ] Indefinite caching
- [ ] Cross-domain cache reuse
- [ ] Blind score aggregation
- [ ] Assuming semantic understanding
- [ ] Using as sole basis for decisions
- [ ] Treating as absolute truth

---

## Example: InsightBridge Integration

```python
class InsightBridge:
    def __init__(self, risk_service):
        self.risk_service = risk_service
        self.policy = PolicyEngine()
        self.circuit_breaker = CircuitBreaker()
    
    def process_content(self, content, user_id, context):
        # Step 1: Get risk signal
        signal = self.risk_service.analyze(content["text"])
        
        # Step 2: Verify signal-only nature
        assert signal["safety_metadata"]["is_decision"] is False
        
        # Step 3: Apply policy layer
        policy_decision = self.policy.evaluate(
            signal=signal,
            user_history=get_user_history(user_id),
            context=context
        )
        
        # Step 4: Check confidence
        if signal["confidence_score"] < 0.8:
            return self.queue_for_review(signal, policy_decision)
        
        # Step 5: Apply Two-Key Rule
        if policy_decision["action"] == "DELETE":
            if not self.circuit_breaker.can_act():
                return self.queue_for_review(signal, policy_decision)
            
            # Require second signal
            if self.has_second_signal(user_id):
                return self.execute_with_audit(policy_decision)
        
        # Step 6: Audit
        self.audit(signal, policy_decision, context)
        
        return policy_decision
```

---

## Example: Workflow Executor Integration

```python
class WorkflowExecutor:
    def __init__(self, risk_service):
        self.risk_service = risk_service
    
    def execute_moderation_workflow(self, content):
        # Step 1: Risk assessment
        risk_signal = self.risk_service.analyze(content)
        
        # Step 2: Route based on confidence
        if risk_signal["confidence_score"] < 0.7:
            return self.route_to_human_review(risk_signal)
        
        # Step 3: Route based on risk + policy
        if risk_signal["risk_score"] > 0.9:
            return self.route_to_senior_moderator(risk_signal)
        elif risk_signal["risk_score"] > 0.6:
            return self.route_to_moderator(risk_signal)
        else:
            return self.auto_approve_with_sampling(risk_signal)
    
    def route_to_human_review(self, signal):
        return {
            "action": "HUMAN_REVIEW",
            "priority": "HIGH" if signal["risk_score"] > 0.7 else "NORMAL",
            "signal": signal,
            "reason": "Low confidence or high risk"
        }
```

---

## Fail-Safe Defaults

### Service Unavailable
```python
try:
    response = risk_service.analyze(text)
except ServiceUnavailable:
    # Fail closed: queue for review
    queue_for_manual_review(text)
    # Do NOT assume safe and auto-approve
```

### Ambiguous Result
```python
response = risk_service.analyze(text)
if response["confidence_score"] < 0.7:
    # Ambiguous: route to human
    queue_for_review(response)
```

### Rate Limit Exceeded
```python
if circuit_breaker.is_open():
    # Too many actions: pause automation
    queue_all_for_review()
    alert_admin("Circuit breaker open")
```

---

## Audit Requirements

### Minimum Audit Trail

```python
audit_entry = {
    "timestamp": now(),
    "content_id": content_id,
    "user_id": user_id,
    
    # Risk signal (from this service)
    "risk_signal": {
        "risk_score": response["risk_score"],
        "confidence_score": response["confidence_score"],
        "risk_category": response["risk_category"],
        "trigger_reasons": response["trigger_reasons"]
    },
    
    # Policy decision (YOUR responsibility)
    "policy_decision": {
        "decision": "DELETE",
        "policy_rule": "Rule 3.2: High risk + repeat offender",
        "decided_by": "policy_engine_v2"
    },
    
    # Action taken (YOUR responsibility)
    "action": {
        "action_type": "DELETE",
        "executed_by": "workflow_executor",
        "human_reviewed": True,
        "reviewer_id": "moderator_123"
    }
}
```

---

## Support & Escalation

### When to Escalate

1. **False Positive Rate > 10%**: Review your policy thresholds
2. **False Negative Rate > 5%**: Consider additional signals
3. **Low Confidence > 30%**: Content may be outside training domain
4. **Service Errors > 1%**: Check service health

### What to Report

- Input text (sanitized)
- Risk signal received
- Expected vs. actual behavior
- Your policy decision
- Action taken

---

## Conclusion

**Remember**: This service provides **signals**, not **decisions**.

Your enforcement system is responsible for:
- Policy interpretation
- Business logic
- Human review
- Final decisions
- Audit trails
- User appeals

This service is responsible for:
- Keyword detection
- Risk scoring
- Explainable triggers
- Deterministic behavior
- Non-authority declaration

**Use this service as ONE INPUT to your decision-making process, never as the SOLE BASIS for consequential actions.**
