# System Guarantees (v3)

## 1. Safety Invariants
1.  **Bounded Output**: The risk score $S$ is strictly $0.0 \le S \le 1.0$.
2.  **Type Safety**: The output always adheres to `OutputSchema`. No `None` returns.
3.  **Fail-Closed**: If `Exception` occurs, `Score=0.0`/`Error=NonNull`. (Clarification: We return Error object, not false safe score).

## 2. Statelessness
1.  **Pure Function**: `analyze_text(Input)` depends ONLY on `Input` and `Constants`.
2.  **Immutability**: The `RISK_KEYWORDS` dictionary is never mutated at runtime.

## 3. Performance
1.  **Complexity**: $O(N)$ where $N$ is input length.
2.  **Memory**: $O(N)$ (Bounded by 5000 char limit).
3.  **Blocking**: CPU-bound, non-blocking (no I/O in the engine).
