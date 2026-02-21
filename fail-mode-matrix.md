# Fail-Mode Matrix

**Generated:** 2026-02-21  
**Source of truth:** `app/engine.py`, `app/contract_enforcement.py`

> **Fail-open**: The engine returns a safe, structured response with `errors != null`. The caller receives  
> a 200 OK and can proceed safely (no enforcement, log the error, let request through with pending-review flag).  
>
> **Fail-closed**: The engine either returns an explicit error structure with `risk_score: 0.0` that  
> signals the caller to NOT auto-act, or the process exits entirely.

---

## Input Layer Failures (Contract Enforcement)

These are caught by `validate_input_contract()` before the engine runs.

| Error Code | Trigger | Fail Mode | HTTP Status | Response | Caller Action |
|---|---|---|---|---|---|
| `INVALID_REQUEST` | Body is not a JSON object | **Fail-open** | 422 | Pydantic validation error | Fix client payload |
| `MISSING_FIELD` | `text` field absent | **Fail-open** | 422 | Pydantic validation error | Fix client payload |
| `FORBIDDEN_FIELD` | Extra top-level field | **Fail-open** | 422 | Contract violation detail | Fix client payload |
| `INVALID_CONTEXT` | `context` is not a dict | **Fail-open** | 422 | Contract violation detail | Fix client payload |
| `FORBIDDEN_ROLE` | `context.role` is forbidden | **Fail-open** | 200 | `errors.error_code: FORBIDDEN_ROLE` | Remove role from request |
| `DECISION_INJECTION` | Forbidden decision field | **Fail-open** | 200 | `errors.error_code: DECISION_INJECTION` | Remove forbidden field |

**Common invariants for all input failures:**
```json
{
  "risk_score": 0.0,
  "confidence_score": 0.0,
  "risk_category": "LOW",
  "trigger_reasons": [],
  "safety_metadata": { "is_decision": false, "authority": "NONE", "actionable": false },
  "errors": { "error_code": "<CODE>", "message": "<human-readable>" }
}
```

---

## Engine Layer Failures (analyze_text)

These are handled inside `analyze_text()` in `app/engine.py`.

| Error Code / Event | Trigger | Fail Mode | HTTP Status | Response | Caller Action |
|---|---|---|---|---|---|
| `EMPTY_INPUT` | Text is empty after strip/lower | **Fail-open** | 200 | Error response | Log and drop request |
| `INVALID_TYPE` | `text` is not a string | **Fail-open** | 200 | Error response | Fix caller / SDK bug |
| `INVALID_ENCODING` | Text fails UTF-8 encode | **Fail-open** | 200 | Error response | Sanitize input encoding |
| `input_truncated` (event) | `len(text) > 5000` | **Fail-open** | 200 | Valid response + truncation note | No action; note in audit |
| `category_capped` (event) | `category_score > 0.6` | **Fail-open** | 200 | Valid adjusted response | No action needed |
| `score_clamped` (event) | `total_score > 1.0` | **Fail-open** | 200 | Valid adjusted response, `risk_score: 1.0` | No action needed |
| `invariant_correction` (event) | Score/category mismatch detected and self-corrected | **Fail-open** | 200 | Valid corrected response | **Alert** — indicates logic regression |
| `INTERNAL_ERROR` | Any uncaught exception in outer try/except | **Fail-closed** | 200 | `errors.error_code: INTERNAL_ERROR` | Do not act on score; flag for review |

> Note: `INTERNAL_ERROR` is called fail-closed because `risk_score: 0.0` with an explicit error forces  
> the caller into a "do not enforce" state. The term is relative — the process survives, but the  
> response signals that the normal scoring path did not complete.

---

## Output Layer Failures (Contract Validation)

These are caught by `validate_output_contract()` when called explicitly (e.g., in tests or decorators).

| Error Code | Trigger | Fail Mode | Effect |
|---|---|---|---|
| `INVALID_IS_DECISION` | `is_decision != False` | **Fail-closed** | `ContractViolation` exception — caller must handle |
| `INVALID_AUTHORITY` | `authority != "NONE"` | **Fail-closed** | `ContractViolation` exception |
| `INVALID_ACTIONABLE` | `actionable != False` | **Fail-closed** | `ContractViolation` exception |
| `FORBIDDEN_OUTPUT_FIELD` | Extra field in response | **Fail-closed** | `ContractViolation` exception |
| `INVALID_RISK_SCORE_RANGE` | `risk_score` outside `[0.0, 1.0]` | **Fail-closed** | `ContractViolation` exception |
| `MISSING_OUTPUT_FIELD` | Required field absent | **Fail-closed** | `ContractViolation` exception |

These violations should never occur in production (the engine is deterministic). Their presence indicates a regression or a mutation attack (see `escalation-tests/test_output_mutation.py`).

---

## Process-Level Failures

| Failure | Trigger | Fail Mode | Caller Experience | Recovery |
|---|---|---|---|---|
| OOM kill | Container memory limit exceeded | **Fail-closed** | Connection reset / timeout | Container auto-restart |
| Disk full | Log volume exhausted | **Fail-closed** | Eventual timeout or 503 | Clear logs, expand volume |
| CPU starvation | Thread exhaustion under extreme load | **Fail-open** (slow) | Increased latency, eventual timeout | Horizontal scale |
| Process crash (unhandled signal) | SIGKILL / SIGSEGV | **Fail-closed** | Connection reset | Container auto-restart |

---

## Decision Tree for Callers

```
Response received?
├── YES:
│   ├── errors == null?
│   │   ├── YES → Normal path. Consume risk_score.
│   │   └── NO  → Error path:
│   │       ├── EMPTY_INPUT / INVALID_TYPE → Fix your payload. No risk signal.
│   │       ├── FORBIDDEN_ROLE / DECISION_INJECTION → Fix your payload. Security alert if unexpected.
│   │       └── INTERNAL_ERROR → Do NOT act on score. Flag for review. Retry once.
└── NO (timeout / connection reset):
    └── Fail open: allow request with 'pending_review' flag. Do not block.
```
