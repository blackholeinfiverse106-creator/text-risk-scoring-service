"""
Tests for DGIC Snapshot Consumer
=================================
Validates formal DGIC snapshot ingestion, immutability, integrity verification,
cryptographic seals, and entropy boundary classification.
"""

import pytest
import hashlib
from datetime import datetime
from app.layer3_dgic import (
    ingest_dgic_snapshot,
    verify_snapshot_integrity,
    DGICSnapshotError,
    EntropyBoundary,
    DGICSnapshot,
)
from app.layer3_dgic import compute_envelope_hash


# ============================================================
# Helpers
# ============================================================

def _make_lineage_hash(seed: str = "test") -> str:
    return hashlib.sha256(seed.encode()).hexdigest()

def _make_valid_envelope_hash(
    epistemic_state: str,
    entropy_score: float,
    contradiction_flag: bool,
    lineage_hash: str,
) -> str:
    payload_dict = {
        "epistemic_state": epistemic_state,
        "entropy_score": entropy_score,
        "contradiction_flag": contradiction_flag,
    }
    return compute_envelope_hash("schema_v1", lineage_hash, payload_dict)


# ============================================================
# Ingestion Tests
# ============================================================

class TestDGICSnapshotIngestion:
    
    def test_ingest_valid_snapshot(self):
        """Valid ingestion creates a frozen DGICSnapshot with correct hash."""
        lineage = _make_lineage_hash()
        envelope = _make_valid_envelope_hash("KNOWN", 0.1, False, lineage)
        
        snapshot = ingest_dgic_snapshot(
            epistemic_state="KNOWN",
            entropy_score=0.1,
            contradiction_flag=False,
            lineage_hash=lineage,
            envelope_hash=envelope,
        )
        
        assert isinstance(snapshot, DGICSnapshot)
        assert snapshot.verified is True
        assert snapshot.entropy_boundary == EntropyBoundary.STABLE
        assert len(snapshot.snapshot_hash) == 64
        assert len(snapshot.snapshot_id) > 0
        assert snapshot.dgic_input.payload.epistemic_state.value == "KNOWN"

    def test_deterministic_snapshot_hash(self):
        """Identical inputs must yield identical snapshot hashes."""
        lineage = _make_lineage_hash()
        envelope = _make_valid_envelope_hash("INFERRED", 0.5, True, lineage)
        
        ts = "2024-01-01T12:00:00Z"
        sid = "snap-123"
        
        snap1 = ingest_dgic_snapshot("INFERRED", 0.5, True, lineage, envelope, snapshot_id=sid, ingestion_timestamp=ts)
        snap2 = ingest_dgic_snapshot("INFERRED", 0.5, True, lineage, envelope, snapshot_id=sid, ingestion_timestamp=ts)
        
        assert snap1.snapshot_hash == snap2.snapshot_hash

    def test_invalid_envelope_seal_rejected(self):
        """Invalid cryptographic seal raises DGICSnapshotError."""
        lineage = _make_lineage_hash()
        invalid_envelope = "a" * 64
        
        with pytest.raises(DGICSnapshotError) as exc:
            ingest_dgic_snapshot("KNOWN", 0.1, False, lineage, invalid_envelope)
            
        assert "SEAL_VERIFICATION_FAILED" in exc.value.code

    def test_invalid_epistemic_state_enum_rejected(self):
        """Invalid epistemic state string raises error."""
        lineage = _make_lineage_hash()
        envelope = _make_valid_envelope_hash("MAYBE", 0.1, False, lineage)
        
        with pytest.raises(DGICSnapshotError) as exc:
            ingest_dgic_snapshot("MAYBE", 0.1, False, lineage, envelope)
            
        assert "INVALID_EPISTEMIC_STATE" in exc.value.code


# ============================================================
# Entropy Boundary Tests
# ============================================================

class TestEntropyBoundaryClassification:
    
    def test_stable_boundary(self):
        """Entropy < 0.3 classified as STABLE."""
        lineage = _make_lineage_hash()
        for entropy in [0.0, 0.1, 0.29]:
            env = _make_valid_envelope_hash("KNOWN", entropy, False, lineage)
            snap = ingest_dgic_snapshot("KNOWN", entropy, False, lineage, env)
            assert snap.entropy_boundary == EntropyBoundary.STABLE

    def test_elevated_boundary(self):
        """0.3 <= Entropy < 0.7 classified as ELEVATED."""
        lineage = _make_lineage_hash()
        for entropy in [0.3, 0.5, 0.69]:
            env = _make_valid_envelope_hash("INFERRED", entropy, False, lineage)
            snap = ingest_dgic_snapshot("INFERRED", entropy, False, lineage, env)
            assert snap.entropy_boundary == EntropyBoundary.ELEVATED

    def test_critical_boundary(self):
        """Entropy >= 0.7 classified as CRITICAL."""
        lineage = _make_lineage_hash()
        for entropy in [0.7, 0.8, 1.0]:
            env = _make_valid_envelope_hash("INFERRED", entropy, True, lineage)
            snap = ingest_dgic_snapshot("INFERRED", entropy, True, lineage, env)
            assert snap.entropy_boundary == EntropyBoundary.CRITICAL


# ============================================================
# Immutability and Integrity Tests
# ============================================================

class TestSnapshotIntegrity:
    
    def test_verify_unmodified_snapshot_passes(self):
        """verify_snapshot_integrity returns True for unmodified snapshot."""
        lineage = _make_lineage_hash()
        envelope = _make_valid_envelope_hash("KNOWN", 0.1, False, lineage)
        
        snapshot = ingest_dgic_snapshot("KNOWN", 0.1, False, lineage, envelope)
        
        assert verify_snapshot_integrity(snapshot) is True

    def test_frozen_dataclass_prevents_mutation(self):
        """Dataclass freezing prevents standard attribute assignment."""
        lineage = _make_lineage_hash()
        envelope = _make_valid_envelope_hash("KNOWN", 0.1, False, lineage)
        snapshot = ingest_dgic_snapshot("KNOWN", 0.1, False, lineage, envelope)
        
        with pytest.raises(Exception):
            snapshot.verified = False
            
        with pytest.raises(Exception):
            snapshot.snapshot_hash = "mutated"

    def test_integrity_verification_catches_underlying_mutation(self):
        """If internal state is somehow bypassed/mutated, verify catches it."""
        lineage = _make_lineage_hash()
        envelope = _make_valid_envelope_hash("KNOWN", 0.1, False, lineage)
        snapshot = ingest_dgic_snapshot("KNOWN", 0.1, False, lineage, envelope)
        
        # Bypass Python dataclass freeze via object.__setattr__
        object.__setattr__(snapshot, "entropy_boundary", EntropyBoundary.CRITICAL)
        
        with pytest.raises(DGICSnapshotError) as exc:
            verify_snapshot_integrity(snapshot)
            
        assert "INTEGRITY_VIOLATION" in exc.value.code
