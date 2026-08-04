# Core Execution (Layer 4) API Integration Guide

This document outlines the strict API contract and integration requirements for the live **Core Execution Service** owned by your teammate. It defines exactly what Core does in the Sovereign Core pipeline, what details to request from the owner, and the exact payloads required for integration.

---

## 🏗️ What Core Does in Our Project

In our architecture, **Core (Layer 4)** is the absolute "Final Dumb Executor". 
It has a very strict authority boundary:
* **Zero Intelligence:** It does not analyze risk, score threat signals, or read DGIC context.
* **Zero Governance:** It does not enforce security policies or check user permissions (Rajya already did that).
* **Cryptographic Verification Only:** Core’s sole responsibility is to inspect the **Sarathi Enforcement Token** attached to the request. It mathematically verifies the cryptographic signature (`signature_hash`).
* **Execution Handoff:** If the token signature is valid and authentic, Core proceeds with physically executing the `proposed_action`. If the signature is missing or tampered with, Core executes a `SarathiHardBlockError` and drops the payload immediately.

---

## 📥 Questions to Ask the Core Service Owner

To connect our `text-risk-scoring-service` to their live Core engine, you must request the following details from them:
1. **Live Endpoint URL:** What is the exact public `POST` URL for the live Core execution engine? (e.g., `https://core-executor-service.onrender.com/api/v1/core/execute`)
2. **Authentication / Headers:** Do we need to pass any custom headers (like API keys or an `X-Sutradhara-Token`) to reach the endpoint?
3. **Payload Confirmation:** Please review the Input Request Contract below. Are there any extra fields your endpoint expects, or does this perfectly match your ingestion schema?

---

## 📝 The API Contracts

### 1. Input Request Contract (What we POST to Core)
When Sarathi mints a valid token, we package it along with the action and POST it to the Core owner's endpoint.

**Expected HTTP Method:** `POST`

**Sample JSON Payload:**
```json
{
  "execution_id": "444c4114-8d77-425c-b1cf-d9de7d6260c3",
  "proposed_action": "Transfer highly classified structural data to Sector 4",
  "request_payload": {
    "actor": "marine-intelligence-bot",
    "target_destination": "Sector 4",
    "priority": "HIGH"
  },
  "enforcement_token": {
    "execution_id": "444c4114-8d77-425c-b1cf-d9de7d6260c3",
    "rajya_verdict": "EXECUTION_APPROVED",
    "timestamp": "2026-07-28T09:58:00.123456+00:00",
    "token_status": "ACTIVE",
    "signature_hash": "a6e7c41fbed1aafbc64fe843f2f1e4b934cb0118bed23ad0d1d98beb6e73285e"
  }
}
```
*Note: The `enforcement_token` is the critical cryptographic key. If the `signature_hash` inside it is invalid or tampered with, the Core owner's service must reject the execution.*

---

### 2. Output Response Contract (What we expect back from Core)
After Core verifies the token and attempts the execution, it should return a standardized status response back to our orchestrator.

#### ✅ Success Response (`200 OK`)
*Returned if the token signature matched and the physical action was executed successfully.*
```json
{
  "execution_id": "444c4114-8d77-425c-b1cf-d9de7d6260c3",
  "enforcement_decision": "ALLOW",
  "status": "EXECUTION_COMPLETED",
  "failure_reason": null
}
```

#### ❌ Rejection / Blocked Response (`403 Forbidden` or `400 Bad Request`)
*Returned if the cryptographic token is invalid, expired, or tampered with.*
```json
{
  "execution_id": "444c4114-8d77-425c-b1cf-d9de7d6260c3",
  "enforcement_decision": "DENY",
  "status": "EXECUTION_BLOCKED",
  "failure_reason": "Sarathi gate HARD BLOCK: TOKEN_INVALID — Enforcement token signature verification failed."
}
```
