"""
Tests for External Bucket Ledger Adapter
========================================
Validates that the external adapter formats artifacts according to 
the Primary_Bucket_Owner envelope specification, and handles HTTP routing
and fail-open semantics correctly.
"""

import json
import pytest
import requests
from unittest.mock import patch, MagicMock

from app.layer5_bucket import (
    write_bucket_entry,
    get_bucket_entries,
    get_bucket_entry,
    compute_artifact_hash,
    BUCKET_SERVICE_URL,
)


# ============================================================
# Hash Computation
# ============================================================

def test_compute_artifact_hash_excludes_itself():
    artifact = {
        "artifact_id": "exec-123",
        "timestamp_utc": "2025-01-19T10:00:00Z",
        "artifact_hash": "should_be_ignored",
        "payload": {"data": "test"}
    }
    
    # Should yield the exact same hash as if artifact_hash was never there
    pure_artifact = {
        "artifact_id": "exec-123",
        "timestamp_utc": "2025-01-19T10:00:00Z",
        "payload": {"data": "test"}
    }
    
    hash1 = compute_artifact_hash(artifact)
    hash2 = compute_artifact_hash(pure_artifact)
    
    assert hash1 == hash2


# ============================================================
# Write Entry (POST)
# ============================================================

@patch("app.layer5_bucket.requests.post")
def test_write_bucket_entry_success(mock_post):
    """Test that a successful post formats the artifact correctly."""
    
    # Mock successful response
    mock_post.return_value = MagicMock()
    mock_post.return_value.raise_for_status = MagicMock()
    mock_post.return_value.text = '{"hash": "mocked_hash"}'
    mock_post.return_value.json.return_value = {"hash": "mocked_hash"}

    result = write_bucket_entry(
        execution_id="exec-abc-123",
        request_payload={"actor": "AI_BEING_1"},
        dgic_snapshot={"epistemic_state": "KNOWN"},
        decision="ALLOW",
        risk_score=0.1,
        confidence=0.9,
        failure_reason=None,
        trace_hash="a"*64
    )

    # Validate output
    assert result is not None
    assert result["artifact_id"] == "exec-abc-123"
    assert result["source_module_id"] == "text_risk_scoring_service"
    assert result["schema_version"] == "1.0.0"
    assert result["artifact_type"] == "truth_event"
    assert "artifact_hash" in result
    
    # Payload validation
    payload = result["payload"]
    assert payload["decision"] == "ALLOW"
    assert payload["risk_score"] == 0.1
    assert payload["trace_hash"] == "a"*64

    # Validate network call
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == f"{BUCKET_SERVICE_URL}/bucket/artifact"
    assert kwargs["json"] == result


@patch("app.layer5_bucket.requests.post")
def test_write_bucket_entry_fail_open(mock_post):
    """Test that if the bucket service fails, we catch the exception and return None."""
    
    # Mock network failure
    mock_post.side_effect = requests.exceptions.ConnectionError("Service unavailable")

    result = write_bucket_entry(
        execution_id="exec-xyz-999",
        request_payload={},
        dgic_snapshot={},
        decision="DENY",
        risk_score=0.9,
        confidence=0.9,
        failure_reason="Too risky",
        trace_hash="b"*64
    )

    # Result should be None (fail open)
    assert result is None


# ============================================================
# Read Entries (GET)
# ============================================================

@patch("app.layer5_bucket.requests.get")
def test_get_bucket_entries(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [{"artifact_id": "test"}]
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    entries = get_bucket_entries(limit=10, offset=0)
    assert len(entries) == 1
    assert entries[0]["artifact_id"] == "test"

    mock_get.assert_called_with(
        f"{BUCKET_SERVICE_URL}/bucket/artifacts",
        params={"limit": 10, "offset": 0},
        timeout=5.0
    )


@patch("app.layer5_bucket.requests.get")
def test_get_bucket_entry(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"artifact_id": "exec-abc-123"}
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    entry = get_bucket_entry("exec-abc-123")
    assert entry is not None
    assert entry["artifact_id"] == "exec-abc-123"

    mock_get.assert_called_with(
        f"{BUCKET_SERVICE_URL}/bucket/artifact/exec-abc-123",
        timeout=3.0
    )

@patch("app.layer5_bucket.requests.get")
def test_get_bucket_entry_not_found(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    entry = get_bucket_entry("missing-id")
    assert entry is None
