# API Contract v2 (SEALED)

## 1. Input Contract (POST /analyze)

### Request Schema
```json
{
  "text": "string (1-5000 characters)",
  "context": {
    "caller_id": "string (optional)",
    "role": "string (forbidden: admin, enforcement, etc.)",
    "use_case": "string (optional)"
  }
}
```

### Constraints
- **UTF-8 Encoding**: Mandatory.
- **Forbidden Roles**: Requests with `role` in `["enforcement", "decision_maker", "judge", "execution", "admin"]` will be rejected with `FORBIDDEN_ROLE`.
- **Decision Fields**: Any field in `context` resembling an instruction (e.g., `action`, `decision`, `override`) will be rejected with `DECISION_INJECTION`.

---

## 2. Output Contract

### Response Schema
```json
{
  "risk_score": "float (0.0 - 1.0)",
  "confidence_score": "float (0.0 - 1.0)",
  "risk_category": "string (LOW | MEDIUM | HIGH)",
  "trigger_reasons": "array of strings",
  "processed_length": "integer (0 - 5000)",
  "safety_metadata": {
    "is_decision": "boolean (ALWAYS False)",
    "authority": "string (ALWAYS 'NONE')",
    "actionable": "boolean (ALWAYS False)"
  },
  "errors": "object | null"
}
```

### Guarantees
- **Immutability**: `safety_metadata` fields are non-negotiable and strictly enforced by the contract layer.
- **Fail-Closed**: In case of violation, the system returns a structured error response with `risk_category: LOW`.
