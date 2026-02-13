# Abuse Scenario Matrix

This document maps potential abuse vectors to the system's defensive behaviors.

| Abuse Vector | Scenario Description | Expected System Behavior | Verified By |
| :--- | :--- | :--- | :--- |
| **Flooding / DoS** | Sending extremely large text payloads (> 10MB). | **Hard Truncation**. F-03 ensures text is capped at `MAX_TEXT_LENGTH` (5000 chars). Analysis proceeds on truncated text. | `test_input_truncation` |
| **Keyword Stuffing** | Input containing thousands of risk keywords (e.g., "kill kill kill..."). | **Score Clamping**. F-04 and F-06 ensure scores and categories are mathematically bounded [0.0, 1.0]. | `test_invariant_score_bounds` |
| **Obfuscation (Zero-Width)** | Inserting zero-width spaces or control chars between letters (e.g., "H`\u200b`a`\u200b`t`\u200b`e"). | **Keyword Miss (Acceptable)**. The system guarantees *explicit* keyword matching only. It does NOT attempt to de-obfuscate, as that introduces non-determinism and performance risk. | `authority-boundaries.md` (Pillar II) |
| **Type Confusion** | Sending JSON objects, arrays, or numbers instead of strings. | **Fast Rejection**. F-02 ensures immediate `INVALID_TYPE` error. | `test_safety_metadata_on_invalid_type` |
| **Polyglot / Binary** | Sending compiled binary code or garbage bytes. | **Safe Processing**. Treated as string. No keywords matched (Low Risk) or `INVALID_TYPE` if decoding fails at framework level. | Normalization Logic |
| **Adversarial Noise** | "I like to k i l l time". | **Literal Interpretation**. Matches "time" (neutral) or misses "k i l l". System does not infer intent. | `authority-boundaries.md` |
| **Replay Attack** | Resending the same request 10,000 times. | **Idemptotency**. Result is identical every single time. | `stress_test_determinism.py` |

## Defensive Invariants
1.  **Complexity Bound**: Time complexity is $O(N \times K)$ where $N$ is text length (capped) and $K$ is number of keywords (constant). Processing time is strictly bounded.
2.  **Memory Bound**: No state is accumulated between requests. Memory usage is constant per request.
3.  **No Side Effects**: Abuse cannot corrupt data or affect other users.
