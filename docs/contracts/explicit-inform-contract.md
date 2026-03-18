# Explicit Inform-Only Contract

## Version: 1.0.0 (SEALED)

This document formally defines the immutable contract for the `Text Risk Scoring Service` API response. Any deviation from this contract is considered a critical system failure.

## 1. Safety Metadata Schema
Every API response **MUST** include the `safety_metadata` object with the following **FIXED** values.

```json
"safety_metadata": {
    "is_decision": false,
    "authority": "NONE",
    "actionable": false
}
```

### Field Definitions
| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| **`is_decision`** | `boolean` | **MUST BE `false`** | Indicates that the response is NOT a final decision. |
| **`authority`** | `string` | **MUST BE `"NONE"`** | Indicates the service claims NO authority over the content. |
| **`actionable`** | `boolean` | **MUST BE `false`** | Indicates the response itself is NOT sufficient for autonomous action. |

## 2. Response Constraints

### 2.1 No Decision Synthesis
The service guarantees it will **NEVER**:
- Return a field named `decision`, `verdict`, `outcome`, or `action`.
- Return values implying a decision (e.g., `status: "BLOCKED"`).

### 2.2 Error Safety
In the event of an internal error, the service **MUST**:
- Return a valid JSON response (if possible) or HTTP error.
- **NEVER** fail open with a default "safe" or "unsafe" signal that looks like a valid score.
- **ALWAYS** set `risk_score` to `0.0` and populates the `errors` object if a partial response is returned.

## 3. Schema Enforcement
The application code (`app/engine.py`) enforces this contract by:
1.  Hardcoding the `safety_metadata` dictionary.
2.  Using type-safe schemas (`app/schemas.py`) that require these fields.
3.  Unit tests (`tests/forbidden_usage_tests.py`) that verify these values are immutable across all input types.

## 4. Consumer Obligation
Consumers of this API **MUST** validate this metadata.
> If `is_decision` is `true`, the consumer **MUST** treat the system as compromised and Halt Operations.
