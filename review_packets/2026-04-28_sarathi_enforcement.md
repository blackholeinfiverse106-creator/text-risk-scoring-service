# Review Packet: Sarathi Pure Enforcement Token + Gate Layer
**Date:** 2026-04-28
**Component:** Sarathi (Layer 1) & Core (Layer 4)

---

## 1. Executive Summary

Sarathi has been stripped of all decision-making authority, risk scoring logic, and text analysis. It has been successfully converted into a **pure enforcement token gate**. 

In the new architecture:
- **Sarathi does NOT decide.**
- **Sarathi does NOT validate DGIC or compute ALLOW/DENY/ABSTAIN.**
- **Sarathi ONLY mints enforcement tokens upon explicit RAJYA approval.**
- **Core executes ONLY if the Sarathi token passes the strict `enforce_token` gate.**

---

## 2. Before vs After Architecture

### Before (Legacy Governance)
```
Sūtradhāra → Intelligence → [ Sarathi (Computes ALLOW/DENY/Risk) ] → Enforcement → RAJYA → Core (Validates RAJYA verdict)
```
*Issue:* Sarathi held intelligence and decision-making logic. Core was validating authority decisions instead of purely executing.

### After (Token-Gated Enforcement)
```
Sūtradhāra → Intelligence → [ Inline Decision Derivation ] → Enforcement → RAJYA → [ Sarathi (Token Minting) ] → Core (Blindly accepts enforce_token() gate)
```
*Fix:* Sūtradhāra derives the intelligence locally. RAJYA approves the payload. Sarathi mints the cryptographic token. Core purely executes upon `enforce_token()` returning `ALLOW`. 

---

## 3. The Enforcement Token Structure

The sole output of Sarathi is now the `SarathiEnforcementToken`. It is a fully deterministic, frozen dataclass designed to act as a cryptographic seal for execution.

```python
@dataclass(frozen=True)
class SarathiEnforcementToken:
    execution_id: str           # Pipeline canonical ID
    rajya_verdict: str          # Must be "EXECUTION_APPROVED"
    token_status: str           # "VALID"
    timestamp: str              # ISO-8601 deterministic timestamp
    signature_hash: str         # SHA-256(execution_id|rajya_verdict|timestamp)
```

Tokens are **only minted** if the RAJYA verdict is `"EXECUTION_APPROVED"`.

---

## 4. The Token Gate (`enforce_token`)

The single public gate for Core execution relies on a strict validation engine.

Checks enforced:
1. `execution_id` strictly matches the token's `execution_id`.
2. `rajya_verdict` == `"EXECUTION_APPROVED"`.
3. `token_status` == `"VALID"`.
4. `signature_hash` strictly matches the SHA-256 reconstruction.

**Failure Consequence:** Any failure triggers a `SarathiHardBlockError`, immediately defaulting Core to `block_execution()`.

---

## 5. Proof Logs (Clean ALLOW Path)

The following logs prove the pipeline execution hierarchy:

```text
INFO     app.rajya_validation_engine:rajya_validation_engine.py:160 RAJYA APPROVED | execution_id=prop-001
INFO     app.sutradhara_control_plane:sutradhara_control_plane.py:215 RAJYA DECISION | execution_id=prop-001 | result=EXECUTION_APPROVED | rejection=NONE
INFO     app.layer1_sarathi:layer1_sarathi.py:169 SARATHI TOKEN MINTED | execution_id=prop-001 | signature=203d1d076ad00d60...
INFO     app.layer1_sarathi:layer1_sarathi.py:277 SARATHI TOKEN VALID | execution_id=prop-001
INFO     app.layer1_sarathi:layer1_sarathi.py:357 SARATHI GATE ALLOW | execution_id=prop-001 | signature=203d1d076ad00d60...
INFO     app.sutradhara_control_plane:sutradhara_control_plane.py:281 CORE HANDOFF | execution_id=prop-001 | rajya=EXECUTION_APPROVED | token_status=VALID -> Core will execute
INFO     app.layer4_core:layer4_core.py:54 CORE ENTRY | execution_id=prop-001 | token_present=True
INFO     app.layer1_sarathi:layer1_sarathi.py:277 SARATHI TOKEN VALID | execution_id=prop-001
INFO     app.layer1_sarathi:layer1_sarathi.py:357 SARATHI GATE ALLOW | execution_id=prop-001 | signature=203d1d076ad00d60...
INFO     app.execution_controller:execution_controller.py:10 Core executing action: Generate daily report | execution_id=prop-001
INFO     app.layer4_core:layer4_core.py:116 CORE EXECUTED | execution_id=prop-001 | action='Generate daily report' | sarathi_gate=ALLOW
INFO     app.layer4_core:layer4_core.py:148 CORE EXIT | execution_id=prop-001 | decision=ALLOW | sarathi_gate=ALLOW
```

**Proof Verification:**
1. RAJYA explicitly approved.
2. Sarathi token was successfully minted *after* RAJYA approval.
3. Core entry acknowledges the token presence.
4. `SARATHI GATE ALLOW` explicitly fires right before `CORE EXECUTED`.
5. Core execution logic relies on `sarathi_gate=ALLOW`.

---

## 6. Verification Status
- **Test Suite:** 465 passed in ~42s.
- **Failures Tested:** Missing token, invalid hash, mismatching IDs, and missing RAJYA approval all result in a HARD BLOCK.
