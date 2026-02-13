# Scoring Invariants & Mathematical Rules

## 1. Core Invariants
These properties must hold true for *every* execution of the scoring engine.

| Invariant ID | Description | Mathematical Expression |
| :--- | :--- | :--- |
| **INV-01** | **Bounded Score** | $0.0 \le S_{final} \le 1.0$ |
| **INV-02** | **Bounded Confidence** | $0.0 \le C_{final} \le 1.0$ |
| **INV-03** | **Monotonicity** | Adding a risk keyword *never* decreases the raw risk score (before clamping). $Score(T + k) \ge Score(T)$ |
| **INV-04** | **Category Consistency** | If $S_{final} \ge 0.7$, then $Category \in \{HIGH\}$. If $0.3 \le S_{final} < 0.7$, then $Category \in \{MEDIUM\}$. If $S_{final} < 0.3$, then $Category \in \{LOW\}$. |
| **INV-05** | **Determinism** | For any input $T$, $f(T)$ is constant across time and environments. |

## 2. Evaluation Order
To ensure determinism, rules must be evaluated in a strict, frozen order.

1.  **Input Normalization**: `strip()`, `lower()`.
2.  **Length Check**: Truncate to `MAX_TEXT_LENGTH` (5000).
3.  **Keyword Matching**: Iterate through categories in **alphabetical order** of their keys:
    1.  `abuse`
    2.  `cybercrime`
    3.  `drugs`
    4.  `extremism`
    5.  `fraud`
    6.  `self_harm`
    7.  `sexual`
    8.  `threats`
    9.  `violence`
    10. `weapons`
4.  **Score Accumulation**:
    - For each category, sum `KEYWORD_WEIGHT` (0.2) per unique detected keyword.
    - Clamp category sub-score to `MAX_CATEGORY_SCORE` (0.6).
    - Add category sub-score to `Total Score`.
5.  **Global Clamping**: Clamp `Total Score` to 1.0.
6.  **Risk Categorization**: Map `Total Score` to Category (Low/Medium/High).
7.  **Confidence Calculation**: Apply penalties.
8.  **Output Formatting**: Round floats to 2 decimal places.

## 3. Forbidden States
The system must never produce an output in these states.

- **State F-1**: `risk_score` > 1.0 or < 0.0.
- **State F-2**: `risk_category` matches "HIGH" but `risk_score` < 0.7.
- **State F-3**: `risk_category` matches "LOW" but `risk_score` >= 0.3.
- **State F-4**: `trigger_reasons` is empty when `risk_score` > 0.0.

## 4. Arithmetic Precision
- All floating point operations use standard IEEE 754 double precision (Python `float`).
- **Rounding**: Final output scores are rounded to 2 decimal places using "Round Half Up" logic implicitly by Python's `round()`, but for strict determinism we accept standard default rounding behavior as long as it's consistent.
