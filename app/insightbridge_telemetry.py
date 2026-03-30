"""
InsightBridge Telemetry Emitter
================================
Emits structured telemetry events for each aggregated signal, making them
observable and auditable by InsightBridge telemetry pipelines and bucket logging.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - Telemetry events are informational only — they MUST NOT trigger actions.
  - All fields are deterministically derived — no ML, no probabilistic inference.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

from app.dgic_enforcement_bridge import DGICEnforcementEnvelope

logger = logging.getLogger(__name__)


# ============================================================
# Telemetry Event Dataclass
# ============================================================

@dataclass(frozen=True)
class InsightBridgeTelemetryEvent:
    """
    A structured telemetry event emitted for each aggregated signal.

    Fields:
        signal_id           : Deterministic hash of aggregation inputs.
        signal_source       : Always "multi_signal_aggregator".
        confidence          : Epistemic confidence from DGIC envelope.
        timestamp           : UTC ISO-8601 timestamp of emission.
        lineage_reference   : Signal lineage from DGIC envelope (full provenance).
        risk_score          : Aggregate risk score.
        signal_count        : Number of input signals aggregated.
        collapse_state      : STABLE | DEGRADED | COLLAPSED from DGIC envelope.
        execution_id        : Global unique execution ID trace.
    """
    execution_id: str
    signal_id: str
    signal_source: str
    confidence: float
    timestamp: str
    lineage_reference: str
    risk_score: float
    signal_count: int
    collapse_state: str


# ============================================================
# Signal ID Computation
# ============================================================

def _compute_telemetry_signal_id(envelope: DGICEnforcementEnvelope) -> str:
    """
    Compute a deterministic signal ID for the telemetry event.
    Derived from truth_boundary_reference + signal_lineage.
    """
    raw = f"{envelope.truth_boundary_reference}|{envelope.signal_lineage}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Telemetry Emission
# ============================================================

def emit_telemetry_event(execution_id: str, envelope: DGICEnforcementEnvelope) -> InsightBridgeTelemetryEvent:
    """
    Build and emit a structured telemetry event from a DGIC enforcement envelope.

    The event is emitted via structured JSON logging, making it consumable
    by InsightBridge telemetry pipelines and bucket logging infrastructure.

    Returns the event for programmatic use (e.g. API response enrichment).
    """
    signal_id = _compute_telemetry_signal_id(envelope)
    timestamp = datetime.now(timezone.utc).isoformat()

    event = InsightBridgeTelemetryEvent(
        execution_id=execution_id,
        signal_id=signal_id,
        signal_source="multi_signal_aggregator",
        confidence=envelope.epistemic_confidence,
        timestamp=timestamp,
        lineage_reference=envelope.signal_lineage,
        risk_score=envelope.aggregate_risk_score,
        signal_count=envelope.signal_count,
        collapse_state=envelope.collapse_state,
    )

    # Emit via structured logging for InsightBridge / bucket logging consumption
    logger.info(
        "InsightBridge telemetry event emitted",
        extra={
            "event_type": "insightbridge_telemetry",
            "telemetry": asdict(event),
        },
    )

    return event


def emit_telemetry_dict(execution_id: str, envelope: DGICEnforcementEnvelope) -> dict:
    """
    Convenience wrapper: emit telemetry and return as a plain dict
    for JSON serialisation in API responses.
    """
    event = emit_telemetry_event(execution_id, envelope)
    return asdict(event)
