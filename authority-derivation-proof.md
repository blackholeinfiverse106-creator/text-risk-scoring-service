# Authority Derivation Proof

**Claim:** The `EnforcementAdapter` cannot derive, claim, or accumulate authority from risk signals.

## Structural Barriers

| Attempt | Why It Fails |
|---|---|
| Set `action` to a command | `action` is a frozen dataclass field, default=`None` |
| Set `authority` to non-NONE | `authority` is a frozen dataclass field, default=`"NONE"` |
| Set `is_decision` to True | `is_decision` is a frozen dataclass field, default=`False` |
| Override via `__init__` | Fields have `init=False` — constructor ignores caller input |
| Call engine to write/block | Engine has no write path — `analyze_text` is read-only |
| Accumulate trust across calls | Adapter is stateless — no memory between `evaluate()` calls |

## Proof by Code

```python
from mock_enforcement_adapter import EnforcementAdapter
adapter = EnforcementAdapter()
rec = adapter.evaluate("kill attack bomb")

assert rec.action      is None    # no write path
assert rec.authority   == "NONE"  # no authority claimed
assert rec.is_decision is False   # not a decision

# Mutation attempt is silently ignored (dataclass init=False):
# EnforcementRecommendation(..., action="ban")  → action still None
```

## Conclusion

The adapter is a **signal consumer**, not an authority. Its outputs are routing hints for a human policy layer. No code path exists to produce an output with `action != None`.
