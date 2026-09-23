# NIYANTRAN KENDRA — SOVEREIGN CORE INTEGRATION CONTRACT

**Document Type:** Canonical Integration Contract  
**Service:** Sovereign Core (Text Risk Scoring Service)  
**Owner:** Rajaryan Verma  
**Audience:** Niyantran Kendra Dashboard Team  
**Date:** 2026-09-23  
**Status:** `LIVE`

---

## 1. What Is Sovereign Core?

Sovereign Core is the BHIV text-risk evaluation runtime. It accepts proposed actions submitted by any registered BHIV/TANTRA participant, processes them through a multi-layer cryptographic governance pipeline (DGIC → Intelligence → RAJYA → Sarathi → Core → Bucket), and returns a deterministic verdict: `ALLOW`, `DENY`, or `ABSTAIN`.

Niyantran Kendra's role is **observational only** — it reads the execution state stream that Sovereign Core emits. It has no control authority over the enforcement pipeline.

---

## 2. Live Deployment Endpoint

```
Base URL: http://163.128.209.18:8000
```

> All endpoints listed below are relative to this base URL.

---

## 3. Endpoints for Niyantran Kendra Integration

### 3.1 Health Check
**Use this to check if Sovereign Core is alive and ready.**

```
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "bhiv-enforcement-gateway"
}
```

---

### 3.2 Live Execution Trace Stream
**This is the primary endpoint for the dashboard. Poll this to get the canonical state of the last 50 executions.**

```
GET /api/v1/niyantran/traces
```

**Authentication:** None required (internal trusted network)  
**Recommended polling interval:** every 3–5 seconds

**Response (200 OK) — Array of execution state objects:**
```json
[
  {
    "execution_id": "exec-a1b2c3d4e5f6",
    "execution_status": "COMPLETED",
    "dgic_state": "KNOWN",
    "risk_score": 0.15,
    "confidence": 0.98,
    "rajya_verdict": "EXECUTION_APPROVED",
    "sarathi_status": "VALID",
    "core_status": "ALLOW",
    "bucket_persistence": true,
    "failure_reason": null,
    "trace_hash": "baecfe00bacf96a1b1cfa52707db79d06354f77b7b0d2d0e78d928cd647fc566"
  },
  {
    "execution_id": "exec-9f8e7d6c5b4a",
    "execution_status": "FAILED",
    "dgic_state": "AMBIGUOUS",
    "risk_score": 0.0,
    "confidence": 0.0,
    "rajya_verdict": "PENDING",
    "sarathi_status": "PENDING",
    "core_status": "PENDING",
    "bucket_persistence": false,
    "failure_reason": "DGIC snapshot rejected: DGIC_SEAL_VERIFICATION_FAILED",
    "trace_hash": "abc123..."
  }
]
```

---

### 3.3 Field Reference — Full Schema

| Field | Type | Description |
|---|---|---|
| `execution_id` | `string` | Unique ID for this execution run. Format: `exec-<hex>` or `tantra-consumer-trace-<hex>` |
| `execution_status` | `string` | `IN_PROGRESS` \| `COMPLETED` \| `FAILED` \| `CRASHED` |
| `dgic_state` | `string` | DGIC epistemic assessment: `KNOWN` \| `INFERRED` \| `AMBIGUOUS` \| `UNKNOWN` |
| `risk_score` | `float` | Risk level from `0.0` (safe) to `1.0` (critical). Null if pipeline failed early. |
| `confidence` | `float` | Confidence of the evaluation `0.0`–`1.0` |
| `rajya_verdict` | `string` | `EXECUTION_APPROVED` \| `DENY` \| `PENDING` (if rejected before RAJYA step) |
| `sarathi_status` | `string` | `VALID` \| `PENDING` (if pipeline did not reach Sarathi minting) |
| `core_status` | `string` | `ALLOW` \| `DENY` \| `ABSTAIN` \| `PENDING` |
| `bucket_persistence` | `boolean` | `true` if the verdict was successfully ledgered to the Bucket (MongoDB on VM). `false` on failure or early termination. |
| `failure_reason` | `string \| null` | Structured error string on failure. `null` on `ALLOW`. |
| `trace_hash` | `string` | SHA-256 hash of the full execution state. Use for replay verification. |

---

### 3.4 Bucket Ledger Entries
**Query the immutable cryptographic ledger of all completed executions.**

```
GET /api/v1/bucket/entries
```

**Response:** Array of raw Bucket artifact objects stored in MongoDB.

---

### 3.5 Replay Verification
**Replay-verify a specific execution by its trace hash.**

```
POST /api/v1/bucket/replay/{trace_hash}
```

**Path Parameter:** `trace_hash` — the SHA-256 trace hash from a trace object  
**Response:** Replay result object with a `match: true/false` field.

---

### 3.6 Bulk Replay Verification
**Replay-verify ALL stored executions at once.**

```
POST /api/v1/bucket/replay_all
```

**Response:**
```json
{
  "total": 12,
  "passed": 11,
  "failed": 1,
  "results": [...]
}
```

---

## 4. Execution Status Lifecycle

```
IN_PROGRESS → COMPLETED (ALLOW / DENY / ABSTAIN)
           → FAILED     (DGIC seal broken, RAJYA reject, Sarathi block, etc.)
           → CRASHED    (unexpected internal error)
```

---

## 5. Verdict Semantics

| Verdict | Meaning |
|---|---|
| `ALLOW` | Action was fully approved through all governance layers. Core executed. Ledgered to Bucket. |
| `DENY` | Action was blocked by RAJYA governance, Sarathi gate, or DGIC. No execution occurred. |
| `ABSTAIN` | System could not confidently evaluate (e.g., DGIC reported UNKNOWN epistemic state). Caller must treat this conservatively as a block. |

---

## 6. Integrating Into Your Dashboard

Since Sovereign Core is not pushing events (it is a request-response service), Niyantran Kendra must **poll** the trace stream.

**Recommended integration pattern:**
```javascript
// Poll traces every 3 seconds
setInterval(async () => {
  const response = await fetch("http://163.128.209.18:8000/api/v1/niyantran/traces");
  const traces = await response.json();
  // Update your dashboard state with `traces`
}, 3000);
```

**Health watchdog:**
```javascript
// Check health every 10 seconds
setInterval(async () => {
  const response = await fetch("http://163.128.209.18:8000/health");
  const data = await response.json();
  setSystemStatus(data.status === "ok" ? "HEALTHY" : "DEGRADED");
}, 10000);
```

---

## 7. What Niyantran Kendra Should NOT Do

> [!CAUTION]
> Niyantran Kendra is strictly an **observational** control plane. The following actions are constitutionally prohibited:
> - Sending `POST /api/v1/sutradhara/invoke` to trigger executions (this is the responsibility of registered BHIV/TANTRA participants, not the dashboard).
> - Attempting to write to or replay the bucket ledger without an explicit governance token.
> - Storing enforcement verdicts in a secondary datastore that could create a parallel truth.

---

## 8. Contact

| Role | Owner |
|---|---|
| Sovereign Core Owner | Rajaryan Verma |
| Bucket Ledger VM | Shared VM (163.128.209.18) |
| Niyantran Kendra | Dashboard Team |
