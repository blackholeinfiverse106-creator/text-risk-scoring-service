# Resource Guard: CPU, Memory & Time Constraints

## 1. Technical Boundary
The Text Risk Scoring Service is designed to be resource-efficient and predictable. It enforces the following constraints to prevent resource abuse:

| Constraint | Value | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Max Text Length** | 5000 chars | Truncation in `analyze_text` |
| **Time Complexity** | O(n) | Single-pass keyword matching |
| **Memory Bound** | Bounded by input size | No large intermediate state |
| **Concurrency** | Stateless | Vertically scalable |

## 2. Resource Abuse Mitigation
### Truncation Strategy
Inputs exceeding 5000 characters are not rejected but **truncated**. 
- A warning is logged at the infrastructure level.
- The `processed_length` in the response reflects the truncated size.
- `trigger_reasons` includes a notice: `"Input text was truncated to safe maximum length"`.

### Algorithmic Safety
The engine uses optimized regular expressions with word boundary anchors (`\b`). The pattern matching time scales linearly with text length, preventing "ReDoS" (Regular Expression Denial of Service) for the static keyword set.

## 3. Deployment Recommendations
To ensure system stability, the service should be deployed with the following limits:
- **CPU**: 0.5 Core (minimum)
- **Memory**: 256MB RAM
- **Timeout**: 500ms per request (aggressive)
