# Escalation Simulation Report

**Generated:** 2026-02-21 12:52:10  
**Verdict:** `ALL BLOCKED`  
**Total attempts:** 47  
**Wall time:** 0.000s

## Summary by Category

| Category | Attempts | Blocked | Succeeded |
|----------|----------|---------|-----------|
| role_attack | 14 | 14 | 0 |
| field_injection | 15 | 15 | 0 |
| schema_smuggling | 10 | 10 | 0 |
| output_mutation | 8 | 8 | 0 |

## Conclusion

**ALL BLOCKED** — 47/47 escalation attempts were blocked by the contract layer.

### Enforcement Mechanism
All blocks are enforced by `app/contract_enforcement.py` — the same module
used in production. No mocking or test-only bypass paths exist.