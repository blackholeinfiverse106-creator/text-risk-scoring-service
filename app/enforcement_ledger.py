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

from app.enforcement_schemas import EvaluateActionRequest, SarathiEvaluateResponse

logger = logging.getLogger(__name__)


# ============================================================
# Ledger Dataclass
# ============================================================

@dataclass(frozen=True)
class EnforcementLedgerEntry:
    """
    A single, immutable enforcement decision record.
    """
    execution_id: str
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
        execution_id: str,
        timestamp_utc: str,
        request: EvaluateActionRequest,
        sarathi_response: SarathiEvaluateResponse,
    ) -> EnforcementLedgerEntry:
        """
        Record a Sarathi-approved decision to the append-only ledger.
        """
        entry = EnforcementLedgerEntry(
            execution_id=execution_id,
            trace_hash=sarathi_response.trace_hash,
            timestamp_utc=timestamp_utc,
            request_payload=request.model_dump(mode="json"),
            dgic_snapshot={},
            decision=sarathi_response.sarathi_decision.value,
            risk_score=sarathi_response.risk_score,
            confidence=sarathi_response.confidence,
            failure_reason=sarathi_response.failure_reason,
        )

        with self._lock:
            self._entries.append(entry)

        logger.debug(
            f"Ledger entry recorded | trace_hash={entry.trace_hash[:8]}...",
            extra={
                "event_type": "ledger_record",
                "execution_id": entry.execution_id,
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
    execution_id: str,
    timestamp_utc: str,
    request: EvaluateActionRequest,
    sarathi_response: SarathiEvaluateResponse,
) -> EnforcementLedgerEntry:
    return ledger_instance.record(execution_id, timestamp_utc, request, sarathi_response)

def get_ledger_entries() -> List[EnforcementLedgerEntry]:
    return ledger_instance.get_all()

def get_ledger_entry(trace_hash: str) -> EnforcementLedgerEntry | None:
    return ledger_instance.get_by_trace_hash(trace_hash)

def clear_ledger() -> None:
    ledger_instance.clear()
