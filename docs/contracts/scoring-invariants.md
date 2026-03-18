# Scoring Algebra & Invariants

## 1. Mathematical Model
 The risk score $S$ for a given input text $T$ is defined as the bounded sum of weighted keyword matches:

$$
S(T) = \min\left(1.0, \sum_{c \in C} \min(MAX\_CAT\_SCORE, \sum_{k \in K_c} w \cdot I(k, T))\right)
$$

Where:
- $C$ is the set of all risk categories.
- $K_c$ is the set of keywords for category $c$.
- $w$ is the keyword weight (constant `0.2`).
- $I(k, T)$ is the indicator function: $1$ if keyword $k$ is found in normalized $T$, else $0$.
- $MAX\_CAT\_SCORE$ is the per-category cap (constant `0.6`).

## 2. Invariants
### 2.1 Identity
$$ S(\text{""}) = 0.0 $$
An empty input string must always produce a score of 0.0 (or trigger an `EMPTY_INPUT` error).

### 2.2 Boundedness
$$ \forall T, 0.0 \le S(T) \le 1.0 $$
The final score is strictly clamped between 0.0 and 1.0 inclusive.

### 2.3 Idempotence (Statelessness)
$$ S(T)_t = S(T)_{t+\Delta} $$
The score for a fixed input $T$ must be identical regardless of when it is computed or what internal state (e.g., caches) exists.

### 2.4 Commutativity of Categories
The order in which categories are evaluated **must not** affect the final `total_score`. 
However, the `risk_category` derivation depends on `total_score`, so stability in `total_score` implies stability in `risk_category`.

## 3. Evaluation Order
To guarantee determinism in logging and side-effects (like the `trigger_reasons` list order), the engine enforces:
1. **Category Order**: Alphabetical by category key.
2. **Keyword Order**: Alphabetical (implied by deterministic iteration if not explicit, but explicit sort is safer).
