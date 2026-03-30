"""
Bucket Ledger Adapter
=======================
External adapter for the Primary Bucket Owner service.

This module replaces the internal JSONL persistence layer. It sends synchronous
HTTP POST requests to the separate Siddhesh-maintained Bucket Service.

Authority Boundary:
  - This module ONLY adapts formatting and handles the network border.
  - Failures fail-open (log error, allow execution) as per architecture policy.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# External service configuration
BUCKET_SERVICE_URL = os.environ.get("BUCKET_SERVICE_URL", "http://localhost:8000")


# ============================================================
# Hash Computation
# ============================================================

def compute_artifact_hash(artifact_dict: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA-256 hash required by the external 
    Bucket service envelope specification.
    """
    # Create copy without artifact_hash to avoid circular hashing
    proof_input = {k: v for k, v in artifact_dict.items() if k != "artifact_hash"}
    raw = json.dumps(proof_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# API Client
# ============================================================

def write_bucket_entry(
    execution_id: str,
    request_payload: Dict[str, Any],
    dgic_snapshot: Dict[str, Any],
    decision: str,
    risk_score: float,
    confidence: float,
    failure_reason: Optional[str],
    trace_hash: str,
) -> Optional[Dict[str, Any]]:
    """
    Synchronously submit the enforcement decision to the external Bucket service.
    Fails open (catches all exceptions, logs them, and does not crash out) to 
    prevent the Bucket from becoming a single point of failure for enforcement.
    """
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    
    # Structure payload inside typical execution details
    execution_payload = {
        "request_payload": request_payload,
        "dgic_snapshot": dgic_snapshot,
        "decision": decision,
        "risk_score": risk_score,
        "confidence": confidence,
        "failure_reason": failure_reason,
        "trace_hash": trace_hash
    }

    # Shape to match the Primary_Bucket_Owner canonical spec
    artifact = {
        "artifact_id": execution_id,
        "source_module_id": "bhiv_enforcement_gate",
        "schema_version": "1.0.0",
        "timestamp_utc": timestamp_utc,
        "artifact_type": "truth_event",
        "payload": execution_payload
    }

    # Add hash
    artifact["artifact_hash"] = compute_artifact_hash(artifact)

    # Dispatch synchronously to external service
    target_url = f"{BUCKET_SERVICE_URL.rstrip('/')}/bucket/artifact"
    
    try:
        logger.info(
            f"Dispatching artifact to external bucket | execution_id={execution_id}",
            extra={
                "event_type": "bucket_dispatch_start",
                "execution_id": execution_id,
                "target_url": target_url
            }
        )
        # Assuming a reasonable timeout so we don't hang enforcement forever
        response = requests.post(
            target_url,
            json=artifact,
            headers={"Content-Type": "application/json"},
            timeout=3.0
        )
        response.raise_for_status()
        
        logger.info(
            f"Artifact successfully stored in external bucket | execution_id={execution_id}",
            extra={
                "event_type": "bucket_dispatch_success",
                "execution_id": execution_id,
            }
        )
        return artifact
        
    except requests.exceptions.RequestException as e:
        # FAIL OPEN POLICY: We do not fail the core logic if logging to bucket fails.
        # Ensure we log loudly so telemetry or alerting catches it.
        logger.error(
            f"External bucket recording failed | execution_id={execution_id} | error={str(e)}",
            exc_info=True,
            extra={
                "event_type": "bucket_dispatch_failed",
                "execution_id": execution_id,
                "target_url": target_url,
                "error": str(e)
            }
        )
        return None


# ============================================================
# API Read Methods
# ============================================================

def get_bucket_entries(limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
    """
    Fetch raw artifacts from the external Bucket service.
    """
    target_url = f"{BUCKET_SERVICE_URL.rstrip('/')}/bucket/artifacts"
    try:
        response = requests.get(target_url, params={"limit": limit, "offset": offset}, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch bucket entries from {target_url}: {e}")
        return []

def get_bucket_entry(artifact_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a specific artifact from the external Bucket service by its ID.
    Note: Previously, the local system indexed by trace_hash. Now we query by artifact_id.
    """
    target_url = f"{BUCKET_SERVICE_URL.rstrip('/')}/bucket/artifact/{artifact_id}"
    try:
        response = requests.get(target_url, timeout=3.0)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch bucket entry {artifact_id} from {target_url}: {e}")
        return None
