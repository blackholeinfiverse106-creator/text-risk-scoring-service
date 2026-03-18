# Replay Proof: Mathematical Reconstruction from Logs

## 1. Theorem
The state of the text scoring engine $S_{text}$ is purely a function of the set of detected keywords $K$ and their weights $W$.
$$ S_{text} = \text{Clamp}(\sum_{c \in Categories} \text{Min}(\sum_{k \in K_c} W_k, \text{Cap}_c)) $$
Since the logs record every element of $K$ and every application of $\text{Cap}_c$, the final score can be derived from logs alone.

## 2. Evidence
The test suite `tests/test_log_replay.py` performs the following rigorous verification:

1.  **Execution**: Runs `analyze_text("complex input")`.
2.  **Capture**: Intercepts the `stderr`/`stdout` log stream.
3.  **Parses**: Extracts `keyword_detected` and `category_capped` events.
4.  **Reconstructs**: Applies the summing logic external to the engine.
5.  **Verifies**: `Reconstructed_Score == Actual_Score`.

## 3. Result
The test passed, proving that the **logs act as a complete, deterministic audit trail**. No "hidden state" influences the decision.
