"""
Enforcement Ledger
==================
Deterministic, append-only replay ledger for enforcement decisions.

Records all inputs, the frozen DGIC snapshot, and the deterministic output.
Enables byte-identical replay verification of past decisions.
"""

import json
import logging
import threading
from dataclasses import dataclass
from typing import List, Dict, Any

from app.enforcement_schemas import EvaluateActionRequest, EvaluateActionResponse
from app.dgic_snapshot_consumer import DGICSnapshot, snapshot_to_dict

logger = logging.getLogger(__name__)


# ============================================================
# Ledger Dataclass
# ============================================================

@dataclass(frozen=True)
class EnforcementLedgerEntry:
    """
    A single, immutable enforcement decision record.
    """
    correlation_id: str
    action_id: str
    trace_hash: str
    timestamp_utc: str
    
    # Inputs
    request_payload: Dict[str, Any]
    dgic_snapshot: Dict[str, Any]
    
    # Outputs
    decision: str
    risk_score: float
    confidence: float
    failure_reason: str | None


# ============================================================
# In-Memory Ledger (Singleton)
# ============================================================

class _EnforcementLedger:
    def __init__(self):
        self._entries: List[EnforcementLedgerEntry] = []
        self._lock = threading.RLock()

    def record(
        self,
        correlation_id: str,
        timestamp_utc: str,
        request: EvaluateActionRequest,
        snapshot: DGICSnapshot,
        response: EvaluateActionResponse,
    ) -> EnforcementLedgerEntry:
        """
        Record a decision to the append-only ledger.
        """
        entry = EnforcementLedgerEntry(
            correlation_id=correlation_id,
            action_id=request.action_id,
            trace_hash=response.trace_hash,
            timestamp_utc=timestamp_utc,
            request_payload=request.model_dump(mode="json"),
            dgic_snapshot=snapshot_to_dict(snapshot),
            decision=response.enforcement_decision.value,
            risk_score=response.risk_score,
            confidence=response.confidence,
            failure_reason=response.failure_reason,
        )

        with self._lock:
            self._entries.append(entry)

        logger.debug(
            f"Ledger entry recorded | trace_hash={entry.trace_hash[:8]}...",
            extra={
                "event_type": "ledger_record",
                "action_id": entry.action_id,
                "decision": entry.decision,
            }
        )
        return entry

    def get_all(self) -> List[EnforcementLedgerEntry]:
        """Return a copy of all ledger entries."""
        with self._lock:
            return list(self._entries)

    def get_by_trace_hash(self, trace_hash: str) -> EnforcementLedgerEntry | None:
        """Look up a specific decision by its deterministic trace hash."""
        with self._lock:
            for entry in self._entries:
                if entry.trace_hash == trace_hash:
                    return entry
        return None
        
    def clear(self) -> None:
        """Clear the ledger (for testing only)."""
        with self._lock:
            self._entries.clear()


# Global Singleton Instance
ledger_instance = _EnforcementLedger()


# ============================================================
# Public API
# ============================================================

def record_decision(
    correlation_id: str,
    timestamp_utc: str,
    request: EvaluateActionRequest,
    snapshot: DGICSnapshot,
    response: EvaluateActionResponse,
) -> EnforcementLedgerEntry:
    return ledger_instance.record(correlation_id, timestamp_utc, request, snapshot, response)

def get_ledger_entries() -> List[EnforcementLedgerEntry]:
    return ledger_instance.get_all()

def get_ledger_entry(trace_hash: str) -> EnforcementLedgerEntry | None:
    return ledger_instance.get_by_trace_hash(trace_hash)

def clear_ledger() -> None:
    ledger_instance.clear()
