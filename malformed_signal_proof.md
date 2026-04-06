# Malformed Signal Survival Proof
**Date:** 2026-04-06T11:13:52Z  
**Status:** ✅ CERTIFIED  
**Result:** 16/16 cases survived

---

## Coverage

All inputs below were injected into `validate_dgic_input()`, `validate_aggregation_inputs()`,
or `analyze_text()`. Every case must either:
- Raise the expected typed exception (structural guard working), OR
- Return a well-formed error response with valid `safety_metadata`

## Case Results

| Label | Description | Result | Note |
|---|---|---|---|
| `bad_version` | envelope version is not schema_v1 | **PASS** | DGICContractViolation: Unsupported envelope version: schema_ |
| `bad_lineage_hash` | lineage_hash is not 64 chars | **PASS** | DGICContractViolation: lineage_hash must be a 64-character S |
| `tampered_envelope_hash` | envelope hash does not match payload | **PASS** | DGICContractViolation: Cryptographic seal broken: envelope_h |
| `illegal_collapse` | ambiguous state with collapse_flag=True | **PASS** | DGICContractViolation: Illegal epistemic collapse: AMBIGUOUS |
| `corrupt_state_string` | epistemic_state is a raw string | **PASS** | DGICContractViolation: payload.epistemic_state must be an Ep |
| `corrupt_state_none` | epistemic_state is None | **PASS** | DGICContractViolation: payload.epistemic_state must be an Ep |
| `contradiction_flag_int` | contradiction_flag is int 1 | **PASS** | DGICContractViolation: payload.contradiction_flag must be a  |
| `plain_dict_instead_of_dgic` | Raw dict passed instead of DGICInput | **PASS** | DGICContractViolation: Input must be a DGICInput instance. |
| `none_instead_of_dgic` | None passed as DGICInput | **PASS** | DGICContractViolation: Input must be a DGICInput instance. |
| `empty_signal_list` | aggregate_signals([]) — empty list | **PASS** | AggregationContractViolation: EMPTY_SIGNALS: At least one si |
| `too_many_signals` | aggregate_signals with 33 signals | **PASS** | AggregationContractViolation: EXCESSIVE_SIGNALS: Maximum 32  |
| `signal_not_tuple` | Signal element is a plain string | **PASS** | AggregationContractViolation: INVALID_SIGNAL_ELEMENT: signal |
| `engine_none_input` | analyze_text(None) | **PASS** | error_code=INVALID_TYPE |
| `engine_integer_input` | analyze_text(42) | **PASS** | error_code=INVALID_TYPE |
| `engine_empty_after_strip` | analyze_text('   ') | **PASS** | error_code=EMPTY_INPUT |
| `engine_huge_payload` | analyze_text(500k chars) | **PASS** | Clean response with safe metadata |

---

## Guarantee

No malformed input caused:
- An unhandled exception propagating to the caller
- A response with `authority != "NONE"` or `is_decision != False`
- A silent no-op (every bad input is explicitly rejected or error-responded)

**Phase Tag:** `v-chaos-certified`
