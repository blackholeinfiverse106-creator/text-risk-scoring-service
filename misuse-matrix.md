# Misuse Detection Matrix

**Version**: 1.0.0  
**Status**: ACTIVE  
**Purpose**: Map specific misuse vectors to detection logic and verification tests.

---

## 1. Misuse Vector Matrix

| ID | Misuse Pattern | Attack Vector | Detection Mechanism | Test File | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M-01** | **Role Injection** | `role: "enforcement"` | Strict forbidden value check | `forbidden-usage-tests/test_role_rejection.py` | ✅ BLOCKED |
| **M-02** | **Decision Injection** | `action: "delete"` | Forbidden key check | `forbidden-usage-tests/test_role_rejection.py` | ✅ BLOCKED |
| **M-03** | **Authority Override** | `override_risk: true` | Forbidden key check | `forbidden-usage-tests/test_role_rejection.py` | ✅ BLOCKED |
| **M-04** | **Execution Claim** | `role: "executor"` | Strict forbidden value check | `forbidden-usage-tests/test_role_rejection.py` | ✅ BLOCKED |
| **M-05** | **Implicit Authority** | `perform_action: true` | Forbidden key check | `forbidden-usage-tests/test_role_rejection.py` | ✅ BLOCKED |

---

## 2. Detection Logic

### M-01 & M-04: Forbidden Roles
The system strictly prohibits specific role identifiers in the `context` object.
- **Forbidden Values**: `enforcement`, `decision_maker`, `judge`, `execution`, `admin`
- **Response**: `ContractViolation: FORBIDDEN_ROLE`

### M-02 & M-03 & M-05: Forbidden Fields
The system strictly prohibits fields that imply decision-making capability.
- **Forbidden Keys**: `action`, `decision`, `execute`, `perform_action`, `override_risk`
- **Response**: `ContractViolation: DECISION_INJECTION`

---

## 3. Verification

All misuse patterns are verified by `forbidden-usage-tests/test_role_rejection.py`.
Tests confirm that:
1.  Injection attempts raise specific error codes.
2.  Error messages explicitly state prohibition.
3.  System fails closed (rejects request completely).

---

**Misuse Matrix Status: SECURE ✓**
