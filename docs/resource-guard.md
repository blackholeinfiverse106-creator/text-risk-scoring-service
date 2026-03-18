# Resource Guard: Limits & Constraints

## 1. Physical Limits
| Metric | Limit | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Payload Size** | 5000 Characters | Hard truncation in `engine.py`. |
| **Response Latency** | < 200ms (P99) | Architectural design (O(n) complexity). |
| **Memory Footprint** | < 50MB per Request | Input size cap prevents unbounded allocation. |

## 2. Burst Protection
- **No Concurrency Limits Internal**: The engine is CPU-bound statless. Concurrency is limited ONLY by the host process (e.g. Uvicorn workers).
- **Worker count suggestion**: `2 * CPU_CORES + 1`.

## 3. Algorithmic Complexity
- **Time Complexity**: $O(N \times K)$ where $N$ is text length and $K$ is total keywords. Since both are bounded ($N=5000$, $K \approx 200$), runtime is effectively $O(1)$ constant time ceiling.
- **Space Complexity**: $O(N)$ for string storage.

## 4. DoS Vector Mitigation
- **ReDoS**: Protected by using simple `re.search` with fixed patterns and no back-references or nested quantifiers.
- **Hash Flooding**: Dictionary inputs prohibited; only simple strings accepted.
