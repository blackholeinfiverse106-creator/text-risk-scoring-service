# Contracts - Text Risk Scoring Service (FINAL & SEALED)

**CONTRACT VERSION: 2.0.0 - FINAL**  
**PREVIOUS VERSION: 1.0.0 (Obsolete)**  
**STATUS: SEALED - NO FURTHER CHANGES PERMITTED**  
**SEALED DATE**: Day 1 - Decision Semantics & Authority Discipline

This document defines the **immutable and final** API contracts for the Text Risk Scoring Service. These contracts includes key **Safety & Non-Authority** fields required for the Enforcement-Safe Decision Interface.

**RELATED DOCUMENTS**:
- decision-semantics.md - Defines exact meaning of all outputs
- authority-boundaries.md - Defines system authority limits
- forbidden-usage.md - Defines prohibited use cases

## Contract Enforcement Policy

**ABSOLUTE RULE:** Any deviation from these contracts constitutes a breaking change and is **FORBIDDEN**.

## Input Contract (SEALED)

### Endpoint
```
POST /analyze
```

### Request Schema (IMMUTABLE)
```json
{
  "text": "string"
}
```

### Required Fields
- **text** (string) - MANDATORY, no exceptions

### Forbidden Fields
- Any field other than "text" is **REJECTED**
- No additional properties allowed
- No nested objects permitted

### Input Limits (ABSOLUTE)
- **Type**: Must be string (no null, number, boolean, array, object)
- **Length**: 0 to 5000 characters (enforced)
- **Encoding**: UTF-8 only
- **Content**: Any valid UTF-8 string

### Input Validation Rules
1. **Type Enforcement**: `typeof input.text === "string"`
2. **Length Enforcement**: `0 ≤ input.text.length ≤ 5000`
3. **Field Enforcement**: Only "text" field allowed
4. **Encoding Enforcement**: Valid UTF-8 sequences only

## Output Contract (SAFETY ENHANCED)

### Response Schema (IMMUTABLE)
```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_severity": "LOW|MEDIUM|HIGH",
  "trigger_reasons": ["string"],
  "processed_length": 0,
  "safety_metadata": {
    "is_decision": false,
    "authority": "NONE",
    "actionable": false
  },
  "errors": null | {
    "error_code": "string",
    "message": "string"
  }
}
```

### Required Fields (ALL MANDATORY)
- **risk_score** (number) - Always present
- **confidence_score** (number) - Always present  
- **risk_severity** (string) - Always present (Renamed from risk_category for semantic clarity)
- **trigger_reasons** (array) - Always present
- **processed_length** (number) - Always present
- **safety_metadata** (object) - MANDATORY - Explicit authority denial
- **errors** (object|null) - Always present

### Forbidden Fields
- No additional fields allowed
- No field removal permitted

### Output Limits (ABSOLUTE)
- **risk_score**: 0.0 ≤ value ≤ 1.0 (2 decimal places)
- **confidence_score**: 0.0 ≤ value ≤ 1.0 (2 decimal places)
- **risk_severity**: Exactly one of ["LOW", "MEDIUM", "HIGH"]
- **trigger_reasons**: Array of strings, 0-100 elements max
- **processed_length**: 0 ≤ value ≤ 5000
- **safety_metadata**:
    - **is_decision**: ALWAYS `false`
    - **authority**: ALWAYS `"NONE"`
    - **actionable**: ALWAYS `false`
- **errors**: null OR {error_code: string, message: string}

### Output Validation Rules
1. **Type Enforcement**: All fields must match exact types
2. **Range Enforcement**: Numeric values within bounds
3. **Enum Enforcement**: risk_severity must be valid enum
4. **Safety Enforcement**: `safety_metadata` values MUST match constants associated with non-authority.

## Error Contract (Sealed)

### Error Response Structure (IMMUTABLE)
```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_severity": "LOW",
  "trigger_reasons": [],
  "processed_length": 0,
  "safety_metadata": {
    "is_decision": false,
    "authority": "NONE",
    "actionable": false
  },
  "errors": {
    "error_code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

### Error Codes (COMPLETE SET)
- **INVALID_TYPE** - Input is not a string
- **EMPTY_INPUT** - Input string is empty after normalization
- **EXCESSIVE_LENGTH** - Input exceeds maximum length (handled via truncation)
- **INVALID_ENCODING** - Input contains invalid UTF-8 sequences
- **FORBIDDEN_FIELD** - Request contains forbidden fields
- **MISSING_FIELD** - Required "text" field is missing
- **INTERNAL_ERROR** - Unexpected system error

### Error Guarantees
1. **Deterministic**: Same invalid input → same error
2. **Explicit**: Every error has specific code and message
3. **Non-ambiguous**: Error reason is always clear
4. **Structured**: Errors always follow error contract

## HTTP Contract (SEALED)

### Status Codes (IMMUTABLE)
- **200 OK** - Successful analysis (including handled errors)
- **400 Bad Request** - Contract violation (malformed JSON, etc.)
- **422 Unprocessable Entity** - Schema validation failure
- **500 Internal Server Error** - Unexpected system failure

### Headers (REQUIRED)
- **Content-Type**: application/json (always)
- **Content-Length**: Accurate byte count (always)

## Semantic Limits (ABSOLUTE)

### Input Semantics
- **No interpretation**: System processes text as-is
- **No context awareness**: Each request is independent
- **No state**: System is stateless
- **No learning**: System behavior is fixed

### Output Semantics
- **Signal only**: Output is risk signal, not decision
- **Deterministic**: Same input always produces same output
- **Bounded**: All outputs are within defined ranges
- **Explainable**: All decisions include reasoning
- **Non-Authoritative**: System explicitly disclaims decision power in every response

## Contract Violations

### Invalid Input Matrix
| Input Type | Error Code | HTTP Status |
|------------|------------|-------------|
| null | INVALID_TYPE | 200 |
| number | INVALID_TYPE | 200 |
| boolean | INVALID_TYPE | 200 |
| array | INVALID_TYPE | 200 |
| object | INVALID_TYPE | 200 |
| "" (empty) | EMPTY_INPUT | 200 |
| "   " (whitespace) | EMPTY_INPUT | 200 |
| 5001+ chars | Truncated | 200 |
| Invalid UTF-8 | INVALID_ENCODING | 200 |
| Missing "text" | MISSING_FIELD | 422 |
| Extra fields | FORBIDDEN_FIELD | 422 |

### Enforcement Actions
1. **Type violations** → INVALID_TYPE error response
2. **Length violations** → Truncation with notification
3. **Field violations** → Schema validation failure
4. **Encoding violations** → INVALID_ENCODING error response

## Compatibility Guarantees

### Backward Compatibility
- **Input contract**: Will never change
- **Output contract**: Version 2.0 introduces `safety_metadata` and renames `risk_category` to `risk_severity`.
- **Error codes**: Will never change
- **Field types**: Will never change

### Forward Compatibility
- **No new required fields**: Ever
- **No field removal**: Ever
- **No type changes**: Ever
- **No semantic changes**: Ever

## Contract Verification

### Validation Requirements
1. Every request must pass input validation
2. Every response must pass output validation
3. Every error must follow error contract
4. Every field must be within defined limits

### Testing Requirements
1. All invalid inputs must be tested
2. All error codes must be validated
3. All boundary conditions must be verified
4. All contract violations must be caught

## Seal Statement

**These contracts are SEALED and IMMUTABLE. Any modification requires a new major version and constitutes a breaking change. The system MUST enforce these contracts absolutely with no exceptions.**

**Contract enforcement is mandatory and non-negotiable.**

---

## Day 1 Completion - Decision Semantics & Authority Discipline

**Sealed on**: Day 1  
**Purpose**: Freeze and formalize system behavior and authority boundaries

### What This Service Does (FINAL)
- Generates risk signals from text using deterministic keyword matching
- Assigns numeric risk scores (0.0 - 1.0) based on keyword weights
- Categorizes risk level (LOW/MEDIUM/HIGH) using fixed thresholds
- Provides explicit trigger reasons for explainability
- Returns confidence scores for signal quality assessment
- Operates deterministically (same input → same output, always)

### What This Service Does NOT Do (FINAL)
- ❌ Make decisions or provide decision authority
- ❌ Understand context, intent, or semantic meaning
- ❌ Learn, adapt, or change behavior over time
- ❌ Guarantee accuracy (false positives/negatives expected)
- ❌ Provide legal, medical, or regulatory compliance
- ❌ Predict future behavior or create risk profiles

### Strict Scoring Semantics (FINAL)

**Risk Score (0.0 - 1.0)**:
- 0.0 - 0.29: LOW (minimal risk indicators)
- 0.30 - 0.69: MEDIUM (moderate risk indicators)
- 0.70 - 1.0: HIGH (strong risk indicators)
- Calculation: Σ(keyword_matches × 0.2) per category, capped at 0.6/category, 1.0 total

**Confidence Score (0.0 - 1.0)**:
- System's self-assessment of signal quality
- NOT a guarantee of accuracy
- Factors: keyword count, category diversity, pattern strength

**Risk Category**:
- Discrete classification based on score thresholds
- Deterministic: same score → same category
- Thresholds are immutable

**Trigger Reasons**:
- Explicit list of detected keywords and categories
- Provides explainability and audit trail
- Empty array = no keywords detected

**Safety Metadata** (IMMUTABLE):
- is_decision: Always false
- authority: Always "NONE"
- actionable: Always false
- Purpose: Prevent misinterpretation as executable command

### Scores MUST NEVER Be Used For (FINAL)

❌ **Prohibited Use Cases**:
1. Sole basis for automated decisions (content deletion, account suspension)
2. Legal or regulatory compliance (evidence, reporting, certification)
3. Medical or psychological assessment (suicide risk, mental health screening)
4. Employment decisions (hiring, firing, performance evaluation)
5. Financial decisions (credit scoring, fraud detection as sole input)
6. Critical safety systems (life-safety, emergency response)
7. Educational assessment (academic integrity as sole evidence)
8. Content moderation without human review
9. Surveillance or monitoring without consent
10. Predictive profiling (future behavior, recidivism)

✅ **Permitted Use Cases**:
1. Human-in-the-loop workflows (flag for review, prioritize queues)
2. Multi-signal systems (one input among many)
3. Demo and evaluation (system testing, integration validation)
4. Pre-screening (initial filtering, volume reduction)
5. Research and development (with ethical approval)

### Explicit Misuse Guards (FINAL)

**Technical Safeguards**:
- safety_metadata field in every response
- Explicit authority denial ("NONE")
- Non-decision declaration (is_decision: false)
- Non-actionable flag (actionable: false)

**Documentation Safeguards**:
- decision-semantics.md: Defines exact output meaning
- authority-boundaries.md: Defines system authority limits
- forbidden-usage.md: Lists prohibited use cases
- system-guarantees.md: Defines what is/isn't guaranteed

**Enforcement Mechanisms**:
- Contract validation on every response
- Structured error handling (fail-closed)
- Deterministic behavior (no randomness)
- Bounded outputs (all values within defined ranges)

### Integration Requirements (FINAL)

**Downstream systems MUST**:
1. Check safety_metadata and respect authority limits
2. Implement human review for consequential decisions
3. Combine with other signals (not sole decision factor)
4. Provide appeals and correction mechanisms
5. Maintain audit trails for decisions
6. Comply with applicable laws and regulations
7. Handle false positives/negatives appropriately

**Downstream systems MUST NOT**:
1. Treat outputs as executable commands
2. Use as sole basis for automated actions
3. Assume semantic understanding or intent detection
4. Rely on for legal, medical, or regulatory compliance
5. Use for prohibited use cases (see forbidden-usage.md)

---

## Contract Seal - Day 1 Complete

**Decision Semantics**: SEALED ✓  
**Authority Boundaries**: SEALED ✓  
**Forbidden Usage**: SEALED ✓  
**Contracts**: SEALED ✓

**No further modifications permitted without major version increment.**
