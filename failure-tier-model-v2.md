# Failure Tier Model v2

**Generated:** 2026-02-21  
**Supersedes:** `failure-tier-model.md`  
**Covers:** All known failure modes in `app/engine.py` and `app/contract_enforcement.py`

---

## Tier Classification Summary

| Tier | Name | Severity | Fail Mode | Alerting | SLA |
|------|------|----------|-----------|----------|-----|
| T1 | User Error | **INFO** | Fail-open | None | Response in <500ms |
| T2 | Policy Violation | **WARN** | Fail-open | Log only | Response in <500ms |
| T3 | Internal Limit | **WARN** | Fail-open (adjusted) | Log + monitor rate | Response in <500ms |
| T4 | Internal Error | **CRITICAL** | Fail-closed (safe struct.) | Immediate page if rate >1% | Response in <500ms |
| T5 | Resource Exhaustion | **CRITICAL** | Fail-closed (process exit) | Immediate page | N/A (process dead) |

---

## Tier T1 — User Error (INFO)

**Definition:** The caller submitted malformed or semantically invalid input. No system fault.

| Error Code | Trigger Condition | HTTP Status | Log Level | Event Type |
|---|---|---|---|---|
| `EMPTY_INPUT` | `text` normalizes to empty string | 200 | INFO | `error_response_generated` |
| `INVALID_TYPE` | `text` is not a string | 200 | INFO | `error_response_generated` |
| `INVALID_REQUEST` | Request body is not a JSON object | 422 | INFO | — |
| `MISSING_FIELD` | `text` field absent | 422 | INFO | — |

**Response invariants:**
- `errors != null` — always explicit
- `risk_score == 0.0` — safe default
- `safety_metadata.is_decision == false` — authority never claimed
- `risk_category == "LOW"` — never silent failure

**Alerting:** None. Client bugs do not indicate system degradation.

**Escalation:** Review client SDK / integration guide if rate exceeds 5%.

---

## Tier T2 — Policy Violation (WARN)

**Definition:** The caller attempted to use the service in a prohibited pattern. Input was structurally valid but semantically forbidden.

| Error Code | Trigger Condition | HTTP Status | Log Level | Event Type |
|---|---|---|---|---|
| `FORBIDDEN_ROLE` | `context.role` is a forbidden value | 200 | WARN | `error_response_generated` |
| `DECISION_INJECTION` | Forbidden decision field in `context` | 200 | WARN | `error_response_generated` |
| `FORBIDDEN_FIELD` | Extra top-level field in request | 422 | WARN | — |
| `INVALID_CONTEXT` | `context` is not a dict | 422 | WARN | — |

**Response invariants:** Same as T1 — safe structured error with `errors != null`.

**Alerting:** Log to audit trail. Page security team if rate exceeds 0.1% of requests (indicates misuse attempt pattern).

**Escalation:** Security review → check if `misuse-matrix-v2.md` covers the attack → update contract if not.

---

## Tier T3 — Internal Limit (WARN)

**Definition:** The engine encountered an internal operating boundary and self-corrected. The caller receives a valid (adjusted) response — no error field.

| Event | Trigger Condition | Adjustment | Log Level | Event Type |
|---|---|---|---|---|
| Category score cap | `category_score > 0.6` | Capped to 0.6 | WARNING | `category_capped` |
| Total score clamp | `total_score > 1.0` | Clamped to 1.0 | WARNING | `score_clamped` |
| Input truncation | `len(text) > 5000` | Truncated to 5000 | WARNING | `input_truncated` |
| Invariant correction | `score ≥ 0.7` but `category != HIGH` | Category forced | ERROR | `invariant_correction` |

**Response invariants:**
- `errors == null` — not an error from the caller's perspective
- `trigger_reasons` includes truncation notice when applicable
- Score is always in `[0.0, 1.0]`

**Alerting:** Monitor `category_capped` and `score_clamped` rates. Sustained elevation may indicate keyword dictionary drift.

**Escalation:** `invariant_correction` events are CRITICAL — indicates a logic regression. Page immediately.

---

## Tier T4 — Internal Error (CRITICAL)

**Definition:** An unexpected exception occurred inside `analyze_text()`. The outer `try/except` caught it and returned a safe structured error.

| Error Code | Trigger | HTTP Status | Log Level | Event Type |
|---|---|---|---|---|
| `INTERNAL_ERROR` | `Exception` caught in outer try/except | 200 | ERROR | `unhandled_exception` |

**Response invariants:**
- `errors.error_code == "INTERNAL_ERROR"`
- `risk_score == 0.0` — caller must not act on this
- `safety_metadata.is_decision == false`

**Alerting:** **Page immediately** if any `INTERNAL_ERROR` appears. This indicates a regression in parsing, regex, or scoring logic.

**SLA:** Engineer must acknowledge within 15 minutes. Root cause within 4 hours.

**Escalation:** Review recent keyword changes or dependency updates. Roll back if cause unclear.

---

## Tier T5 — Resource Exhaustion (CRITICAL)

**Definition:** The process cannot continue. Memory, disk, or OS-level limits exceeded.

| Failure | Trigger | Behaviour | Log Level |
|---|---|---|---|
| OOM (Out of Memory) | Process RSS exceeds container limit | Process killed by OOM killer | OS-level |
| Disk Full | Log write fails | Process may hang or crash | OS-level |
| CPU starvation | Thread pool exhausted | Response timeout | OS-level |

**Response:** No structured response possible — the process is dead or unresponsive.

**Alerting:** Infrastructure monitoring (Prometheus, CloudWatch, etc.) must detect process death. Page within 1 minute.

**SLA:** Auto-restart within 30s (container orchestration). Engineer acknowledge within 5 minutes.

**Escalation:** Resource boundary analysis (`resource-boundary-model.md`) defines safe operating limits. Scale horizontally if sustained.

---

## Error Code → Tier Mapping

| Error Code | Tier | Severity |
|---|---|---|
| `EMPTY_INPUT` | T1 | INFO |
| `INVALID_TYPE` | T1 | INFO |
| `INVALID_REQUEST` | T1 | INFO |
| `MISSING_FIELD` | T1 | INFO |
| `INVALID_ENCODING` | T1 | INFO |
| `FORBIDDEN_ROLE` | T2 | WARN |
| `DECISION_INJECTION` | T2 | WARN |
| `FORBIDDEN_FIELD` | T2 | WARN |
| `INVALID_CONTEXT` | T2 | WARN |
| `category_capped` (event) | T3 | WARN |
| `score_clamped` (event) | T3 | WARN |
| `input_truncated` (event) | T3 | WARN |
| `invariant_correction` (event) | T3→T4 | ERROR |
| `INTERNAL_ERROR` | T4 | CRITICAL |
| OOM / Disk / CPU | T5 | CRITICAL |
