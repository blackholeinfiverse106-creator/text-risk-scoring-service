# System Integration Guide

**Version:** v1.0  
**Date:** 2026-03-16  
**Audience:** DGIC (Pritesh Patra), Core Orchestration (Aakanksha), System Testing (Vinayak Tiwari), Backend Infrastructure (Akash)

---

## 1. API Endpoints

### `POST /api/v1/aggregate/unified`

**Primary endpoint** — accepts multiple typed signals, returns an InsightBridge-compatible payload enriched with DGIC envelope and telemetry.

**Request:**
```json
{
  "signals": [
    {
      "signal_id": "unique-string-id",
      "signal_type": "TEXT_RISK_SIGNAL",
      "base_risk_score": 0.7,
      "base_confidence_score": 0.9,
      "dgic_envelope": {
        "version": "schema_v1",
        "lineage_hash": "<64-char SHA-256>",
        "envelope_hash": "<64-char SHA-256>",
        "payload": {
          "epistemic_state": "KNOWN",
          "entropy_score": 0.0,
          "contradiction_flag": false
        },
        "collapse_flag": false
      }
    }
  ]
}
```

**Valid `signal_type` values:**
- `TEXT_RISK_SIGNAL`
- `BEHAVIOR_ANOMALY_SIGNAL`
- `POLICY_VIOLATION_SIGNAL`
- `EXTERNAL_DETECTOR_SIGNAL`

**Valid `epistemic_state` values:**
- `KNOWN` — full confidence, normal scoring
- `INFERRED` — confidence scaled by entropy
- `AMBIGUOUS` — risk capped at 0.69, confidence halved
- `UNKNOWN` — full abstention, score forced to 0.0

**Response:**
```json
{
  "signal_id": "<64-char SHA-256>",
  "source_type": "text_risk_scoring_service",
  "signal_timestamp": "2026-03-16T00:00:00+00:00",
  "lineage_reference": "<64-char SHA-256>",
  "aggregated_risk_score": 0.65,
  "epistemic_confidence": 0.85,
  "contradiction_flag": false,
  "abstention_flag": false,
  "decision": null,
  "authority": "NONE",
  "dgic_envelope": {
    "epistemic_confidence": 0.85,
    "signal_lineage": "<64-char SHA-256>",
    "collapse_state": "STABLE",
    "truth_boundary_reference": "<64-char SHA-256>"
  },
  "telemetry": {
    "signal_id": "<64-char SHA-256>",
    "signal_source": "multi_signal_aggregator",
    "confidence": 0.85,
    "timestamp": "2026-03-16T00:00:00+00:00",
    "lineage_reference": "<64-char SHA-256>",
    "risk_score": 0.65,
    "signal_count": 3,
    "collapse_state": "STABLE"
  }
}
```

---

## 2. Integration with DGIC (Pritesh)

The aggregated signal is wrapped inside a DGIC epistemic envelope via `dgic_enforcement_bridge.py`.

**Envelope fields:**

| Field | Type | Description |
|---|---|---|
| `epistemic_confidence` | `float [0.0, 1.0]` | Composite confidence after DGIC scaling |
| `signal_lineage` | `str (SHA-256)` | Full provenance: aggregation hash + all evidence hashes |
| `collapse_state` | `str` | `STABLE` / `DEGRADED` / `COLLAPSED` |
| `truth_boundary_reference` | `str (SHA-256)` | Immutable fingerprint of aggregation inputs |

**Truth-layer constraints respected:**
- `AMBIGUOUS` is never collapsed to a decision
- `collapse_flag` is never used to derive authority
- `evidence_hash` is passed through unmodified

---

## 3. Integration with Core Orchestration (Aakanksha)

Use `core_enforcement_adapter.py` for programmatic integration:

```python
from app.core_enforcement_adapter import process_for_core, payload_to_dict

signals_raw = [
    {
        "signal_id": "sig-001",
        "signal_type": "TEXT_RISK_SIGNAL",
        "base_risk_score": 0.7,
        "base_confidence_score": 0.9,
        "dgic_envelope": { ... }
    }
]

payload = process_for_core(signals_raw)
result = payload_to_dict(payload)
```

**Validation errors** raise `CoreAdapterValidationError` with structured `code` and `message`.

---

## 4. Integration with InsightBridge Telemetry

Telemetry events are emitted via structured JSON logging on every aggregation call:

```json
{
  "event_type": "insightbridge_telemetry",
  "telemetry": {
    "signal_id": "<SHA-256>",
    "signal_source": "multi_signal_aggregator",
    "confidence": 0.85,
    "timestamp": "2026-03-16T00:00:00+00:00",
    "lineage_reference": "<SHA-256>",
    "risk_score": 0.65,
    "signal_count": 3,
    "collapse_state": "STABLE"
  }
}
```

These are consumable by InsightBridge pipelines and bucket logging infrastructure.

---

## 5. Integration with Bucket Logging

All structured log events include `event_type` fields for filtering:

| Event Type | Module | Description |
|---|---|---|
| `unified_aggregation_start` | `signal_aggregator` | Aggregation initiated |
| `unified_signal_scored` | `signal_aggregator` | Per-signal scoring result |
| `unified_aggregation_complete` | `signal_aggregator` | Final aggregate computed |
| `dgic_envelope_created` | `dgic_enforcement_bridge` | DGIC envelope produced |
| `insightbridge_telemetry` | `insightbridge_telemetry` | Telemetry event emitted |
| `core_adapter_validate` | `core_enforcement_adapter` | Inbound validation started |
| `core_adapter_complete` | `core_enforcement_adapter` | Core payload ready |

---

## 6. Testing (Vinayak)

```bash
# Full test suite
python -m pytest tests/ -v

# Multi-signal scenarios
python -m pytest tests/test_signal_aggregation.py -v

# Conflicting signals
python -m pytest tests/test_conflicting_signals.py -v

# Deterministic replay (1,000 iterations × 7 scenarios)
python -m pytest tests/test_deterministic_signal_replay.py -v
```

**Deterministic replay** hashes all semantic output fields across 1,000 iterations per scenario and asserts zero divergence.

---

## 7. Error Codes

| Code | Source | Meaning |
|---|---|---|
| `EMPTY_SIGNALS` | Core adapter | No signals provided |
| `MISSING_SIGNAL_FIELDS` | Core adapter | Required fields missing |
| `INVALID_SIGNAL_TYPE` | Core adapter | Unknown signal type |
| `INVALID_RISK_SCORE_RANGE` | Core adapter | Score outside [0.0, 1.0] |
| `DGIC_CONTRACT_VIOLATION` | Core adapter | DGIC envelope integrity failure |
| `ALL_SIGNALS_ABSTAINED` | Aggregator | All UNKNOWN → no score produced |
| `UNIFIED_AGGREGATION_FAILED` | API | Unhandled aggregation error |
