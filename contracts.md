# Contracts - Text Risk Scoring Service (SEALED)

**CONTRACT VERSION: 1.0.0 - IMMUTABLE**  
**SEALED DATE: 2024**  
**MODIFICATION POLICY: FORBIDDEN**

This document defines the **immutable and final** API contracts for the Text Risk Scoring Service. These contracts are **SEALED** and cannot be modified without breaking compatibility.

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

## Output Contract (SEALED)

### Response Schema (IMMUTABLE)
```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_category": "LOW|MEDIUM|HIGH",
  "trigger_reasons": ["string"],
  "processed_length": 0,
  "errors": null | {
    "error_code": "string",
    "message": "string"
  }
}
```

### Required Fields (ALL MANDATORY)
- **risk_score** (number) - Always present
- **confidence_score** (number) - Always present  
- **risk_category** (string) - Always present
- **trigger_reasons** (array) - Always present
- **processed_length** (number) - Always present
- **errors** (object|null) - Always present

### Forbidden Fields
- No additional fields allowed
- No field removal permitted
- No field renaming allowed

### Output Limits (ABSOLUTE)
- **risk_score**: 0.0 ≤ value ≤ 1.0 (2 decimal places)
- **confidence_score**: 0.0 ≤ value ≤ 1.0 (2 decimal places)
- **risk_category**: Exactly one of ["LOW", "MEDIUM", "HIGH"]
- **trigger_reasons**: Array of strings, 0-100 elements max
- **processed_length**: 0 ≤ value ≤ 5000
- **errors**: null OR {error_code: string, message: string}

### Output Validation Rules
1. **Type Enforcement**: All fields must match exact types
2. **Range Enforcement**: Numeric values within bounds
3. **Enum Enforcement**: risk_category must be valid enum
4. **Array Enforcement**: trigger_reasons must be string array
5. **Error Enforcement**: errors must be null or valid error object

## Error Contract (SEALED)

### Error Response Structure (IMMUTABLE)
```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_category": "LOW",
  "trigger_reasons": [],
  "processed_length": 0,
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
- **Output contract**: Will never change
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