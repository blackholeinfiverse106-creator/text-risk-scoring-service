# Integration Readiness: DEPLOYMENT GREEN

## 1. Dependency Map
The system interacts with the host environment ONLY via:
- **Input**: `analyze_text(str)` function call.
- **Output**: JSON Dictionary (Standard Schema).
- **Resources**: CPU cycles and RAM (See `resource-guard.md`).
- **Network**: **ZERO**. No external calls. No Database. No internet.

## 2. Red Lines (Strict Prohibitions)
1.  **Do NOT edit `RISK_KEYWORDS` at runtime.** The engine assumes immutability.
2.  **Do NOT try to import `engine.py` in a threaded context without understanding the GIL.** (Though we are thread-safe, CPU binding applies).
3.  **Do NOT use `risk_score` as a database key.** It is a float and subject to potential micro-variance in different floating point architectures (though we round to 2 decimals).

## 3. Versioning
This snapshot is **v2.1.0**. Any changes to scoring logic will bump `MINOR` version.
