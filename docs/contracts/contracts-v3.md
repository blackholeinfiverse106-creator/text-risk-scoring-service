# API Contract v3 (FROZEN — Integration Release)

**Version:** v3  
**Status:** FROZEN for integration. Changes require v4 and a migration notice.  
**Supersedes:** `contracts-v2.md`  
**Date:** 2026-02-21

---

## Input Contract `POST /analyze`

```json
{
  "text": "string",
  "context": {
    "caller_id": "string (optional)",
    "use_case":  "string (optional)",
    "role":      "string (forbidden — see below)"
  }
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `text` | string | **Yes** | 1–5000 chars, UTF-8 |
| `context` | object | No | Must be a JSON object if present |
| `context.caller_id` | string | No | Opaque identifier, logged |
| `context.use_case` | string | No | Free text, logged |
| `context.role` | string | No (forbidden if set to reserved value) | Triggers `FORBIDDEN_ROLE` if value ∈ `{admin, enforcement, judge, execution, decision_maker}` |

**Forbidden context fields:** `action`, `execute`, `decision`, `perform_action`, `override_risk` — trigger `DECISION_INJECTION`.

**Forbidden top-level fields:** anything other than `text`, `context` — triggers `FORBIDDEN_FIELD`.

---

## Output Contract

```json
{
  "risk_score":       "float [0.0, 1.0]",
  "confidence_score": "float [0.0, 1.0]",
  "risk_category":    "LOW | MEDIUM | HIGH",
  "trigger_reasons":  ["string"],
  "processed_length": "int [0, 5000]",
  "safety_metadata": {
    "is_decision": false,
    "authority":   "NONE",
    "actionable":  false
  },
  "errors": null
}
```

**Absolute guarantees (structurally enforced, not configurable):**

| Field | Guaranteed value | Enforcement |
|---|---|---|
| `safety_metadata.is_decision` | `false` always | `validate_output_contract()` |
| `safety_metadata.authority` | `"NONE"` always | `validate_output_contract()` |
| `safety_metadata.actionable` | `false` always | `validate_output_contract()` |

---

## Error Response

On any error, the normal response shape is returned with `errors != null`:

```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_category": "LOW",
  "trigger_reasons": [],
  "processed_length": 0,
  "safety_metadata": { "is_decision": false, "authority": "NONE", "actionable": false },
  "errors": {
    "error_code": "EMPTY_INPUT",
    "message": "Text is empty"
  }
}
```

**Valid error codes:** `EMPTY_INPUT`, `INVALID_TYPE`, `FORBIDDEN_ROLE`, `DECISION_INJECTION`, `FORBIDDEN_FIELD`, `MISSING_FIELD`, `INVALID_CONTEXT`, `INVALID_ENCODING`, `INTERNAL_ERROR`

---

## Stability Contract

| Element | v3 Guarantee |
|---|---|
| All output field names | Stable |
| `safety_metadata` shape | Stable and immutable |
| Risk categories (LOW/MEDIUM/HIGH) | Stable |
| Error codes | Stable |
| Score formula / thresholds | Stable (0.3/0.7 boundaries) |
| `trigger_reasons` content | Unstable (informational, may change) |
| `message` in errors | Unstable (human-readable) |
