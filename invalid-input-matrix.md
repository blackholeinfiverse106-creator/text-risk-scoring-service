# Invalid Input Matrix - Text Risk Scoring Service

This document provides a **complete and exhaustive** matrix of all possible invalid inputs and their deterministic handling by the system.

## Contract Enforcement Guarantee

**ABSOLUTE RULE:** Every invalid input produces:
1. **Deterministic failure** - Same input always produces same error
2. **Explicit error code** - Specific, unambiguous error identifier  
3. **Non-ambiguous reason** - Clear explanation of what went wrong

## Invalid Input Classification

### Category 1: Type Violations

| Input Value | Input Type | Error Code | Error Message | HTTP Status |
|-------------|------------|------------|---------------|-------------|
| `null` | null | INVALID_TYPE | Input must be a string | 200 |
| `123` | number | INVALID_TYPE | Input must be a string | 200 |
| `true` | boolean | INVALID_TYPE | Input must be a string | 200 |
| `[]` | array | INVALID_TYPE | Input must be a string | 200 |
| `{}` | object | INVALID_TYPE | Input must be a string | 200 |

**Handling:** All type violations are caught at the engine level and return structured error responses.

### Category 2: Content Violations

| Input Value | Description | Error Code | Error Message | HTTP Status |
|-------------|-------------|------------|---------------|-------------|
| `""` | Empty string | EMPTY_INPUT | Text is empty | 200 |
| `"   "` | Whitespace only | EMPTY_INPUT | Text is empty | 200 |
| `"\t\n "` | Mixed whitespace | EMPTY_INPUT | Text is empty | 200 |

**Handling:** Content is normalized (trimmed, lowercased) before validation. Empty content after normalization triggers EMPTY_INPUT error.

### Category 3: Length Violations

| Input Length | Description | Handling | Response Modification |
|--------------|-------------|----------|----------------------|
| 0 chars | Empty | Error response | EMPTY_INPUT error |
| 1-5000 chars | Valid range | Normal processing | No modification |
| 5001+ chars | Excessive | Truncation | Added to trigger_reasons |

**Handling:** Excessive length is handled via deterministic truncation, not rejection. The truncation is logged and reported in trigger_reasons.

### Category 4: Structure Violations

| Request Structure | Error Code | Error Message | HTTP Status |
|-------------------|------------|---------------|-------------|
| Missing "text" field | MISSING_FIELD | Required field 'text' is missing | 422 |
| Extra fields present | FORBIDDEN_FIELD | Forbidden fields: [field_names] | 422 |
| Non-JSON request | INVALID_REQUEST | Request must be JSON object | 422 |
| Malformed JSON | INVALID_REQUEST | Request must be JSON object | 400 |

**Handling:** Structure violations are caught at the API contract layer before reaching the engine.

### Category 5: Encoding Violations

| Input Content | Description | Error Code | Error Message | HTTP Status |
|---------------|-------------|------------|---------------|-------------|
| Invalid UTF-8 | Malformed encoding | INVALID_ENCODING | Text contains invalid UTF-8 sequences | 200 |
| Binary data | Non-text content | INVALID_ENCODING | Text contains invalid UTF-8 sequences | 200 |

**Handling:** Encoding validation occurs during contract enforcement.

## Error Response Structure

All invalid inputs produce responses following this **immutable structure**:

```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_category": "LOW",
  "trigger_reasons": [],
  "processed_length": 0,
  "errors": {
    "error_code": "ERROR_CODE",
    "message": "Human readable explanation"
  }
}
```

## Determinism Verification

### Same Input → Same Output

| Test Input | Expected Error Code | Determinism Verified |
|------------|--------------------|--------------------|
| `null` | INVALID_TYPE | ✅ |
| `123` | INVALID_TYPE | ✅ |
| `true` | INVALID_TYPE | ✅ |
| `[]` | INVALID_TYPE | ✅ |
| `{}` | INVALID_TYPE | ✅ |
| `""` | EMPTY_INPUT | ✅ |
| `"   "` | EMPTY_INPUT | ✅ |
| Missing field | MISSING_FIELD | ✅ |
| Extra fields | FORBIDDEN_FIELD | ✅ |

### Error Code Stability

All error codes are **immutable** and will never change:
- `INVALID_TYPE` - Type validation failure
- `EMPTY_INPUT` - Empty content after normalization
- `INVALID_ENCODING` - UTF-8 encoding violation
- `MISSING_FIELD` - Required field missing
- `FORBIDDEN_FIELD` - Extra fields present
- `INVALID_REQUEST` - Malformed request structure
- `INTERNAL_ERROR` - Unexpected system error

## Boundary Conditions

### Edge Cases Matrix

| Edge Case | Input Example | Expected Behavior |
|-----------|---------------|-------------------|
| Minimum valid | `"a"` | Normal processing |
| Maximum valid | `"a" * 5000` | Normal processing |
| Just over limit | `"a" * 5001` | Truncation to 5000 |
| Unicode content | `"🔥💀☠️"` | Normal processing |
| Mixed content | `"hello 世界"` | Normal processing |
| Only numbers | `"123456"` | Normal processing |
| Only symbols | `"!@#$%^"` | Normal processing |

### Special Character Handling

| Character Type | Example | Handling |
|----------------|---------|----------|
| Unicode emoji | `"😀😃😄"` | Normal processing |
| Unicode text | `"こんにちは"` | Normal processing |
| Control chars | `"\x00\x01\x02"` | Normal processing |
| Newlines | `"line1\nline2"` | Normal processing |
| Tabs | `"word1\tword2"` | Normal processing |

## Contract Violation Responses

### HTTP Status Code Mapping

| Violation Type | HTTP Status | Response Body |
|----------------|-------------|---------------|
| Type violation | 200 | Structured error response |
| Content violation | 200 | Structured error response |
| Length violation | 200 | Truncation handling |
| Structure violation | 422 | Structured error response |
| JSON malformation | 400 | HTTP error response |
| System error | 500 | HTTP error response |

## Testing Coverage

### Required Test Cases

Every entry in this matrix **MUST** have corresponding test cases:

1. **Type Violation Tests** - All non-string types
2. **Content Violation Tests** - Empty and whitespace-only inputs
3. **Length Violation Tests** - Boundary conditions around 5000 chars
4. **Structure Violation Tests** - Missing/extra fields
5. **Encoding Violation Tests** - Invalid UTF-8 sequences
6. **Determinism Tests** - Same input produces same output
7. **Error Structure Tests** - All errors follow contract

### Verification Requirements

1. **Completeness** - All possible invalid inputs covered
2. **Determinism** - Same input always produces same error
3. **Explicitness** - Every error has clear code and message
4. **Non-ambiguity** - Error reasons are unambiguous
5. **Contract Compliance** - All responses follow output contract

## Matrix Completeness Guarantee

**This matrix is COMPLETE and EXHAUSTIVE.** No invalid input exists outside these categories. Any input not covered by this matrix is by definition valid and will be processed normally.

**Contract enforcement is absolute and non-negotiable.**