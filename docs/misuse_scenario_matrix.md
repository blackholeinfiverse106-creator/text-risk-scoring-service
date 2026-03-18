# Misuse Scenario Matrix: Formal Contract Enforcement

This document maps specific misuse vectors to the system's deterministic response, verifying that the safety invariants are preserved.

## 1. Authority Usurpation
**Invariant Preserved**: *Non-Authority (The system never makes decisions).*

| Misuse Vector | Input Pattern | System Response | Error Code | Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Role Impersonation** | `context: {"role": "admin"}` | **REJECT** | `FORBIDDEN_ROLE` | Admin role implies executive power, which the engine lacks. |
| **Judge Impersonation** | `context: {"role": "judge"}` | **REJECT** | `FORBIDDEN_ROLE` | 'Judge' implies legal weight, which is prohibited. |
| **Action Injection** | `context: {"action": "ban"}` | **REJECT** | `DECISION_INJECTION` | Engine provides signals, not actions. |
| **Outcome Injection** | `context: {"outcome": "block"}` | **REJECT** | `DECISION_INJECTION` | Users cannot pre-determine the output state. |

## 2. Risk Fabrication
**Invariant Preserved**: *Integrity (The score reflects the text, nothing else).*

| Misuse Vector | Input Pattern | System Response | Error Code | Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Score Override** | `context: {"override_risk": 0.0}` | **REJECT** | `DECISION_INJECTION` | Attempts to bypass scoring logic. |
| **Safety Bypass** | `context: {"skip_safety": true}` | **REJECT** | `DECISION_INJECTION` | Safety checks are non-negotiable. |

## 3. Resource & Protocol Abuse
**Invariant Preserved**: *Availability (The system fail-closes to protect resources).*

| Misuse Vector | Input Pattern | System Response | Error Code | Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Empty Input** | `text: ""` | **Error (200 OK)** | `EMPTY_INPUT` | Meaningless input. |
| **Type Mismatch** | `text: 12345` | **Error (422)** | `VALIDATION_ERROR` | Schema violation (Pydantic). |
| **Giant Payload** | `text: "a" * 10000` | **TRUNCATE** | `N/A` (Processed) | 5000 char cap enforced silently to prevent DoS. |

## 4. Verification
These scenarios are structurally enforced by `app/contract_enforcement.py` and verified by:
- `tests/forbidden_usage_tests/test_context_rejection.py`
- `tests/forbidden_usage_tests/test_role_rejection.py`
- `tests/enforcement_abuse_tests/test_authority_misuse.py`
