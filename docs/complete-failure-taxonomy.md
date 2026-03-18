# Complete Failure Taxonomy

## 1. Input Errors (Client-Side)
Errors caused by malformed or invalid client requests. Always actionable by the client.

| Code | Description | HTTP Status | Action |
| :--- | :--- | :--- | :--- |
| `EMPTY_INPUT` | Input string is empty after trimming. | 400 | Provide non-empty text. |
| `INVALID_TYPE` | Input is not a JSON string. | 422 | Ensure `text` field is a string. |
| `EXCESSIVE_LENGTH` | Input exceeds 5000 chars. | 400 | Truncate input before sending. |
| `INVALID_JSON` | Malformed JSON body. | 400 | Fix JSON syntax. |
| `DECISION_INJECTION`| Client attempted to inject decision fields. | 403 | Remove `decision` or `override` fields. |

## 2. Execution Errors (System-Side)
Unexpected runtime failures. Indicates a bug or infrastructure issue.

| Code | Description | Severity | Policy |
| :--- | :--- | :--- | :--- |
| `INTERNAL_ERROR` | Unhandled exception (e.g., KeyError). | High | Log stack trace, return 500. |
| `TIMEOUT` | Processing exceeded time limit. | Medium | Retry with backoff. |
| `RESOURCE_EXHAUSTED`| System OOM or CPU starvation. | Critical | Fail closed, alert SRE. |

## 3. Scoring Violations (Logic Integrity)
Logic invariants broken during execution.

| Code | Description | Handling |
| :--- | :--- | :--- |
| `INVARIANT_VIOLATION`| Score/Category mismatch (e.g. 0.9/LOW). | **Fail-Closed**: Force Risk=HIGH, Log Error. |
| `IMPOSSIBLE_STATE` | Negative score or NaN. | **Fail-Closed**: Return Error, do not score. |

## 4. Resource Exhaustion (DoS Protection)
| Limit | Threshold | Consequence |
| :--- | :--- | :--- |
| **Payload Size** | 5000 chars | Truncation + Warning Log. |
| **Request Rate** | Defined at Gateway | 429 Too Many Requests. |
| **Recursion Depth** | Flat (Iterative only) | N/A (By Design). |
