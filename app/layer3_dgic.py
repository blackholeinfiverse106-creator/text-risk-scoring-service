from __future__ import annotations
"""
Sovereign Layer File: app/layer3_dgic.py
"""


# ==================================================
# Source: app/dgic_adapter.py
# ==================================================

"""
DGIC Integration Adapter
========================
Consumes structured epistemic outputs from the Deterministic Graph Intelligence Core (DGIC)
and maps them deterministically to scoring behaviour modifiers.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority from DGIC fields.
  - This module NEVER collapses Ambiguous epistemic state into a binary decision.
  - safety_metadata.is_decision remains False under ALL epistemic states.
  - safety_metadata.authority remains "NONE" under ALL epistemic states.
  - All transformations are purely structural — no ML, no probabilistic inference.
"""


import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

# Confidence scaling: how much entropy reduces confidence under INFERRED state.
# confidence_multiplier = 1.0 - entropy_score * INFERRED_ENTROPY_SCALING_FACTOR
INFERRED_ENTROPY_SCALING_FACTOR = 0.4

# Under AMBIGUOUS state the risk score is capped below the HIGH threshold.
# 0.69 keeps the score in MEDIUM range at worst — the system cannot escalate
# an ambiguous signal to HIGH on its own.
AMBIGUOUS_RISK_CEILING = 0.69

# Confidence multiplier applied when state is AMBIGUOUS — signals are contradictory.
AMBIGUOUS_CONFIDENCE_MULTIPLIER = 0.5

# Abstention ceiling: UNKNOWN state forces risk_score to 0.0.
UNKNOWN_RISK_CEILING = 0.0

# Valid entropy score range
ENTROPY_MIN = 0.0
ENTROPY_MAX = 1.0


# ============================================================
# Epistemic State Enum
# ============================================================

class EpistemicState(str, Enum):
    """
    The four epistemic states emitted by DGIC.

    KNOWN     — The intelligence core has high-confidence, grounded evidence.
    INFERRED  — Evidence exists but confidence is reduced by entropy.
    AMBIGUOUS — Contradictory or insufficient signals; state must NOT be collapsed.
    UNKNOWN   — No epistemic grounding available; system must abstain.
    """
    KNOWN     = "KNOWN"
    INFERRED  = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN   = "UNKNOWN"


# ============================================================
# Input / Output Dataclasses
# ============================================================

@dataclass(frozen=True)
class DGICPayload:
    epistemic_state: EpistemicState
    entropy_score: float
    contradiction_flag: bool

@dataclass(frozen=True)
class DGICInput:
    """The strict schema_v1 epistemic envelope from DGIC."""
    version: str
    lineage_hash: str
    envelope_hash: str
    payload: DGICPayload
    
    # Internal flags
    collapse_flag: bool = False
    
    @property
    def evidence_hash(self) -> str:
        # Legacy property alias for previous pipeline steps
        return self.lineage_hash

@dataclass(frozen=True)
class DGICAdapterResult:
    """
    The output of epistemic adaptation.

    Fields:
        scoring_mode           : How the engine result should be modified.
                                 One of: NORMAL | CONFIDENCE_SCALED | RISK_BOUNDED | ABSTAIN
        confidence_multiplier  : Factor applied to the engine's raw confidence_score.
        risk_ceiling           : Upper bound on risk_score (None = no ceiling).
        epistemic_warning      : True when epistemic state is ambiguous or unknown.
        abstain                : True when the system must not emit a risk signal.
        evidence_hash          : DGIC evidence_hash passed through unmodified.
        epistemic_state        : Original state, retained for auditability.
    """
    scoring_mode:          str
    confidence_multiplier: float
    risk_ceiling:          Optional[float]
    epistemic_warning:     bool
    abstain:               bool
    evidence_hash:         str
    epistemic_state:       EpistemicState


# ============================================================
# Contract Violation
# ============================================================

class DGICContractViolation(Exception):
    """Raised when the DGIC input violates the structural or cryptographic contract."""
    pass


# ============================================================
# Part A — Input Validation
# ============================================================

def build_evidence_hash(text: str) -> str:
    """Stub to simulate computing a hash. (Legacy/Test method)"""
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()

def compute_envelope_hash(version: str, lineage_hash: str, payload_dict: dict) -> str:
    """Computes the deterministic cryptographic seal of a DGIC envelope."""
    import hashlib
    import json
    # Ensure stable sorting for deterministic hashing
    payload_str = json.dumps(payload_dict, sort_keys=True)
    raw = f"{version}|{lineage_hash}|{payload_str}"
    return hashlib.sha256(raw.encode()).hexdigest()

def validate_dgic_input(dgic: DGICInput) -> None:
    """
    Validates the structural and cryptographic integrity of the DGIC schema_v1 envelope.
    Raises DGICContractViolation if invalid.
    """
    if not isinstance(dgic, DGICInput):
        raise DGICContractViolation("Input must be a DGICInput instance.")

    if dgic.version != "schema_v1":
        raise DGICContractViolation(f"Unsupported envelope version: {dgic.version}. Expected 'schema_v1'.")
        
    if not isinstance(dgic.lineage_hash, str) or len(dgic.lineage_hash) != 64:
        raise DGICContractViolation("lineage_hash must be a 64-character SHA-256 hex string.")
        
    if not isinstance(dgic.envelope_hash, str) or len(dgic.envelope_hash) != 64:
        raise DGICContractViolation("envelope_hash must be a 64-character SHA-256 hex string.")
        
    if not isinstance(dgic.payload, DGICPayload):
        raise DGICContractViolation("payload must be a valid DGICPayload object.")
        
    if not isinstance(dgic.payload.epistemic_state, EpistemicState):
        raise DGICContractViolation("payload.epistemic_state must be an EpistemicState enum.")
        
    if isinstance(dgic.payload.entropy_score, bool) or not isinstance(dgic.payload.entropy_score, (int, float)):
        raise DGICContractViolation("payload.entropy_score must be a numeric float.")
            
    import math
    if math.isnan(dgic.payload.entropy_score):
         raise DGICContractViolation("payload.entropy_score cannot be NaN (fails range check conceptually).")
         
    if not (0.0 <= dgic.payload.entropy_score <= 1.0):
        raise DGICContractViolation(f"payload.entropy_score {dgic.payload.entropy_score} out of bounds [0.0, 1.0].")
        
    if not isinstance(dgic.payload.contradiction_flag, bool):
        raise DGICContractViolation("payload.contradiction_flag must be a boolean.")
        
    # Cryptographic Seal Verification
    payload_dict = {
        "epistemic_state": dgic.payload.epistemic_state.value,
        "entropy_score": dgic.payload.entropy_score,
        "contradiction_flag": dgic.payload.contradiction_flag
    }
    expected_seal = compute_envelope_hash(dgic.version, dgic.lineage_hash, payload_dict)
    
    if expected_seal != dgic.envelope_hash:
        raise DGICContractViolation("Cryptographic seal broken: envelope_hash does not match payload hash. ENVELOPE TAMPERED.")

    if dgic.payload.epistemic_state == EpistemicState.AMBIGUOUS and dgic.collapse_flag:
        raise DGICContractViolation("Illegal epistemic collapse: AMBIGUOUS state cannot be forcefully collapsed to KNOWN/escalated.")


# ============================================================
# Part B — Epistemic Mapping (Deterministic)
# ============================================================

def adapt_dgic(dgic: DGICInput) -> DGICAdapterResult:
    """
    Deterministically maps the DGIC EpistemicState into scoring parameters.
    No probabilistic inference. No collapse of AMBIGUOUS.
    """
    # Defensive structural validation first
    validate_dgic_input(dgic)
    
    state = dgic.payload.epistemic_state
    entropy = dgic.payload.entropy_score

    if state == EpistemicState.KNOWN:
        result = DGICAdapterResult(
            scoring_mode          = "NORMAL",
            confidence_multiplier = 1.0,
            risk_ceiling          = None,
            epistemic_warning     = False,
            abstain               = False,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    elif state == EpistemicState.INFERRED:
        multiplier = round(1.0 - entropy * INFERRED_ENTROPY_SCALING_FACTOR, 6)
        multiplier = max(0.0, min(1.0, multiplier))  # clamp defensively
        result = DGICAdapterResult(
            scoring_mode          = "CONFIDENCE_SCALED",
            confidence_multiplier = multiplier,
            risk_ceiling          = None,
            epistemic_warning     = False,
            abstain               = False,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    elif state == EpistemicState.AMBIGUOUS:
        # Prevent escalation to HIGH entirely.
        result = DGICAdapterResult(
            scoring_mode          = "RISK_BOUNDED",
            confidence_multiplier = AMBIGUOUS_CONFIDENCE_MULTIPLIER,
            risk_ceiling          = AMBIGUOUS_RISK_CEILING,
            epistemic_warning     = True,
            abstain               = False,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    else:  # EpistemicState.UNKNOWN
        # Fail closed. Abstain.
        result = DGICAdapterResult(
            scoring_mode          = "ABSTAIN",
            confidence_multiplier = 0.0,
            risk_ceiling          = UNKNOWN_RISK_CEILING,
            epistemic_warning     = True,
            abstain               = True,
            evidence_hash         = dgic.lineage_hash,
            epistemic_state       = state,
        )

    logger.info(
        "DGIC adapter mapped epistemic state",
        extra={
            "event_type":         "dgic_adaptation",
            "epistemic_state":    state.value,
            "scoring_mode":       result.scoring_mode,
            "confidence_mult":    result.confidence_multiplier,
            "risk_ceiling":       result.risk_ceiling,
            "epistemic_warning":  result.epistemic_warning,
            "abstain":            result.abstain,
        }
    )

    return result


# ============================================================
# Part A — Score Modifier Application
# ============================================================

# Abstention error code
ABSTENTION_ERROR_CODE = "EPISTEMIC_ABSTENTION"

# Frozen safety_metadata — always identical, never derived from DGIC.
_SAFETY_METADATA: Dict[str, Any] = {
    "is_decision": False,
    "authority":   "NONE",
    "actionable":  False,
}


def apply_dgic_modifiers(
    base_result:    Dict[str, Any],
    adapter_result: DGICAdapterResult,
) -> Dict[str, Any]:
    """
    Applies DGIC-derived modifiers to a base engine result.
    Returns a NEW dict.
    """
    import copy
    result = copy.deepcopy(base_result)

    mode    = adapter_result.scoring_mode
    state   = adapter_result.epistemic_state

    # --- ABSTAIN ---
    if adapter_result.abstain:
        result["risk_score"]       = 0.0
        result["confidence_score"] = 0.0
        result["risk_category"]    = "LOW"
        result["trigger_reasons"]  = []
        result["processed_length"] = result.get("processed_length", 0)
        result["safety_metadata"]  = dict(_SAFETY_METADATA)
        result["errors"] = {
            "error_code": ABSTENTION_ERROR_CODE,
            "message":    (
                "Epistemic abstention: no grounded evidence available. "
                "Risk signal suppressed by DGIC UNKNOWN state."
            ),
        }
        result["dgic_metadata"] = {
            "epistemic_state":   state.value,
            "scoring_mode":      mode,
            "epistemic_warning": True,
            "evidence_hash":     adapter_result.evidence_hash,
        }
        return result

    # --- CONFIDENCE_SCALED ---
    if mode == "CONFIDENCE_SCALED":
        raw_conf = result.get("confidence_score", 1.0)
        scaled   = round(
            max(0.0, min(1.0, raw_conf * adapter_result.confidence_multiplier)),
            2
        )
        result["confidence_score"] = scaled

    # --- RISK_BOUNDED ---
    elif mode == "RISK_BOUNDED":
        ceiling = adapter_result.risk_ceiling
        raw_score = result.get("risk_score", 0.0)
        if ceiling is not None and raw_score > ceiling:
            clamped = round(ceiling, 2)
            result["risk_score"] = clamped
            result["risk_category"] = _score_to_category(clamped)
        
        raw_conf = result.get("confidence_score", 1.0)
        result["confidence_score"] = round(
            max(0.0, min(1.0, raw_conf * adapter_result.confidence_multiplier)), 2
        )

    # --- Authority invariant re-assertion (defensive) ---
    result["safety_metadata"] = dict(_SAFETY_METADATA)

    # --- dgic_metadata sidecar ---
    result["dgic_metadata"] = {
        "epistemic_state":   state.value,
        "scoring_mode":      mode,
        "epistemic_warning": adapter_result.epistemic_warning,
        "evidence_hash":     adapter_result.evidence_hash,
    }

    return result


def _score_to_category(score: float) -> str:
    """Recalculate risk_category from a (possibly clamped) score."""
    if score < 0.3:
        return "LOW"
    elif score < 0.7:
        return "MEDIUM"
    else:
        return "HIGH"

# ==================================================
# Source: app/dgic_snapshot_consumer.py
# ==================================================

"""
DGIC Snapshot Consumer
=======================
Formal ingestion, verification, and freezing of DGIC epistemic state snapshots.

This module is the ONLY entry point through which DGIC state enters enforcement.
All snapshots are frozen at ingestion — enforcement NEVER mutates upstream state.

Invariants (IMMUTABLE):
  - Snapshots are frozen (immutable) after ingestion.
  - Cryptographic seal is verified at ingestion time.
  - Snapshot hash is computed at ingestion and verified post-processing.
  - Entropy boundaries are classified at ingestion.
  - No field of the snapshot may be written to after ingestion.
"""


import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


logger = logging.getLogger(__name__)


# ============================================================
# Entropy Boundary Classification
# ============================================================

class EntropyBoundary(str, Enum):
    """
    Deterministic entropy zone classification.

    STABLE   — Low entropy. Full confidence in epistemic grounding.
    ELEVATED — Moderate entropy. Confidence degraded, extra caution warranted.
    CRITICAL — High entropy. Maximum caution. Signal reliability severely compromised.
    """
    STABLE = "STABLE"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


# Entropy threshold constants
ENTROPY_STABLE_CEILING = 0.3
ENTROPY_ELEVATED_CEILING = 0.7


def classify_entropy_boundary(entropy_score: float) -> EntropyBoundary:
    """
    Deterministically classify entropy into a boundary zone.

    [0.0, 0.3) → STABLE
    [0.3, 0.7) → ELEVATED
    [0.7, 1.0] → CRITICAL
    """
    if entropy_score < ENTROPY_STABLE_CEILING:
        return EntropyBoundary.STABLE
    elif entropy_score < ENTROPY_ELEVATED_CEILING:
        return EntropyBoundary.ELEVATED
    else:
        return EntropyBoundary.CRITICAL


# ============================================================
# DGIC Snapshot — Frozen at Ingestion
# ============================================================

@dataclass(frozen=True)
class DGICSnapshot:
    """
    An ingested and frozen DGIC epistemic state snapshot.

    All fields are set at ingestion and CANNOT be modified.
    The snapshot_hash is the cryptographic proof that enforcement
    did not mutate the DGIC state during processing.
    """
    snapshot_id: str
    ingested_at: str  # ISO-8601 UTC timestamp
    dgic_input: DGICInput  # The frozen DGIC envelope
    snapshot_hash: str  # SHA-256 of the snapshot at ingestion
    entropy_boundary: EntropyBoundary
    verified: bool  # True if cryptographic seal passed at ingestion


# ============================================================
# Snapshot Hash Computation
# ============================================================

def _compute_snapshot_hash(
    snapshot_id: str,
    ingested_at: str,
    dgic_input: DGICInput,
    entropy_boundary: EntropyBoundary,
) -> str:
    """
    Compute a deterministic SHA-256 hash of the entire snapshot state.
    Used to verify immutability: hash at ingestion == hash post-processing.
    """
    canonical = {
        "snapshot_id": snapshot_id,
        "ingested_at": ingested_at,
        "version": dgic_input.version,
        "lineage_hash": dgic_input.lineage_hash,
        "envelope_hash": dgic_input.envelope_hash,
        "epistemic_state": dgic_input.payload.epistemic_state.value,
        "entropy_score": dgic_input.payload.entropy_score,
        "contradiction_flag": dgic_input.payload.contradiction_flag,
        "collapse_flag": dgic_input.collapse_flag,
        "entropy_boundary": entropy_boundary.value,
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Snapshot Ingestion
# ============================================================

class DGICSnapshotError(Exception):
    """Raised when DGIC snapshot ingestion or verification fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def ingest_dgic_snapshot(
    epistemic_state: str,
    entropy_score: float,
    contradiction_flag: bool,
    lineage_hash: str,
    envelope_hash: str,
    snapshot_id: Optional[str] = None,
    ingestion_timestamp: Optional[str] = None,
) -> DGICSnapshot:
    """
    Formally ingest a DGIC epistemic state into a frozen snapshot.

    Pipeline:
      1. Parse raw fields into DGICInput (frozen dataclass)
      2. Validate cryptographic envelope seal
      3. Classify entropy boundary
      4. Compute snapshot hash at point of ingestion
      5. Return frozen DGICSnapshot — immutable from here forward

    Raises DGICSnapshotError on any validation failure.
    """
    # Generate snapshot metadata
    sid = snapshot_id or str(uuid.uuid4())
    ts = ingestion_timestamp or datetime.now(timezone.utc).isoformat()

    # Step 1: Parse into frozen DGICInput
    try:
        state_enum = EpistemicState(epistemic_state)
    except ValueError:
        raise DGICSnapshotError(
            "INVALID_EPISTEMIC_STATE",
            f"Invalid epistemic state: '{epistemic_state}'. Must be one of: KNOWN, INFERRED, AMBIGUOUS, UNKNOWN"
        )

    payload = DGICPayload(
        epistemic_state=state_enum,
        entropy_score=entropy_score,
        contradiction_flag=contradiction_flag,
    )

    dgic_input = DGICInput(
        version="schema_v1",
        lineage_hash=lineage_hash,
        envelope_hash=envelope_hash,
        payload=payload,
        collapse_flag=False,  # Enforcement NEVER collapses epistemic state
    )

    # Step 2: Validate cryptographic envelope seal
    verified = False
    try:
        validate_dgic_input(dgic_input)
        verified = True
    except DGICContractViolation as e:
        raise DGICSnapshotError(
            "DGIC_SEAL_VERIFICATION_FAILED",
            f"Cryptographic seal verification failed: {str(e)}"
        )

    # Step 3: Classify entropy boundary
    entropy_boundary = classify_entropy_boundary(entropy_score)

    # Step 4: Compute snapshot hash
    snapshot_hash = _compute_snapshot_hash(sid, ts, dgic_input, entropy_boundary)

    # Step 5: Construct frozen snapshot
    snapshot = DGICSnapshot(
        snapshot_id=sid,
        ingested_at=ts,
        dgic_input=dgic_input,
        snapshot_hash=snapshot_hash,
        entropy_boundary=entropy_boundary,
        verified=verified,
    )

    logger.info(
        "DGIC snapshot ingested",
        extra={
            "event_type": "dgic_snapshot_ingested",
            "snapshot_id": sid,
            "epistemic_state": epistemic_state,
            "entropy_score": entropy_score,
            "entropy_boundary": entropy_boundary.value,
            "contradiction_flag": contradiction_flag,
            "verified": verified,
            "snapshot_hash": snapshot_hash[:16] + "...",
        },
    )

    return snapshot


# ============================================================
# Post-Processing Integrity Verification
# ============================================================

def verify_snapshot_integrity(snapshot: DGICSnapshot) -> bool:
    """
    Verify that the snapshot was NOT mutated during enforcement processing.

    Recomputes the snapshot hash from current field values and compares
    to the hash recorded at ingestion time.

    Returns True if integrity holds. Raises DGICSnapshotError if violated.
    """
    recomputed = _compute_snapshot_hash(
        snapshot.snapshot_id,
        snapshot.ingested_at,
        snapshot.dgic_input,
        snapshot.entropy_boundary,
    )

    if recomputed != snapshot.snapshot_hash:
        logger.error(
            "DGIC snapshot integrity violation detected!",
            extra={
                "event_type": "dgic_snapshot_integrity_violation",
                "snapshot_id": snapshot.snapshot_id,
                "expected_hash": snapshot.snapshot_hash,
                "recomputed_hash": recomputed,
            },
        )
        raise DGICSnapshotError(
            "SNAPSHOT_INTEGRITY_VIOLATION",
            f"Snapshot {snapshot.snapshot_id} was mutated during processing. "
            f"Expected hash: {snapshot.snapshot_hash[:16]}..., "
            f"got: {recomputed[:16]}..."
        )

    logger.debug(
        "DGIC snapshot integrity verified",
        extra={
            "event_type": "dgic_snapshot_integrity_verified",
            "snapshot_id": snapshot.snapshot_id,
        },
    )

    return True


# ============================================================
# Snapshot Serialization (for replay ledger)
# ============================================================

def snapshot_to_dict(snapshot: DGICSnapshot) -> dict:
    """
    Serialize a DGICSnapshot to a plain dict for JSON storage / replay.
    """
    return {
        "snapshot_id": snapshot.snapshot_id,
        "ingested_at": snapshot.ingested_at,
        "version": snapshot.dgic_input.version,
        "lineage_hash": snapshot.dgic_input.lineage_hash,
        "envelope_hash": snapshot.dgic_input.envelope_hash,
        "epistemic_state": snapshot.dgic_input.payload.epistemic_state.value,
        "entropy_score": snapshot.dgic_input.payload.entropy_score,
        "contradiction_flag": snapshot.dgic_input.payload.contradiction_flag,
        "collapse_flag": snapshot.dgic_input.collapse_flag,
        "entropy_boundary": snapshot.entropy_boundary.value,
        "snapshot_hash": snapshot.snapshot_hash,
        "verified": snapshot.verified,
    }

# ==================================================
# Source: app/dgic_enforcement_bridge.py
# ==================================================

"""
DGIC Enforcement Bridge
========================
Wraps an AggregatedUnifiedSignal into a DGIC-compliant epistemic envelope
for downstream consumption by the Deterministic Graph Intelligence Core.

Authority Boundary (IMMUTABLE):
  - This module NEVER derives enforcement authority.
  - safety_metadata.is_decision remains False in all outputs.
  - safety_metadata.authority remains "NONE" in all outputs.
  - collapse_state is purely informational — it MUST NOT be used to derive authority.
  - All transformations are purely structural — no ML, no probabilistic inference.
"""


import hashlib
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.layer6_insightbridge import AggregatedUnifiedSignal, ScoredUnifiedSignal

logger = logging.getLogger(__name__)


# ============================================================
# Collapse State Enum (Deterministic)
# ============================================================

class CollapseState:
    """
    Deterministic collapse states derived from aggregation flags.

    STABLE    — No epistemic warnings, no abstentions. Full signal fidelity.
    DEGRADED  — At least one epistemic warning or partial abstention. Signal is usable but weakened.
    COLLAPSED — All signals abstained. No usable risk signal was produced.
    """
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    COLLAPSED = "COLLAPSED"


# Frozen safety metadata — always identical, never derived from DGIC.
_SAFETY_METADATA = {
    "is_decision": False,
    "authority": "NONE",
    "actionable": False,
}


# ============================================================
# Output Dataclass
# ============================================================

@dataclass(frozen=True)
class DGICEnforcementEnvelope:
    """
    DGIC-compliant epistemic envelope wrapping an aggregated signal.

    Fields:
        epistemic_confidence       : Deterministic composite confidence from aggregation.
        signal_lineage             : SHA-256 provenance chain of aggregation inputs.
        collapse_state             : STABLE | DEGRADED | COLLAPSED — informational only.
        truth_boundary_reference   : Immutable fingerprint of the aggregation inputs.
        aggregate_risk_score       : Clamped [0.0, 1.0] risk score.
        aggregate_risk_category    : LOW | MEDIUM | HIGH.
        signal_count               : Total number of input signals.
        active_signal_count        : Signals that were not abstained.
        contradiction_density      : Fraction of signals with contradiction_flag=True.
        safety_metadata            : Always {is_decision: False, authority: "NONE", actionable: False}.
        errors                     : None or structured error (e.g. all-abstain).
    """
    epistemic_confidence: float
    signal_lineage: str
    collapse_state: str
    truth_boundary_reference: str
    aggregate_risk_score: float
    aggregate_risk_category: str
    signal_count: int
    active_signal_count: int
    contradiction_density: float
    safety_metadata: dict
    errors: Optional[dict]


# ============================================================
# Collapse State Derivation (Deterministic)
# ============================================================

def _derive_collapse_state(agg: AggregatedUnifiedSignal) -> str:
    """
    Deterministically derive the collapse state from aggregation flags.

    Rules (evaluated in order):
      1. all_abstained=True  → COLLAPSED
      2. epistemic_warning=True OR any_abstained=True → DEGRADED
      3. Otherwise → STABLE
    """
    if agg.all_abstained:
        return CollapseState.COLLAPSED
    if agg.epistemic_warning or agg.any_abstained:
        return CollapseState.DEGRADED
    return CollapseState.STABLE


# ============================================================
# Lineage Computation
# ============================================================

def _compute_signal_lineage(agg: AggregatedUnifiedSignal) -> str:
    """
    Compute a deterministic SHA-256 lineage hash from the aggregation hash
    and per-signal evidence hashes.

    This provides full provenance: the lineage uniquely identifies
    which signals were combined and what evidence chain backs each one.
    """
    evidence_hashes = [s.evidence_hash for s in agg.scored_signals]
    lineage_input = {
        "aggregation_hash": agg.aggregation_hash,
        "evidence_chain": evidence_hashes,
    }
    serialised = json.dumps(lineage_input, sort_keys=True)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ============================================================
# Main Bridge Function
# ============================================================

def wrap_in_dgic_envelope(agg: AggregatedUnifiedSignal) -> DGICEnforcementEnvelope:
    """
    Wrap an AggregatedUnifiedSignal into a DGIC-compliant epistemic envelope.

    This is a pure structural transformation — no scoring, no mutation,
    no authority derivation, no probabilistic inference.
    """
    collapse_state = _derive_collapse_state(agg)
    signal_lineage = _compute_signal_lineage(agg)

    envelope = DGICEnforcementEnvelope(
        epistemic_confidence=agg.aggregate_confidence,
        signal_lineage=signal_lineage,
        collapse_state=collapse_state,
        truth_boundary_reference=agg.aggregation_hash,
        aggregate_risk_score=agg.aggregate_risk_score,
        aggregate_risk_category=agg.aggregate_risk_category,
        signal_count=agg.signal_count,
        active_signal_count=agg.active_signal_count,
        contradiction_density=agg.contradiction_density,
        safety_metadata=dict(_SAFETY_METADATA),
        errors=agg.errors,
    )

    logger.info(
        "DGIC enforcement envelope created",
        extra={
            "event_type": "dgic_envelope_created",
            "collapse_state": collapse_state,
            "epistemic_confidence": envelope.epistemic_confidence,
            "signal_lineage": signal_lineage[:16] + "...",
            "truth_boundary_reference": envelope.truth_boundary_reference[:16] + "...",
            "aggregate_risk_score": envelope.aggregate_risk_score,
        },
    )

    return envelope
