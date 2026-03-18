# Semantic Hash Specification

**Version:** 1.0  
**Date:** 2026-02-21  
**Author:** Determinism Proof System

---

## 1. Purpose

This document formally defines the **Semantic Hash Contract** for the Text Risk Scoring Service.

A _semantic hash_ is a stable, reproducible fingerprint of the **decision-relevant** output of `analyze_text()`. It is the foundation of the replay harness and cross-process determinism proof.

---

## 2. Included Fields

The following fields from the `analyze_text()` response are **included** in the semantic hash:

| Field | Type | Rationale |
|---|---|---|
| `risk_score` | `float` | Core scoring output. Must be deterministic. |
| `confidence_score` | `float` | Derived from keyword count — deterministic. |
| `risk_category` | `str` | Threshold-derived from `risk_score` — deterministic. |
| `trigger_reasons` | `list[str]` | Keyword match log — deterministic. **Sorted** before hashing. |
| `processed_length` | `int` | Length of normalized, truncated input — deterministic. |

For **error responses**, only these fields are hashed:

| Field | Rationale |
|---|---|
| `risk_score` | Always `0.0` on error |
| `risk_category` | Always `"LOW"` on error |
| `errors.error_code` | Deterministic error code (e.g. `EMPTY_INPUT`, `INVALID_TYPE`) |

---

## 3. Excluded Fields

The following fields are **explicitly excluded** from the semantic hash:

| Field | Reason for Exclusion |
|---|---|
| `correlation_id` | UUID — non-deterministic by design (caller-supplied or generated) |
| `safety_metadata` | Constant values (`is_decision: False`, `authority: "NONE"`) — adds no signal |
| `errors.message` | Free-text human message — may vary across versions without semantic change |
| Log timestamps | System time — non-deterministic |

---

## 4. Canonical Implementation

```python
import hashlib
import json
from typing import Any, Dict

SEMANTIC_FIELDS = [
    "risk_score",
    "confidence_score",
    "risk_category",
    "trigger_reasons",
    "processed_length",
]

def get_semantic_hash(response: Dict[str, Any]) -> str:
    """
    Compute a stable SHA-256 hash over the semantic fields of an
    analyze_text() response.
    
    - For success responses: hashes SEMANTIC_FIELDS.
    - For error responses: hashes risk_score, risk_category, error_code.
    - trigger_reasons is sorted before hashing (list order is irrelevant).
    """
    if response.get("errors"):
        core = {
            "risk_score":    response["risk_score"],
            "risk_category": response["risk_category"],
            "error_code":    response["errors"].get("error_code"),
        }
    else:
        core = {field: response[field] for field in SEMANTIC_FIELDS}
        core["trigger_reasons"] = sorted(core["trigger_reasons"])

    serialized = json.dumps(core, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()
```

---

## 5. Invariant Statement

> **Given the same input string `t`, `get_semantic_hash(analyze_text(t))` SHALL return
> the identical hexdigest on every invocation, in every process, across all
> threads — as proven by `replay_harness.py` and `cross_process_test.py`.**

---

## 6. Change Policy

A change to the semantic hash spec (i.e. adding/removing a field) constitutes a **breaking contract change** and must be:

1. Documented in `CHANGELOG.md`.
2. Re-verified via `replay_harness.py`.
3. Signed off in `system-guarantees-v2.md`.
