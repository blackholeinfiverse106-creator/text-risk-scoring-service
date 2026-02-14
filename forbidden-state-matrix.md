# Forbidden State Matrix

This matrix enumerates all prohibited system states and their corresponding enforcement mechanisms.

| Forbidden State | Impact | Enforcement Level | Error/Mitigation |
| :--- | :--- | :--- | :--- |
| `risk_score` > 1.0 | Scoring overflow | Engine Logic | Clamped to 1.0 |
| `risk_score` < 0.0 | Scoring underflow | Engine Logic | Clamped to 0.0 |
| `authority` = `True` | Authority claim | Contract Layer | Rejected (ContractViolation) |
| `is_decision` = `True` | Decision claim | Contract Layer | Rejected (ContractViolation) |
| Empty Input Text | Undefined behavior | Engine Logic | Rejected (EMPTY_INPUT) |
| Illegal Encoding | System instability | Contract Layer | Rejected (INVALID_ENCODING) |
| Forbidden Roles | Misuse/Misalignment | Contract Layer | Rejected (FORBIDDEN_ROLE) |
| Decision Injection | Agency injection | Contract Layer | Rejected (DECISION_INJECTION) |
| Missing Schema Field | Contract breakage | Contract Layer | Rejected (MISSING_FIELD) |
| Extra Schema Field | Contract pollution | Contract Layer | Rejected (FORBIDDEN_FIELD) |

---

## Enforcement Hierarchy
1. **Pydantic Schema**: First line of defense for basic types and presence.
2. **Contract Layer**: Second line for semantic constraints (roles, authority, injected fields).
3. **Engine Logic**: Final line for score clamping and internal invariants.
