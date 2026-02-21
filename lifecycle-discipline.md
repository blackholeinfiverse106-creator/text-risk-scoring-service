# Lifecycle Discipline

Defines the deterministic startup and shutdown semantics of the service.

## Startup

```
Process start
     │
     ├─ 1. Load RISK_KEYWORDS dict (constant, from source)
     ├─ 2. Compile regex patterns (lazy, on first analyze_text call)
     ├─ 3. Setup JSON logging (observability.setup_json_logging)
     └─ 4. Bind HTTP on port 8000 (uvicorn)

Ready state: all requests handled identically from first call.
```

**No warm-up required.** The first request is treated identically to the millionth.

**No state initialized at startup.** Engine carries no mutable globals between requests.

## Per-Request Lifecycle

```
Request received
     │
     ├─ validate_input_contract()   ← fail-open on contract violation
     ├─ analyze_text()              ← stateless, deterministic
     ├─ validate_output_contract()  ← fail-closed on output mutation
     └─ Return response
```

Each request is fully independent. No state is read from or written between requests.

## Shutdown

```
SIGTERM / SIGINT received
     │
     ├─ Uvicorn drains in-flight requests (graceful shutdown)
     ├─ No files to flush (logging to stdout only)
     ├─ No connections to close (no DB, no cache)
     └─ Process exits
```

**Shutdown is always clean.** No persistent state means no risk of inconsistent state on crash.

## Restart Guarantee

| Scenario | Effect on correctness |
|---|---|
| Immediate restart after crash | None — stateless |
| Restart mid-request | In-flight request lost; client retries safely |
| Rolling restart (2 instances) | No coordination needed — sessions are per-request |
| Cold start after 30 days | Identical output to day 1 (determinism proof) |
