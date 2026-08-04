# Rajya Governance & Enforcement Validation Engine API

This document provides the integration specifications for calling the standalone **Rajya Validation Engine Endpoint** hosted on our Sovereign Core runtime.

---

## 📍 Endpoint Overview

* **Base URL:** `https://text-risk-scoring-service.onrender.com`
* **Route:** `/api/v1/rajya/validate`
* **HTTP Method:** `POST`
* **Content-Type:** `application/json`

### Purpose & Authority Boundary
The **Rajya Validation Engine** provides the mandatory governance check prior to executing any action in an AI agent pipeline or system. 
It performs a **Strict Consensus & Integrity Verification**:
1. **Identity Integrity Protection:** Confirms that the execution request ID has not been tampered with across upstream agent layers.
2. **Double-Lock Authority Assurance:** Ensures both the cryptographic authorization token (Sarathi) and the structural risk enforcement gate have explicitly evaluated to **`ALLOW`**.

If any layer expresses epistemic doubt (`ABSTAIN`), threat risk (`DENY`), or cryptographic inconsistency, Rajya immediately revokes execution authority.

---

## 📥 Request Contract (Input Payload)

Send a JSON payload adhering to the `RajyaValidationRequest` schema:

| Field Name | Type | Required? | Description |
| :--- | :--- | :--- | :--- |
| `execution_id` | `string` | **Yes** | Canonical unique identifier for the execution pipeline attempt (e.g., UUID). |
| `sarathi_decision` | `string` | **Yes** | Final authorization verdict derived by Sarathi Layer 1 (`"ALLOW"`, `"DENY"`, or `"ABSTAIN"`). |
| `sarathi_execution_id` | `string` | **Yes** | The execution ID bound inside the Sarathi authorization token. Must precisely match `execution_id`. |
| `enforcement_verdict` | `object` | **Yes** | Structured enforcement dictionary returned by Layer 4 containing at minimum an `"enforcement_decision"` field (`"ALLOW"`, `"DENY"`, or `"ABSTAIN"`). |

### Example Approved Input Contract:
```json
{
  "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
  "sarathi_decision": "ALLOW",
  "sarathi_execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
  "enforcement_verdict": {
    "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
    "enforcement_decision": "ALLOW",
    "trace_hash": "a75eace926f5277e27b8da32a22c56436ed80086f2f221627a3ef74a5adde68c",
    "risk_score": 0.15,
    "confidence": 0.95
  }
}
```

---

## 📤 Response Contract (Output Verdicts)

The service will process the request deterministically and always respond with `HTTP 200 OK` containing the explicit governance status.

### 1. Success Response (Execution Approved)
Returned when all four strict governance identity and safety invariants pass:
```json
{
  "status": "EXECUTION_APPROVED"
}
```

### 2. Rejection Response (Execution Forbidden)
Returned whenever an authority is missing, an ID mismatch is detected, or any upstream decision evaluated to anything other than `"ALLOW"`:
```json
{
  "status": "REJECT",
  "rejection_code": "RAJYA_SARATHI_NOT_ALLOW",
  "rejection_reason": "Sarathi decision is 'DENY', not ALLOW. Execution not authorized."
}
```

---

## 🚨 Table of Rejection Codes

When adapting the response into your service error handlers, reference these deterministic rejection codes:

| Rejection Code | Trigger Condition | Recommended Action |
| :--- | :--- | :--- |
| `RAJYA_SARATHI_AUTHORITY_MISSING` | `sarathi_decision` was omitted or passed as `null`. | Ensure your Sarathi evaluation step executed before invoking Rajya. |
| `RAJYA_ENFORCEMENT_AUTHORITY_MISSING` | `enforcement_verdict` was omitted or invalid. | Ensure your Layer 4 enforcement gate object is passed inside the request. |
| `RAJYA_EXECUTION_ID_MISMATCH` | `sarathi_execution_id` != `execution_id`. | Abort immediately! Indicates potential identity tampering or crossed session contexts. |
| `RAJYA_SARATHI_NOT_ALLOW` | `sarathi_decision` was `"DENY"` or `"ABSTAIN"`. | Halt execution; action blocked due to policy breach or epistemic doubt. |
| `RAJYA_ENFORCEMENT_NOT_ALLOW` | `enforcement_verdict.enforcement_decision` was not `"ALLOW"`. | Halt execution; action blocked by downstream gate enforcement rules. |

---

## 💻 Code Integration Samples for Teammates

### 1. Python (`requests`)
```python
import requests

RAJYA_VALIDATE_URL = "https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate"

payload = {
    "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
    "sarathi_decision": "ALLOW",
    "sarathi_execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
    "enforcement_verdict": {
        "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
        "enforcement_decision": "ALLOW",
        "trace_hash": "a75eace926f5277e27b8da32a22c56436ed80086f2f221627a3ef74a5adde68c"
    }
}

response = requests.post(RAJYA_VALIDATE_URL, json=payload, timeout=10)
result = response.json()

if result.get("status") == "EXECUTION_APPROVED":
    print("✅ Governance Cleared. Proceeding with core action...")
else:
    print(f"❌ Governance Rejection: {result.get('rejection_code')} — {result.get('rejection_reason')}")
```

### 2. JavaScript / TypeScript (`fetch` API)
```javascript
const url = "https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate";

const payload = {
  execution_id: "c8f2b77a-2454-4712-baea-35b8696d744f",
  sarathi_decision: "ALLOW",
  sarathi_execution_id: "c8f2b77a-2454-4712-baea-35b8696d744f",
  enforcement_verdict: {
    execution_id: "c8f2b77a-2454-4712-baea-35b8696d744f",
    enforcement_decision: "ALLOW",
    trace_hash: "a75eace926f5277e27b8da32a22c56436ed80086f2f221627a3ef74a5adde68c"
  }
};

async function validateRajya() {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  
  const data = await res.json();
  if (data.status === "EXECUTION_APPROVED") {
    console.log("✅ Execution Approved!");
  } else {
    console.error(`❌ Blocked (${data.rejection_code}): ${data.rejection_reason}`);
  }
}

validateRajya();
```

### 3. cURL (Terminal Testing)
```bash
curl -X POST https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate \
     -H "Content-Type: application/json" \
     -d '{
           "execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
           "sarathi_decision": "ALLOW",
           "sarathi_execution_id": "c8f2b77a-2454-4712-baea-35b8696d744f",
           "enforcement_verdict": {
             "enforcement_decision": "ALLOW",
             "trace_hash": "a75eace926f5277e27b8da32a22c56436ed80086f2f221627a3ef74a5adde68c"
           }
         }'
```
