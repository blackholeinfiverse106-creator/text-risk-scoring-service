"""
Tests for Sarathi Enforcement Token Gate — Phase 3 + Phase 4
=============================================================
Validates:
  Phase 3 — Token Validation Engine:
    - execution_id match check
    - RAJYA verdict check
    - token_status check
    - signature hash integrity check
    - HARD BLOCK on any failure

  Phase 4 — Gate Implementation:
    - enforce_token(valid_token) → ALLOW
    - enforce_token(invalid_token) → BLOCK (SarathiHardBlockError)
    - enforce_token(None) → BLOCK (SarathiHardBlockError)
    - NO other logic allowed
"""

import pytest
import hashlib
from dataclasses import replace

from app.layer1_sarathi import (
    SarathiEnforcementToken,
    SarathiHardBlockError,
    SarathiTokenMintError,
    mint_enforcement_token,
    validate_enforcement_token,
    enforce_token,
)


# ============================================================
# Helpers
# ============================================================

def _mint_valid_token(
    execution_id: str = "exec-001",
    timestamp: str = "2026-04-28T12:00:00.000000Z",
) -> SarathiEnforcementToken:
    """Mint a valid enforcement token for testing."""
    return mint_enforcement_token(
        execution_id=execution_id,
        rajya_verdict="EXECUTION_APPROVED",
        timestamp=timestamp,
    )


def _compute_expected_hash(execution_id: str, rajya_verdict: str, timestamp: str) -> str:
    return hashlib.sha256(
        f"{execution_id}|{rajya_verdict}|{timestamp}".encode("utf-8")
    ).hexdigest()


# ============================================================
# Phase 3: Token Validation Engine
# ============================================================

class TestTokenValidationEngine:
    """Phase 3: validate_enforcement_token checks."""

    def test_valid_token_passes(self):
        """Valid token passes all checks."""
        token = _mint_valid_token()
        assert validate_enforcement_token(token) is True

    def test_valid_token_with_matching_execution_id(self):
        """Valid token + matching pipeline execution_id passes."""
        token = _mint_valid_token(execution_id="exec-match-001")
        assert validate_enforcement_token(token, pipeline_execution_id="exec-match-001") is True

    def test_execution_id_mismatch_fails(self):
        """Token execution_id != pipeline execution_id → HARD BLOCK."""
        token = _mint_valid_token(execution_id="exec-token-id")
        assert validate_enforcement_token(token, pipeline_execution_id="exec-DIFFERENT-id") is False

    def test_rajya_verdict_not_approved_fails(self):
        """rajya_verdict != EXECUTION_APPROVED → HARD BLOCK."""
        token = _mint_valid_token()
        # Create a tampered token with wrong verdict
        tampered = SarathiEnforcementToken(
            execution_id=token.execution_id,
            rajya_verdict="REJECT",
            token_status="VALID",
            timestamp=token.timestamp,
            signature_hash=token.signature_hash,
        )
        assert validate_enforcement_token(tampered) is False

    def test_token_status_not_valid_fails(self):
        """token_status != VALID → HARD BLOCK."""
        token = _mint_valid_token()
        tampered = SarathiEnforcementToken(
            execution_id=token.execution_id,
            rajya_verdict=token.rajya_verdict,
            token_status="INVALID",
            timestamp=token.timestamp,
            signature_hash=token.signature_hash,
        )
        assert validate_enforcement_token(tampered) is False

    def test_signature_hash_tampered_fails(self):
        """Tampered signature_hash → HARD BLOCK."""
        token = _mint_valid_token()
        tampered = SarathiEnforcementToken(
            execution_id=token.execution_id,
            rajya_verdict=token.rajya_verdict,
            token_status=token.token_status,
            timestamp=token.timestamp,
            signature_hash="a" * 64,  # tampered
        )
        assert validate_enforcement_token(tampered) is False

    def test_signature_hash_is_deterministic(self):
        """Same inputs → same signature hash."""
        token1 = _mint_valid_token(execution_id="det-001", timestamp="2026-01-01T00:00:00Z")
        token2 = _mint_valid_token(execution_id="det-001", timestamp="2026-01-01T00:00:00Z")
        assert token1.signature_hash == token2.signature_hash

    def test_different_inputs_different_hash(self):
        """Different execution_ids → different signature hashes."""
        token1 = _mint_valid_token(execution_id="det-001")
        token2 = _mint_valid_token(execution_id="det-002")
        assert token1.signature_hash != token2.signature_hash

    def test_hash_matches_expected_computation(self):
        """signature_hash = SHA-256(execution_id|rajya_verdict|timestamp)."""
        exec_id = "exec-hash-check"
        ts = "2026-04-28T12:00:00Z"
        token = _mint_valid_token(execution_id=exec_id, timestamp=ts)
        expected = _compute_expected_hash(exec_id, "EXECUTION_APPROVED", ts)
        assert token.signature_hash == expected

    def test_none_pipeline_id_skips_id_check(self):
        """When pipeline_execution_id is None, execution_id check is skipped."""
        token = _mint_valid_token(execution_id="any-id")
        assert validate_enforcement_token(token, pipeline_execution_id=None) is True


# ============================================================
# Phase 4: Gate Implementation — enforce_token()
# ============================================================

class TestEnforceTokenGate:
    """Phase 4: enforce_token() returns ALLOW or raises BLOCK."""

    def test_valid_token_returns_allow(self):
        """VALID token → ALLOW."""
        token = _mint_valid_token()
        result = enforce_token(token)
        assert result == "ALLOW"

    def test_valid_token_with_matching_id_returns_allow(self):
        """VALID token + matching pipeline ID → ALLOW."""
        token = _mint_valid_token(execution_id="gate-001")
        result = enforce_token(token, pipeline_execution_id="gate-001")
        assert result == "ALLOW"

    def test_none_token_raises_hard_block(self):
        """None token → BLOCK (SarathiHardBlockError)."""
        with pytest.raises(SarathiHardBlockError) as exc_info:
            enforce_token(None)
        assert exc_info.value.code == "TOKEN_MISSING"

    def test_invalid_verdict_raises_hard_block(self):
        """Token with wrong rajya_verdict → BLOCK."""
        token = SarathiEnforcementToken(
            execution_id="exec-001",
            rajya_verdict="REJECT",
            token_status="VALID",
            timestamp="2026-01-01T00:00:00Z",
            signature_hash="a" * 64,
        )
        with pytest.raises(SarathiHardBlockError) as exc_info:
            enforce_token(token)
        assert exc_info.value.code == "TOKEN_INVALID"

    def test_tampered_hash_raises_hard_block(self):
        """Token with tampered hash → BLOCK."""
        token = _mint_valid_token()
        tampered = SarathiEnforcementToken(
            execution_id=token.execution_id,
            rajya_verdict=token.rajya_verdict,
            token_status=token.token_status,
            timestamp=token.timestamp,
            signature_hash="b" * 64,
        )
        with pytest.raises(SarathiHardBlockError) as exc_info:
            enforce_token(tampered)
        assert exc_info.value.code == "TOKEN_INVALID"

    def test_execution_id_mismatch_raises_hard_block(self):
        """Token execution_id != pipeline ID → BLOCK."""
        token = _mint_valid_token(execution_id="exec-TOKEN")
        with pytest.raises(SarathiHardBlockError) as exc_info:
            enforce_token(token, pipeline_execution_id="exec-PIPELINE")
        assert exc_info.value.code == "TOKEN_INVALID"

    def test_invalid_status_raises_hard_block(self):
        """Token with status != VALID → BLOCK."""
        token = _mint_valid_token()
        tampered = SarathiEnforcementToken(
            execution_id=token.execution_id,
            rajya_verdict=token.rajya_verdict,
            token_status="EXPIRED",
            timestamp=token.timestamp,
            signature_hash=token.signature_hash,
        )
        with pytest.raises(SarathiHardBlockError) as exc_info:
            enforce_token(tampered)
        assert exc_info.value.code == "TOKEN_INVALID"

    def test_enforce_token_only_returns_allow_string(self):
        """enforce_token() return value is exactly the string 'ALLOW'."""
        token = _mint_valid_token()
        result = enforce_token(token)
        assert result == "ALLOW"
        assert isinstance(result, str)

    def test_hard_block_error_has_code_and_message(self):
        """SarathiHardBlockError carries structured code and message."""
        with pytest.raises(SarathiHardBlockError) as exc_info:
            enforce_token(None)
        err = exc_info.value
        assert hasattr(err, "code")
        assert hasattr(err, "message")
        assert isinstance(err.code, str)
        assert isinstance(err.message, str)


# ============================================================
# Mint rejection — token never created without RAJYA approval
# ============================================================

class TestMintRejection:
    """Verify mint_enforcement_token refuses non-APPROVED verdicts."""

    def test_reject_verdict_raises(self):
        with pytest.raises(SarathiTokenMintError):
            mint_enforcement_token("exec-001", "REJECT", "2026-01-01T00:00:00Z")

    def test_empty_verdict_raises(self):
        with pytest.raises(SarathiTokenMintError):
            mint_enforcement_token("exec-001", "", "2026-01-01T00:00:00Z")

    def test_random_verdict_raises(self):
        with pytest.raises(SarathiTokenMintError):
            mint_enforcement_token("exec-001", "MAYBE_APPROVED", "2026-01-01T00:00:00Z")
