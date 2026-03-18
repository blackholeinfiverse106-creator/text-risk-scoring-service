# Failure Tier Model

## Tier 1: Routine Failures (User Actionable)
- **Examples**: `EMPTY_INPUT`, `EXCESSIVE_LENGTH` (if rejected), `INVALID_TYPE`.
- **Response**: 4xx HTTP Error.
- **Alerting**: None (Client issue).

## Tier 2: Transient Failures (Retryable)
- **Examples**: `TIMEOUT` (if implemented), Network blips.
- **Response**: 503 Service Unavailable.
- **Alerting**: Warning if > 5% rate.

## Tier 3: Logic Corruption (Critical)
- **Examples**: `INVARIANT_VIOLATION`, `IMPOSSIBLE_STATE`.
- **Response**: **500 Internal Error** (Fail Closed).
- **Alerting**: **IMMEDIATE PAGER** (Indicates breach of determinism or core logic).

## Tier 4: Resource Exhaustion (System Critical)
- **Examples**: OOM, Disk Full.
- **Response**: Process Crash / Restart.
- **Alerting**: **IMMEDIATE PAGER**.
