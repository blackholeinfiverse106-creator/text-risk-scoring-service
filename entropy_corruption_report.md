# Entropy Corruption Report
**Date:** 2026-06-03T07:54:25Z  
**Status:** ✅ CERTIFIED  
**Result:** 21/21 entropy injection cases handled correctly

---

## Test Methodology

Each entropy value was injected into a `DGICInput` with `epistemic_state=INFERRED`
and passed through `validate_dgic_input()`. Values expected to be rejected must raise
`DGICContractViolation`. Values in `[0.0, 1.0]` must be accepted and produce a
valid `confidence_multiplier = 1.0 - entropy * 0.4` within `[0.0, 1.0]`.

## Case Results

| Label | Entropy Value | Should Reject | Result | Note |
|---|---|---|---|---|
| `boundary_zero` | `0.0` | False | **PASS** | Accepted correctly. confidence_multiplier=1.0000 |
| `boundary_one` | `1.0` | False | **PASS** | Accepted correctly. confidence_multiplier=0.6000 |
| `boundary_mid` | `0.5` | False | **PASS** | Accepted correctly. confidence_multiplier=0.8000 |
| `boundary_near_zero` | `0.0001` | False | **PASS** | Accepted correctly. confidence_multiplier=1.0000 |
| `boundary_near_one` | `0.9999` | False | **PASS** | Accepted correctly. confidence_multiplier=0.6000 |
| `above_one` | `1.0001` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `well_above_one` | `999.0` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `below_zero` | `-0.0001` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `well_below_zero` | `-100.0` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `bool_true` | `True` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `bool_false` | `False` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `string_numeric` | `0.5` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `string_nan` | `nan` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `none_value` | `None` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `list_value` | `[0.5]` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `dict_value` | `{'e': 0.5}` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `float_nan` | `nan` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `float_inf` | `inf` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `float_neg_inf` | `-inf` | True | **PASS** | Correctly rejected: DGICContractViolation: payload.entropy_score  |
| `int_zero` | `0` | False | **PASS** | Accepted correctly. confidence_multiplier=1.0000 |
| `int_one` | `1` | False | **PASS** | Accepted correctly. confidence_multiplier=0.6000 |

---

## Entropy Acceptance Rule

```
accept_condition: isinstance(entropy, (int, float))
                  AND NOT isinstance(entropy, bool)
                  AND 0.0 <= entropy <= 1.0
```

All values outside this predicate are structurally rejected before any scoring occurs.

**Phase Tag:** `v-chaos-certified`
