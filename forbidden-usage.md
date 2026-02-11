# Forbidden Usage - Text Risk Scoring Service

**Version**: 1.0.0  
**Status**: SEALED  
**Purpose**: Explicitly define prohibited use cases and misuse scenarios

---

## Critical Warning

**THIS SERVICE MUST NOT BE USED AS THE SOLE BASIS FOR ANY CONSEQUENTIAL DECISION.**

The system is a keyword-based signal generator with known limitations. Using it beyond its design boundaries creates unacceptable risk.

---

## Absolutely Prohibited Use Cases

### 1. Autonomous Decision Making ❌

**FORBIDDEN**: Using risk scores to trigger automated actions without human review

**Examples of Prohibited Use**:
- Automatic content deletion based on HIGH risk score
- Automatic account suspension/banning
- Automatic access denial
- Automatic transaction blocking
- Automatic message filtering without review queue

**Why Prohibited**:
- False positives are expected and common
- No semantic understanding of context
- Cannot detect sarcasm, irony, or legitimate use
- Keyword-based approach is inherently limited

**Acceptable Alternative**:
- Flag content for human review
- Queue for manual inspection
- Provide risk signal to human decision-maker

---

### 2. Legal or Regulatory Compliance ❌

**FORBIDDEN**: Using outputs for legal, regulatory, or compliance purposes

**Examples of Prohibited Use**:
- Evidence in legal proceedings
- Regulatory reporting or certification
- Compliance audit documentation
- Legal liability determination
- Contract enforcement decisions
- Terms of service violation proof

**Why Prohibited**:
- Not legally validated
- No chain of custody
- No expert witness support
- Keyword-based approach insufficient for legal standards
- False positives create legal liability

**Acceptable Alternative**:
- Use as initial screening only
- Combine with legal review
- Supplement with expert analysis

---

### 3. Medical or Psychological Assessment ❌

**FORBIDDEN**: Using for mental health, medical, or psychological evaluation

**Examples of Prohibited Use**:
- Suicide risk assessment (as sole input)
- Mental health screening
- Psychological profiling
- Clinical diagnosis support
- Crisis intervention triggering (without human review)
- Therapy or counseling decisions

**Why Prohibited**:
- Not medically validated
- No clinical expertise
- Cannot assess actual mental state
- False negatives could be life-threatening
- Ethical and legal liability

**Acceptable Alternative**:
- Use as one input to trained professionals
- Combine with clinical assessment
- Never replace human judgment in crisis situations

---

### 4. Employment Decisions ❌

**FORBIDDEN**: Using for hiring, firing, or employment-related decisions

**Examples of Prohibited Use**:
- Candidate screening (as sole criterion)
- Employee monitoring and evaluation
- Termination decisions
- Promotion/demotion decisions
- Performance reviews
- Background check automation
- Workplace investigation evidence

**Why Prohibited**:
- Discriminatory potential
- Legal liability (employment law)
- No validation for employment context
- False positives harm careers
- Privacy concerns

**Acceptable Alternative**:
- Not recommended for employment context at all
- If used, only as one minor input with extensive human oversight

---

### 5. Financial Decisions ❌

**FORBIDDEN**: Using for credit, fraud, or financial risk assessment

**Examples of Prohibited Use**:
- Credit scoring or lending decisions
- Fraud detection (as sole input)
- Transaction blocking without review
- Account freezing without investigation
- Insurance underwriting
- Investment decisions
- Financial background checks

**Why Prohibited**:
- Not financially validated
- Regulatory compliance issues (FCRA, etc.)
- False positives cause financial harm
- No domain-specific financial expertise
- Legal liability

**Acceptable Alternative**:
- Use as one signal in multi-factor fraud detection
- Always require human review before financial action
- Combine with domain-specific fraud tools

---

### 6. Critical Safety Systems ❌

**FORBIDDEN**: Using in life-safety or critical infrastructure systems

**Examples of Prohibited Use**:
- Physical security access control (as sole input)
- Emergency response triggering
- Critical infrastructure protection
- Aviation/transportation safety
- Medical device control
- Industrial safety systems
- Law enforcement decisions

**Why Prohibited**:
- Life-safety implications
- False negatives could be catastrophic
- No safety certification
- Insufficient reliability for critical systems
- Legal and ethical liability

**Acceptable Alternative**:
- Not recommended for safety-critical systems
- If used, only as non-critical supplementary input

---

### 7. Educational Assessment ❌

**FORBIDDEN**: Using for student evaluation or academic decisions

**Examples of Prohibited Use**:
- Academic integrity violation detection (as sole evidence)
- Student disciplinary action
- Grade determination
- Admission decisions
- Scholarship decisions
- Plagiarism detection
- Student monitoring

**Why Prohibited**:
- Educational impact on students
- False positives harm academic records
- No pedagogical validation
- Privacy concerns (FERPA)
- Ethical issues

**Acceptable Alternative**:
- Use as initial flag for instructor review
- Never as sole evidence of academic misconduct
- Combine with human judgment and context

---

### 8. Content Moderation Without Review ❌

**FORBIDDEN**: Fully automated content moderation without human oversight

**Examples of Prohibited Use**:
- Automatic post deletion
- Automatic comment hiding
- Automatic user shadowbanning
- Automatic content demotion
- Automatic account restrictions

**Why Prohibited**:
- High false positive rate
- No context understanding
- Cannot detect legitimate use of flagged words
- Chilling effect on free expression
- Platform liability

**Acceptable Alternative**:
- Flag content for moderator review
- Prioritize review queue by risk score
- Provide context to human moderators
- Allow appeals process

---

### 9. Surveillance or Monitoring ❌

**FORBIDDEN**: Mass surveillance or invasive monitoring

**Examples of Prohibited Use**:
- Employee communication monitoring (without consent/disclosure)
- Student surveillance
- Citizen monitoring
- Social media mass scanning
- Private message interception
- Behavioral profiling

**Why Prohibited**:
- Privacy violations
- Legal issues (wiretapping laws, GDPR, etc.)
- Ethical concerns
- Chilling effect on communication
- Potential for abuse

**Acceptable Alternative**:
- Use only with explicit consent and disclosure
- Limit to specific, justified use cases
- Ensure legal compliance
- Provide transparency and appeals

---

### 10. Predictive Profiling ❌

**FORBIDDEN**: Predicting future behavior or creating risk profiles

**Examples of Prohibited Use**:
- Pre-crime prediction
- Recidivism risk scoring
- Behavioral forecasting
- Threat actor profiling
- Radicalization prediction
- Future harm assessment

**Why Prohibited**:
- System analyzes current text only, not future behavior
- No predictive validity
- Ethical issues (presumption of innocence)
- Discriminatory potential
- Legal liability

**Acceptable Alternative**:
- Analyze current content only
- Do not extrapolate to future behavior
- Combine with actual behavioral evidence

---

## Misuse Scenarios

### Scenario 1: Automated Content Deletion

**Misuse**:
```python
result = analyze_text(user_comment)
if result["risk_category"] == "HIGH":
    delete_comment(user_comment)  # ❌ FORBIDDEN
```

**Why Wrong**:
- No human review
- False positives will delete legitimate content
- No appeals process
- Chilling effect on users

**Correct Usage**:
```python
result = analyze_text(user_comment)
if result["risk_category"] == "HIGH":
    flag_for_review(user_comment, result)  # ✅ CORRECT
    notify_moderator(user_comment, result)
```

---

### Scenario 2: Account Suspension

**Misuse**:
```python
result = analyze_text(user_message)
if result["risk_score"] > 0.7:
    suspend_account(user_id)  # ❌ FORBIDDEN
```

**Why Wrong**:
- Severe consequence without human judgment
- Single message insufficient for account action
- No context consideration
- No appeals process

**Correct Usage**:
```python
result = analyze_text(user_message)
if result["risk_score"] > 0.7:
    add_to_review_queue(user_id, user_message, result)  # ✅ CORRECT
    escalate_to_trust_and_safety_team(user_id)
```

---

### Scenario 3: Legal Evidence

**Misuse**:
```python
result = analyze_text(defendant_message)
submit_as_evidence(result)  # ❌ FORBIDDEN
```

**Why Wrong**:
- Not legally validated
- No expert witness
- Keyword-based approach insufficient for legal standards
- Creates legal liability

**Correct Usage**:
```python
# Do not use for legal purposes at all
# If absolutely necessary, use only as initial screening
# for human legal expert review
```

---

### Scenario 4: Suicide Risk Assessment

**Misuse**:
```python
result = analyze_text(user_message)
if "self_harm" in result["trigger_reasons"]:
    auto_notify_authorities(user_id)  # ❌ FORBIDDEN (without human review)
```

**Why Wrong**:
- Life-safety implications
- False positives cause unnecessary interventions
- False negatives could be fatal
- Requires trained professional assessment

**Correct Usage**:
```python
result = analyze_text(user_message)
if "self_harm" in result["trigger_reasons"]:
    alert_trained_crisis_counselor(user_id, result)  # ✅ CORRECT
    # Let trained professional assess and decide action
```

---

### Scenario 5: Employment Screening

**Misuse**:
```python
result = analyze_text(candidate_social_media)
if result["risk_score"] > 0.5:
    reject_candidate(candidate_id)  # ❌ FORBIDDEN
```

**Why Wrong**:
- Discriminatory potential
- Legal liability (employment law)
- No validation for employment context
- Privacy concerns

**Correct Usage**:
```python
# Do not use for employment decisions at all
# System not designed or validated for this purpose
```

---

## Misuse Detection Patterns

### Red Flags Indicating Misuse

🚩 **No human in the loop**
- Automated actions without review
- No manual approval step
- No appeals process

🚩 **Consequential decisions**
- Account suspension/deletion
- Access denial
- Financial impact
- Legal consequences

🚩 **Sole decision factor**
- Risk score is only input
- No other signals considered
- No context evaluation

🚩 **Critical systems**
- Life-safety implications
- Financial transactions
- Legal proceedings
- Medical decisions

🚩 **Mass surveillance**
- Bulk scanning without consent
- Invasive monitoring
- Privacy violations

---

## Enforcement Mechanisms

### Technical Safeguards

**safety_metadata field**:
```json
{
  "is_decision": false,
  "authority": "NONE",
  "actionable": false
}
```

**Purpose**: Explicitly declare non-authority in every response

**Usage**: Downstream systems MUST check this field and respect limitations

---

### Legal Disclaimers

**Service provides**:
- Risk signals only
- No warranties
- No fitness for particular purpose
- No liability for misuse

**Service does NOT provide**:
- Decision-making capability
- Legal advice
- Medical advice
- Professional expertise

---

### Monitoring and Auditing

**Recommended practices**:
- Log all API calls
- Monitor for automated action patterns
- Audit downstream usage
- Review for prohibited use cases
- Enforce usage policies

---

## Acceptable Use Cases

### What IS Permitted

✅ **Human-in-the-loop workflows**
- Flag content for manual review
- Prioritize review queues
- Provide context to human reviewers

✅ **Multi-signal systems**
- One input among many
- Combined with other risk indicators
- Contextualized with domain expertise

✅ **Demo and evaluation**
- System demonstrations
- Integration testing
- Behavior validation

✅ **Pre-screening**
- Initial content filtering
- Volume reduction for human review
- Pattern identification

✅ **Research and development**
- Algorithm evaluation
- System testing
- Academic research (with ethical approval)

---

## Liability and Responsibility

### User Responsibility

**Users of this service are responsible for**:
- Ensuring appropriate use cases
- Implementing human review
- Complying with applicable laws
- Respecting user privacy
- Providing transparency
- Handling false positives/negatives

### Service Limitations

**Service provider is NOT responsible for**:
- Misuse of outputs
- Downstream decisions
- False positives/negatives
- Legal compliance
- Fitness for particular purpose

---

## Reporting Misuse

If you observe misuse of this service:
1. Document the misuse pattern
2. Identify the prohibited use case
3. Report to service administrators
4. Cease prohibited usage immediately

---

## Summary: Forbidden Usage Contract

### Never Use For

❌ Autonomous decisions without human review
❌ Legal or regulatory compliance
❌ Medical or psychological assessment
❌ Employment decisions
❌ Financial decisions
❌ Critical safety systems
❌ Educational assessment (as sole evidence)
❌ Content moderation without review
❌ Surveillance without consent
❌ Predictive profiling

### Always Require

✅ Human review for consequential decisions
✅ Multi-factor decision making
✅ Context consideration
✅ Appeals process
✅ Legal compliance
✅ Ethical oversight

---

## Seal Statement

**These prohibitions are ABSOLUTE and NON-NEGOTIABLE.**

Violation of these usage restrictions creates unacceptable risk and liability.

All users MUST comply with these restrictions.

**Forbidden Usage: SEALED ✓**
