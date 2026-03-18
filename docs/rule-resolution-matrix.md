# Rule Resolution Matrix

## 1. Category Precedence
When multiple categories are detected, the system must deterministically decide the "Primary Category" behavior if a tie-breaker is needed, or simply for informative purposes.
The hierarchy is strictly defined as follows (Highest Priority First):

1. **Child Safety** (sexual_minor, self_harm)
2. **Violence** (violence, weapons, threats)
3. **Extremism** (extremism, cybercrime)
4. **Illegal** (drugs, fraud)
5. **Harassment** (abuse, sexual)

## 2. Conflict Resolution Table

| Matched Categories | Resolved "Primary" (Reported in Log) | Rationale |
| :--- | :--- | :--- |
| {Self_Harm, Violence} | Self_Harm | Immediate life safety takes precedence. |
| {Terrorism, Violence} | Terrorism | Specific intent > General action. |
| {Fraud, Abuse} | Fraud | Financial risk usually implies systemic actor. |
| {Drugs, Sexual} | Drugs | Illegal goods > Content policy (generally). |

*Note: The current engine sums ALL scores. This matrix specifically governs the `trigger_reasons` ordering or any future "Primary Label" field.*

## 3. Illegal Path Rejection
The engine explicitly rejects the following semantic combinations as "Illegal/Impossible" and flags them as anomalies:
- `Score > 0.0` but `reasons` is empty.
- `Score == 0.0` but `risk_category` is `HIGH`.
- `processed_length` != actual length of normalized text.

## 4. Resolution Function
$$
Resolved(C_{matched}) = \text{argmax}_{c \in C_{matched}} (Priority(c))
$$
Where $Priority(c)$ is the integer rank defined in Section 1.
