# Decision Semantics - Text Risk Scoring Service

**Version**: 1.0.0  
**Status**: SEALED  
**Purpose**: Define exact meaning of all outputs and prevent misinterpretation

---

## What This Service Does

### Primary Function
**Generates risk signals from text input using deterministic keyword matching.**

This service:
- ✅ Analyzes text for predefined risk keywords
- ✅ Assigns numeric risk scores (0.0 - 1.0)
- ✅ Categorizes risk level (LOW/MEDIUM/HIGH)
- ✅ Provides explicit trigger reasons
- ✅ Returns confidence scores for signal quality
- ✅ Operates deterministically (same input → same output)

### Signal Generation Only
**This is a signal generator, NOT a decision maker.**

The service produces:
- Risk indicators
- Pattern matches
- Structured data for downstream systems
- Explainable reasoning

---

## What This Service Does NOT Do

### Explicitly Prohibited Functions

❌ **Does NOT make decisions**
- No autonomous actions
- No executable commands
- No policy enforcement
- No access control

❌ **Does NOT understand context**
- No semantic analysis
- No intent detection
- No sarcasm/irony detection
- No domain-specific interpretation

❌ **Does NOT learn or adapt**
- No model training
- No behavior changes over time
- No personalization
- No feedback incorporation

❌ **Does NOT guarantee accuracy**
- False positives expected
- False negatives expected
- Keyword-based limitations
- No legal/medical validity

❌ **Does NOT provide legal compliance**
- Not a legal tool
- Not regulatory compliant
- Not admissible as evidence
- Not a compliance checker

---

## Score Semantics

### Risk Score (0.0 - 1.0)

**Definition**: Cumulative weight of detected risk keywords, capped at 1.0

#### Score Ranges

**0.0 - 0.29: LOW Risk**
- Meaning: No or minimal risk indicators detected
- Interpretation: Text contains few/no predefined risk keywords
- Action guidance: Minimal scrutiny required
- Confidence: High when score is 0.0, lower as it approaches 0.29

**0.30 - 0.69: MEDIUM Risk**
- Meaning: Moderate presence of risk indicators
- Interpretation: Multiple keywords detected OR single high-weight category
- Action guidance: Human review recommended
- Confidence: Variable based on keyword diversity

**0.70 - 1.0: HIGH Risk**
- Meaning: Strong presence of risk indicators
- Interpretation: Multiple categories triggered OR keyword saturation
- Action guidance: Immediate human review required
- Confidence: Higher with diverse category matches

#### Score Calculation
```
risk_score = Σ(keyword_matches × 0.2) per category
           capped at 0.6 per category
           capped at 1.0 total
```

**Key Properties**:
- Deterministic (same keywords → same score)
- Bounded (0.0 ≤ score ≤ 1.0)
- Additive (more keywords → higher score)
- Capped (prevents saturation)

---

### Confidence Score (0.0 - 1.0)

**Definition**: System's confidence in the risk score accuracy

#### Confidence Calculation Logic

**High Confidence (0.8 - 1.0)**
- No keywords detected (clean text)
- Multiple keywords from diverse categories
- Strong pattern consistency

**Medium Confidence (0.5 - 0.79)**
- Single keyword detected
- Keywords from single category only
- Ambiguous patterns

**Low Confidence (0.0 - 0.49)**
- Single keyword + single category
- Minimal evidence
- High false positive risk

#### Confidence Factors
```
confidence = 1.0
if keyword_count == 1: confidence -= 0.3
if category_count > 1: confidence -= 0.2
if keyword_count <= 2: confidence -= 0.2
confidence = clamp(confidence, 0.0, 1.0)
```

**Interpretation**:
- Low confidence → Treat signal with skepticism
- High confidence → Signal more reliable
- Confidence ≠ Accuracy (keyword-based limitations remain)

---

### Risk Category (LOW/MEDIUM/HIGH)

**Definition**: Discrete classification based on risk score thresholds

#### Category Semantics

**LOW**
- Score range: 0.0 - 0.29
- Meaning: Minimal or no risk indicators
- Typical triggers: 0-1 keywords
- Recommended action: Standard processing
- False positive rate: Low
- False negative rate: High (misses subtle risks)

**MEDIUM**
- Score range: 0.30 - 0.69
- Meaning: Moderate risk indicators present
- Typical triggers: 2-3 keywords OR single high-risk category
- Recommended action: Human review
- False positive rate: Moderate
- False negative rate: Moderate

**HIGH**
- Score range: 0.70 - 1.0
- Meaning: Strong risk indicators present
- Typical triggers: Multiple categories OR keyword saturation
- Recommended action: Immediate review + escalation
- False positive rate: Higher (aggressive detection)
- False negative rate: Lower (catches most keyword matches)

#### Threshold Boundaries
```
if score < 0.3:  category = "LOW"
if 0.3 ≤ score < 0.7:  category = "MEDIUM"
if score ≥ 0.7:  category = "HIGH"
```

**Critical Note**: Thresholds are fixed and deterministic. Same score always produces same category.

---

## Trigger Reasons Semantics

**Definition**: Explicit list of detected keywords and their categories

### Format
```json
"trigger_reasons": [
  "Detected violence keyword: kill",
  "Detected fraud keyword: scam",
  "Input text was truncated to safe maximum length"
]
```

### Interpretation
- Each reason corresponds to a specific keyword match
- Category name indicates risk domain
- Keyword shown is exact match (case-insensitive)
- Order is non-deterministic (set-based)
- Empty array = no keywords detected

### Usage
- Explainability: Shows why score was assigned
- Debugging: Validates detection logic
- Human review: Guides reviewer attention
- Audit trail: Documents decision basis

---

## Safety Metadata Semantics

**Definition**: Explicit declaration of system authority and limitations

### Fields

**is_decision**: Always `false`
- Meaning: Output is NOT an executable decision
- Interpretation: Requires human judgment
- Usage: Prevent autonomous action

**authority**: Always `"NONE"`
- Meaning: System has NO decision-making authority
- Interpretation: Cannot enforce actions
- Usage: Prevent misuse as policy engine

**actionable**: Always `false`
- Meaning: Output is NOT directly actionable
- Interpretation: Requires downstream processing
- Usage: Prevent direct execution

### Purpose
Prevents misinterpretation of risk scores as:
- Commands
- Policies
- Executable decisions
- Autonomous actions

---

## What Scores MUST NEVER Be Used For

### Prohibited Use Cases

❌ **Sole basis for automated decisions**
- Content deletion without review
- Account suspension without review
- Access denial without review
- Legal action without review

❌ **Legal or regulatory compliance**
- Evidence in legal proceedings
- Regulatory reporting
- Compliance certification
- Audit documentation

❌ **Medical or psychological assessment**
- Mental health screening
- Suicide risk assessment (as sole input)
- Psychological profiling
- Clinical diagnosis

❌ **Financial decisions**
- Credit scoring
- Fraud detection (as sole input)
- Transaction blocking (without review)
- Account freezing (without review)

❌ **Critical safety decisions**
- Physical security decisions
- Emergency response triggers
- Life-safety systems
- Critical infrastructure protection

❌ **Employment decisions**
- Hiring/firing decisions
- Performance evaluation
- Background checks
- Promotion decisions

❌ **Educational assessment**
- Student evaluation
- Academic integrity (as sole evidence)
- Admission decisions
- Disciplinary action

---

## Correct Interpretation Guidelines

### How to Use Scores Correctly

✅ **As input to human review**
- Flag content for manual inspection
- Prioritize review queue
- Guide reviewer attention
- Provide initial assessment

✅ **As one signal among many**
- Combine with other risk indicators
- Aggregate with behavioral signals
- Contextualize with user history
- Validate with domain expertise

✅ **For demo and evaluation**
- Demonstrate risk detection capability
- Evaluate system behavior
- Test integration patterns
- Validate determinism

✅ **For pre-screening**
- Initial content filtering
- Batch processing triage
- Volume reduction for human review
- Pattern identification

---

## Semantic Boundaries

### What Scores Represent

**Scores represent**:
- Keyword match density
- Pattern presence
- Statistical signal strength
- Deterministic calculation result

**Scores do NOT represent**:
- Intent or motivation
- Actual harm likelihood
- Legal culpability
- Contextual meaning
- Future behavior prediction

### Interpretation Limits

**You can infer**:
- Presence of risk keywords
- Relative keyword density
- Category distribution
- Pattern consistency

**You CANNOT infer**:
- User intent
- Actual threat level
- Contextual appropriateness
- Semantic meaning
- Sarcasm or irony

---

## Error Semantics

### Error Response Interpretation

When `errors` field is non-null:
- Risk score defaults to 0.0 (fail-closed)
- Category defaults to "LOW" (fail-closed)
- Trigger reasons empty
- Processed length = 0

**Error codes**:
- `INVALID_TYPE`: Input not a string
- `EMPTY_INPUT`: Input empty after normalization
- `INVALID_ENCODING`: Invalid UTF-8 sequences
- `INTERNAL_ERROR`: Unexpected system failure

**Interpretation**: Error responses indicate processing failure, NOT low risk. Do not treat as "safe" signal.

---

## Determinism Semantics

### Guaranteed Behavior

**Same input → Same output**
- Identical text produces identical scores
- No randomness
- No external dependencies
- No temporal variation
- No user-specific variation

**Implications**:
- Cacheable results
- Reproducible testing
- Predictable behavior
- Audit trail consistency

**Limitations**:
- Keyword list is static
- No adaptation to new patterns
- No learning from feedback
- No context awareness

---

## Confidence vs. Accuracy

### Critical Distinction

**Confidence Score**: System's self-assessment of signal quality
**Accuracy**: Actual correctness of risk assessment

**Key Points**:
- High confidence ≠ High accuracy
- Low confidence ≠ Low accuracy
- Confidence measures signal strength, not correctness
- Accuracy limited by keyword-based approach

**Example**:
```
Text: "I will kill time before the meeting"
Risk Score: 0.2 (violence keyword: "kill")
Confidence: 0.3 (single keyword, single category)
Actual Risk: None (false positive)
```

Confidence correctly indicates weak signal, but cannot detect false positive.

---

## Semantic Versioning

### Score Meaning Stability

**Guaranteed**:
- Score calculation logic is frozen
- Thresholds are immutable
- Category boundaries are fixed
- Keyword weights are constant

**Not Guaranteed**:
- Keyword list may expand (minor version)
- New categories may be added (minor version)
- Confidence logic may improve (minor version)

**Breaking Changes** (major version):
- Score calculation changes
- Threshold modifications
- Category redefinition
- Weight adjustments

---

## Summary: Decision Semantics Contract

### What Outputs Mean

| Output | Meaning | NOT Meaning |
|--------|---------|-------------|
| risk_score | Keyword match density | Actual threat level |
| confidence_score | Signal quality | Accuracy guarantee |
| risk_category | Score threshold bucket | Decision recommendation |
| trigger_reasons | Detected keywords | Intent or context |
| safety_metadata | Authority disclaimer | Legal protection |

### Usage Contract

**Permitted**: Signal generation, human review input, demo/evaluation
**Prohibited**: Autonomous decisions, legal evidence, medical assessment

### Interpretation Contract

**Reliable**: Keyword detection, deterministic behavior, bounded outputs
**Unreliable**: Intent detection, context understanding, semantic analysis

---

## Seal Statement

**These semantics are FINAL and IMMUTABLE.**

Any change to score meaning, threshold interpretation, or usage guidance constitutes a breaking change requiring major version increment.

All downstream systems MUST interpret outputs according to these semantics.

**Decision Semantics: SEALED ✓**
