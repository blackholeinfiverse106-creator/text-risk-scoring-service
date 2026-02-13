# Rule Resolution Matrix

This matrix defines the deterministic outcome when multiple risk factors are present.

## 1. Category Interactions

| Category A | Category B | Interaction Type | Resolution Rule |
| :--- | :--- | :--- | :--- |
| **Violence** | **Threats** | Synergistic | Score adds up (bounded by global max). Reasons list both. |
| **Self-Harm** | **Violence** | Distinct | Score adds up. Distinct intents. |
| **Fraud** | **Cybercrime** | Overlapping | Score adds up. Often appear together in "scam" contexts. |
| **Sexual** | **Abuse** | Aggravating | Score adds up. Harassment with sexual undertones is high risk. |

*Note: Currently, all categories are additive. There are no safe-listing or canceling interactions.*

## 2. Priority & Ordering
When generating `trigger_reasons`, the order is fixed by the category evaluation order (Alphabetical).

**Example Output Order:**
1. Abuse
2. Cybercrime
3. ...
4. Violence
5. Weapons

## 3. Confidence Penalties Matrix

| Condition | Penalty | Rationale |
| :--- | :--- | :--- |
| **0 Keywords** | N/A | Base confidence 1.0 (Low Risk, High Confidence) |
| **1 Keyword Only** | -0.3 | Single keyword might be noise/contextual. |
| **> 1 Category** | -0.2 | Multiple categories *can* imply complex context, slightly reducing certainty of specific classification (Legacy logic preserved). |
| **<= 2 Keywords Total** | -0.2 | Low data volume reduces detection confidence. |

*Note: Penalties are cumulative but Confidence is lower-bounded at 0.0.*
