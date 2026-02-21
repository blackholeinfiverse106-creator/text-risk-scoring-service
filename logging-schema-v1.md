# Logging Schema v1 — Frozen Specification

**Version:** v1  
**Status:** FROZEN — schema changes require a new version tag (`v2`)  
**Source:** `app/observability.py` (`JsonFormatter`) + `app/engine.py`  
**Date:** 2026-02-21

> [!IMPORTANT]
> This document is a **formal freeze** of the JSON log schema. Consumers (log parsers, SIEM rules, audit replays) may depend on this schema. Any change to field names, types, or the event catalog **MUST** create `logging-schema-v2.md`, not modify this file.

---

## 1. Base Record Shape

Every log line emitted by the service is a single JSON object on one line. The following fields are present on **every** log record.

| Field | Type | Example | Stability |
|---|---|---|---|
| `timestamp` | string (ISO 8601) | `"2026-02-21T07:34:12+0000"` | **STABLE** |
| `level` | string (enum) | `"INFO"`, `"WARNING"`, `"ERROR"` | **STABLE** |
| `message` | string | `"Request started"` | UNSTABLE (human-readable, may change) |
| `logger` | string | `"app.engine"` | **STABLE** |
| `path` | string | `"/app/engine.py"` | UNSTABLE (deployment-dependent) |
| `line` | integer | `161` | UNSTABLE (may shift with code changes) |

### Optional Extended Fields

| Field | Type | Present when | Stability |
|---|---|---|---|
| `correlation_id` | string | All `app.engine` log records | **STABLE** |
| `event_type` | string (enum) | Engine events (see §2) | **STABLE** |
| `details` | object | When `event_type` is set | Shape varies per event (see §2) |

---

## 2. Event Type Catalog

All `event_type` values are enumerated here. Log consumers MUST treat any unlisted value as **unknown** and not rely on its `details` shape.

### `analysis_start`
Emitted: Once per request, before any processing.  
Level: INFO

```json
{
  "event_type": "analysis_start",
  "correlation_id": "<id>",
  "details": null
}
```

---

### `input_received`
Emitted: After type-check passes, before normalization.  
Level: INFO

```json
{
  "event_type": "input_received",
  "correlation_id": "<id>",
  "details": {
    "raw_length": 142
  }
}
```

---

### `input_truncated`
Emitted: When `len(text) > MAX_TEXT_LENGTH` (5000).  
Level: WARNING

```json
{
  "event_type": "input_truncated",
  "correlation_id": "<id>",
  "details": {
    "original_length": 8200,
    "max_length": 5000
  }
}
```

---

### `keyword_detected`
Emitted: Once per matched keyword per request. May emit many times.  
Level: INFO

```json
{
  "event_type": "keyword_detected",
  "correlation_id": "<id>",
  "details": {
    "category": "violence",
    "keyword": "attack"
  }
}
```

---

### `category_capped`
Emitted: When a category accumulates more than `MAX_CATEGORY_SCORE` (0.6).  
Level: WARNING

```json
{
  "event_type": "category_capped",
  "correlation_id": "<id>",
  "details": {
    "category": "violence",
    "raw_score": 0.8,
    "cap": 0.6
  }
}
```

---

### `score_clamped`
Emitted: When `total_score > 1.0` before clamping.  
Level: WARNING

```json
{
  "event_type": "score_clamped",
  "correlation_id": "<id>",
  "details": {
    "raw_score": 1.4,
    "cap": 1.0
  }
}
```

---

### `invariant_correction`
Emitted: When a score/category mismatch is self-corrected.  
Level: ERROR — **treat as CRITICAL, page on-call**

```json
{
  "event_type": "invariant_correction",
  "correlation_id": "<id>",
  "details": {
    "score": 0.75,
    "category": "MEDIUM",
    "correction": "HIGH"
  }
}
```

---

### `analysis_complete`
Emitted: Once per request, after scoring is finalized.  
Level: INFO

```json
{
  "event_type": "analysis_complete",
  "correlation_id": "<id>",
  "details": {
    "score": 0.8,
    "confidence": 0.8,
    "category": "HIGH",
    "processing_time_ms": 2.3
  }
}
```

---

### `error_response_generated`
Emitted: When an error response is returned (any tier T1/T2/T4).  
Level: ERROR

```json
{
  "event_type": "error_response_generated",
  "correlation_id": "<id>",
  "details": {
    "code": "EMPTY_INPUT",
    "message": "Text is empty"
  }
}
```

---

### `unhandled_exception`
Emitted: When `except Exception` is triggered in the outer try/except.  
Level: ERROR — **CRITICAL, page on-call immediately**

```json
{
  "event_type": "unhandled_exception",
  "correlation_id": "<id>",
  "details": null
}
```
> Note: Python traceback is included in the log record via `exc_info=True`. The formatted traceback appears in the `message` field when using standard formatters or is accessible via the LogRecord's `exc_text` attribute.

---

## 3. Stability Contract

| Element | Stability Guarantee |
|---|---|
| Field names in base record | **STABLE** in v1 |
| `correlation_id` presence on all engine records | **STABLE** in v1 |
| `event_type` enum values listed above | **STABLE** in v1 |
| `details` field names within each event type | **STABLE** in v1 |
| `message` string content | UNSTABLE — do not parse programmatically |
| `path` and `line` | UNSTABLE — shift with code changes |

---

## 4. Log Replay Guarantee

Proven in `tests/test_log_replay.py`: the `risk_score` of any request can be **fully reconstructed** from the log stream using only these events:
1. Collect all `keyword_detected` events → accumulate `category_score`
2. Apply `category_capped` overrides
3. Sum all `category_score` values
4. Apply total score clamp if needed

This means the log stream constitutes a **full audit trail** sufficient to re-derive scoring decisions.

---

## 5. Consumer Notes

- **Do not filter on `message`** — use `event_type` for programmatic log processing
- **Correlation ID** is always a string; it may be `"UNKNOWN"` if not provided by the caller
- **Rate alerts:** Create alerts on:
  - `event_type: "invariant_correction"` — any occurrence
  - `event_type: "unhandled_exception"` — any occurrence
  - `event_type: "error_response_generated"` with `code: "INTERNAL_ERROR"` — any occurrence
