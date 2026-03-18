# Error Propagation Proof

**Generated:** 2026-02-21 13:02:49  
**Verdict:** `ALL 9 PATHS VERIFIED`

## Invariants Checked Per Path

1. `errors` field is non-null
2. `safety_metadata.is_decision == False`
3. `risk_category` is `LOW | MEDIUM | HIGH`
4. `error_code` matches expected value
5. All required response fields are present

## Results

| Error Path | Expected Code | Status | Notes |
|---|---|---|---|
| EMPTY_INPUT | `EMPTY_INPUT` | **PASS** | — |
| INVALID_TYPE (int) | `INVALID_TYPE` | **PASS** | — |
| INVALID_TYPE (None) | `INVALID_TYPE` | **PASS** | — |
| INVALID_TYPE (list) | `INVALID_TYPE` | **PASS** | — |
| INVALID_TYPE (bool) | `INVALID_TYPE` | **PASS** | — |
| INVALID_TYPE (dict) | `INVALID_TYPE` | **PASS** | — |
| INTERNAL_ERROR | `INTERNAL_ERROR` | **PASS** | — |
| FORBIDDEN_ROLE | `FORBIDDEN_ROLE` | **PASS** | — |
| DECISION_INJECTION | `DECISION_INJECTION` | **PASS** | — |

## Conclusion

**ALL 9 PATHS VERIFIED** — every error code path in `app/engine.py` and `app/contract_enforcement.py`
preserves the non-authority invariant (`is_decision: false`) and returns a complete,
structurally safe response even under fault conditions.