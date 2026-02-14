# Failure Tier Model

The Text Risk Scoring Service categorizes failures into three distinct tiers to ensure appropriate response and escalation.

| Tier | Category | Description | HTTP Code | Mitigation / Escalation |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Input Failure | User-provided data is invalid (e.g., empty text, wrong type). | 400 / 422 | Return structured error; no escalation required. |
| **Tier 2** | Resource / Usage | System limits exceeded or forbidden usage detected (e.g., forbidden role). | 429 / 403 | Throttling or rejection; log as "Operational Warning". |
| **Tier 3** | System Critical | Internal logic failure or contract violation (output side). | 500 | **Fail-Closed**: Return safe defaults; immediate escalation to engineering. |

## Graceful Degradation Rules
1. **Contract Violation Recovery**: If the engine produces an invalid score, the contract layer catches it and overrides the response to `risk_category: LOW` while logging a Tier 3 event.
2. **Unexpected Exception**: In case of a crash, the middleware returns a Tier 3 JSON error instead of a stack trace.
3. **Truncation**: Excessive input length is treated as a Tier 2 event—processing continues after truncation to maintain availability.
