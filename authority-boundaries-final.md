# Authority Boundaries: FINAL DECLARATION

## 1. Non-Authority Manifesto
The Text Risk Scoring Service explicitly disclaims all executive authority. It possesses:
- **No Agency**: It cannot ban, suspend, or charge users.
- **No Memory**: It does not track user history or "strikes".
- **No Judgment**: It detects *keywords*, not *intent*.

## 2. Structural Enforcements
This lack of authority is not just policy; it is code.
- **Input Rejection**: Requests containing "decision" fields are rejected (`test_context_rejection.py`).
- **Output Metadata**: Every response includes `is_decision: False` and `authority: "NONE"`.
- **Type Safety**: The API schema forbids returning actionable commands (`schemas.py`).

## 3. Sovereign Closure
The system is sealed. It provides **signals**, not **verdicts**. Any system attempting to treat it as a judge violates the integration contract.
