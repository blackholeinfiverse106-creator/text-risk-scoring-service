from __future__ import annotations
"""
Sovereign Layer File: app/layer1_sarathi.py
"""


# ==================================================
# Source: app/engine.py
# ==================================================

import re
import logging
import uuid
import time
from typing import Dict, Any

# =========================
# Logging Setup (STEP 3.1)
# =========================
# Logging configured by main app entry point
logger = logging.getLogger(__name__)

# =========================
# Configuration Constants
# =========================
MAX_TEXT_LENGTH = 5000
KEYWORD_WEIGHT = 0.2
MAX_CATEGORY_SCORE = 0.6  # Prevents saturation from one category


# =========================
# Risk Keywords
# =========================
RISK_KEYWORDS = {
    # Violence & Physical Harm
    "violence": [
        "kill", "killing", "murder", "murdered", "attack", "attacked",
        "assault", "stab", "stabbing", "shoot", "shooting",
        "bomb", "explosion", "explode", "terror", "terrorist",
        "gun", "knife", "weapon", "fight", "fighting",
        "beat", "beating", "strangle", "choke", "burn",
        "dead", "death", "execute", "execution"
    ],

    # Fraud & Financial Crime
    "fraud": [
        "scam", "scammer", "fraud", "fraudulent", "hack", "hacked",
        "phish", "phishing", "spoof", "spoofing", "identity theft",
        "fake", "forgery", "impersonate", "impersonation",
        "credit card fraud", "stolen card", "money laundering",
        "ponzi", "pyramid scheme", "crypto scam",
        "investment scam", "loan scam", "refund scam",
        "account takeover", "otp scam"
    ],

    # Abuse & Harassment
    "abuse": [
        "idiot", "stupid", "dumb", "moron", "loser",
        "hate", "hateful", "trash", "garbage",
        "shut up", "get lost", "go die",
        "worthless", "pathetic", "disgusting",
        "racist", "sexist", "bigot",
        "slur", "insult", "harass", "harassment",
        "bully", "bullying"
    ],

    # Sexual & Explicit Content
    "sexual": [
        "sex", "sexual", "porn", "pornography", "nude", "naked",
        "explicit", "adult content", "xxx", "fetish",
        "escort", "prostitute", "hooker",
        "rape", "molest", "sexual assault",
        "child abuse", "minor sexual"
    ],

    # Drugs & Illegal Substances
    "drugs": [
        "drug", "drugs", "cocaine", "heroin", "meth",
        "weed", "marijuana", "ganja", "hash",
        "lsd", "ecstasy", "mdma",
        "overdose", "inject", "dealer", "drug dealer",
        "illegal substance", "narcotics"
    ],

    # Extremism & Radicalization
    "extremism": [
        "terrorism", "terrorist", "extremist",
        "radicalize", "radicalization",
        "isis", "al qaeda", "taliban",
        "jihad", "holy war",
        "white supremacy", "neo nazi",
        "hate group", "militant"
    ],

    # Self-Harm & Suicide
    "self_harm": [
        "suicide", "kill myself", "self harm",
        "cut myself", "cutting",
        "end my life", "want to die",
        "no reason to live",
        "jump off", "hang myself",
        "overdose myself"
    ],

    # Cybercrime & Hacking
    "cybercrime": [
        "ddos", "malware", "ransomware",
        "virus", "trojan", "spyware",
        "keylogger", "backdoor",
        "brute force", "sql injection",
        "zero day", "exploit",
        "payload", "botnet"
    ],

    # Weapons & Illegal Tools
    "weapons": [
        "gun", "firearm", "rifle", "pistol",
        "ammunition", "ammo",
        "grenade", "missile",
        "explosive", "bomb",
        "knife", "dagger", "blade",
        "silencer", "automatic weapon"
    ],

    # Threats & Intimidation
    "threats": [
        "i will kill you", "you will die",
        "i will hurt you",
        "watch your back",
        "you are dead",
        "i am coming for you",
        "threaten", "threatening",
        "extort", "blackmail",
        "ransom"
    ]
}


# =========================
# Error Response Helper
# =========================
def error_response(code: str, message: str, execution_id: str = "UNKNOWN") -> Dict[str, Any]:
    logger.error(
        f"Error response generated: {code}",
        extra={"execution_id": execution_id, "event_type": "error_response_generated", "details": {"code": code, "message": message}}
    )
    return {
        "risk_score": 0.0,
        "confidence_score": 0.0,
        "risk_category": "LOW",
        "trigger_reasons": [],
        "processed_length": 0,
        "safety_metadata": {
            "is_decision": False,
            "authority": "NONE",
            "actionable": False
        },
        "errors": {
            "error_code": code,
            "message": message
        }
    }

# =========================
# Core Analysis Function
# =========================
def analyze_text(text: str, execution_id: str = "UNKNOWN") -> Dict[str, Any]:
    try:
        start_time = time.time()
        
        logger.info("Request started", extra={"execution_id": execution_id, "event_type": "analysis_start"})
        # =========================
        # F-02: INVALID TYPE
        # =========================
        if not isinstance(text, str):
            return error_response("INVALID_TYPE", "Input must be a string", execution_id)

        logger.info(f"Received text for analysis | len={len(text)}", extra={"execution_id": execution_id, "event_type": "input_received", "details": {"raw_length": len(text)}})

        # Normalize input
        text = text.strip().lower()

        # =========================
        # F-01: EMPTY INPUT
        # =========================
        if not text:
            return error_response("EMPTY_INPUT", "Text is empty", execution_id)

        # =========================
        # F-03: EXCESSIVE LENGTH
        # =========================
        truncated = False
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(
                "Input truncated",
                extra={"execution_id": execution_id, "event_type": "input_truncated", "details": {"original_length": len(text), "max_length": MAX_TEXT_LENGTH}}
            )
            text = text[:MAX_TEXT_LENGTH]
            truncated = True

        total_score = 0.0
        reasons = []

        keyword_count = 0
        matched_categories = set()

        # =========================
        # CORE MATCHING LOGIC
        # =========================
        for category, keywords in sorted(RISK_KEYWORDS.items()):
            category_score = 0.0

            for keyword in keywords:
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, text):
                    logger.info(
                        f"Keyword detected: {keyword}",
                        extra={"execution_id": execution_id, "event_type": "keyword_detected", "details": {"category": category, "keyword": keyword}}
                    )
                    category_score += KEYWORD_WEIGHT
                    keyword_count += 1
                    matched_categories.add(category)
                    reasons.append(f"Detected {category} keyword: {keyword}")

            # =========================
            # F-04: CATEGORY SATURATION
            # =========================
            if category_score > MAX_CATEGORY_SCORE:
                logger.warning(
                    f"Category score capped for {category}",
                    extra={"execution_id": execution_id, "event_type": "category_capped", "details": {"category": category, "raw_score": category_score, "cap": MAX_CATEGORY_SCORE}}
                )
                category_score = MAX_CATEGORY_SCORE

            total_score += category_score

        # =========================
        # F-06: SCORE CLAMPING
        # =========================
        if total_score > 1.0:
            logger.warning(
                "Total score clamped",
                extra={"execution_id": execution_id, "event_type": "score_clamped", "details": {"raw_score": total_score, "cap": 1.0}}
            )
            total_score = 1.0

        # =========================
        # RISK THRESHOLDS
        # =========================
        # Explicit interval definitions covering the entire domain [0.0, 1.0]
        if total_score < 0.3:
            risk_category = "LOW"
        elif 0.3 <= total_score < 0.7:
            risk_category = "MEDIUM"
        else:
            # Implies total_score >= 0.7
            risk_category = "HIGH"

        # =========================
        # INVARIANT CHECK: Score/Category Consistency
        # =========================
        if total_score >= 0.7 and risk_category != "HIGH":
             logger.error("Invariant violation detected", extra={"execution_id": execution_id, "event_type": "invariant_correction", "details": {"score": total_score, "category": risk_category, "correction": "HIGH"}})
             risk_category = "HIGH"
        
        if total_score < 0.3 and risk_category == "HIGH":
             logger.error("Invariant violation detected", extra={"execution_id": execution_id, "event_type": "invariant_correction", "details": {"score": total_score, "category": "HIGH", "correction": "LOW"}})
             risk_category = "LOW"

        # =========================
        # CONFIDENCE SCORE
        # =========================
        confidence = 1.0
        category_count = len(matched_categories)

        if keyword_count == 0:
            confidence = 1.0
        else:
            if keyword_count == 1:
                confidence -= 0.3
            if category_count > 1:
                confidence -= 0.2
            if keyword_count <= 2:
                confidence -= 0.2

        confidence = max(0.0, min(confidence, 1.0))

        processing_time = time.time() - start_time
        logger.info(
            f"Final decision: {risk_category}",
            extra={"execution_id": execution_id, "event_type": "analysis_complete", "details": {"score": total_score, "confidence": confidence, "category": risk_category, "processing_time_ms": processing_time * 1000}}
        )

        if truncated:
            reasons.append("Input text was truncated to safe maximum length")

        return {
            "risk_score": round(total_score, 2),
            "confidence_score": round(confidence, 2),
            "risk_category": risk_category,
            "trigger_reasons": reasons,
            "processed_length": len(text),
            "safety_metadata": {
                "is_decision": False,
                "authority": "NONE",
                "actionable": False
            },
            "errors": None
        }

    # =========================
    # F-07: UNEXPECTED FAILURE
    # =========================
    except Exception:
        logger.error(
            "Unexpected runtime error during text analysis",
            exc_info=True,
            extra={"execution_id": execution_id, "event_type": "unhandled_exception"}
        )
        return error_response(
            "INTERNAL_ERROR",
            "Unexpected processing error",
            execution_id
        )


# ==================================================
# Source: app/sarathi_governance.py
# ==================================================

"""
Sarathi Governance Engine — Layer 1 Decision Engine
==================================================
The single deterministic governance gate through which ALL proposed actions
pass before being sent to the execution gate in the BHIV ecosystem.

Invariants (IMMUTABLE):
  - All decisions are deterministic: same inputs → same output, always.
  - No probabilistic outputs. No mutation of upstream epistemic states.
  - DGIC epistemic state is consumed read-only.
  - Trace hash enables byte-identical replay verification.
  - UNKNOWN epistemic state → ABSTAIN (fail-safe).
  - AMBIGUOUS + elevated risk → DENY (conservative).
"""


import hashlib
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional

from app.enforcement_schemas import (
    EvaluateActionRequest,
    SarathiEvaluateResponse,
    SarathiDecision,
    SourceSystem,
)
from app.layer3_dgic import (
    adapt_dgic,
    apply_dgic_modifiers,
)
from app.layer3_dgic import (
    ingest_dgic_snapshot,
    verify_snapshot_integrity,
    DGICSnapshotError,
    EntropyBoundary,
)
from app.insightbridge_rules import calculate_weighted_signal
from app.marine_rules import calculate_marine_signal
from app.aiaic_rules import calculate_aiaic_signal
from app.c4s_rules import calculate_c4s_signal
from app.layer3_dgic import snapshot_to_dict

logger = logging.getLogger(__name__)


# ============================================================
# Constants — Enforcement Thresholds
# ============================================================

# Risk score at or above this threshold → DENY
DENY_RISK_THRESHOLD = 0.7

# AMBIGUOUS epistemic state + risk at or above this → DENY
AMBIGUOUS_DENY_THRESHOLD = 0.3


# ============================================================
# Trace Hash Computation
# ============================================================

def compute_trace_hash(request: EvaluateActionRequest) -> str:
    """
    Compute a deterministic SHA-256 trace hash from all input fields.
    Guarantees: same inputs → same hash. Enables replay verification.
    """
    # Build a canonical, sorted representation of all inputs
    context_signals_canonical = [
        {
            "signal_id": s.signal_id,
            "signal_type": s.signal_type,
            "value": s.value,
            "source": s.source,
        }
        for s in sorted(request.context_signals, key=lambda s: s.signal_id)
    ]

    canonical = {
        "execution_id": request.execution_id,
        "actor": request.actor,
        "proposed_action": request.proposed_action,
        "context_signals": context_signals_canonical,
        "dgic_epistemic_state": {
            "epistemic_state": request.dgic_epistemic_state.epistemic_state,
            "entropy_score": request.dgic_epistemic_state.entropy_score,
            "contradiction_flag": request.dgic_epistemic_state.contradiction_flag,
            "lineage_hash": request.dgic_epistemic_state.lineage_hash,
            "envelope_hash": request.dgic_epistemic_state.envelope_hash,
        },
        "source_system": request.source_system.value,
    }

    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ============================================================
# Context Signal Aggregation
# ============================================================

def aggregate_context_signals(request: EvaluateActionRequest) -> float:
    """
    Deterministic weighted aggregation of context signals.
    Returns 0.0 if no signals provided.
    
    InsightBridge signals are mathematically weighted by severity type.
    Other sources currently default to 1.0 multiplier (raw value).
    
    Uses max-of-weighted-signals (fail-high) strategy.
    """
    if not request.context_signals:
        return 0.0

    weighted_values = []
    for signal in request.context_signals:
        source_upper = signal.source.upper()
        if source_upper == SourceSystem.INSIGHTBRIDGE.value:
            weighted_values.append(calculate_weighted_signal(signal))
        elif source_upper == SourceSystem.MARINE_INTELLIGENCE.value:
            weighted_values.append(calculate_marine_signal(signal))
        elif source_upper == SourceSystem.AIAIC.value:
            weighted_values.append(calculate_aiaic_signal(signal))
        elif source_upper == SourceSystem.C4S.value:
            weighted_values.append(calculate_c4s_signal(signal))
        else:
            # Other signals maintain 1.0 multiplier (raw value)
            weighted_values.append(signal.value)

    # Fail-high: take the maximum computed weighted signal
    return max(weighted_values)


# ============================================================
# Sarathi Governance Evaluation
# ============================================================

def evaluate_action(request: EvaluateActionRequest) -> SarathiEvaluateResponse:
    """
    The deterministic governance gate.

    Pipeline:
      1. Compute trace hash (for replay verification)
      2. Validate DGIC envelope
      3. Map epistemic state to scoring modifiers
      4. Analyze proposed action text for risk
      5. Apply DGIC epistemic modifiers
      6. Aggregate context signals
      7. Compute final risk = max(text_risk, context_risk)
      8. Make deterministic decision (ALLOW / DENY / ABSTAIN)

    Returns: SarathiEvaluateResponse — fully structured, no unstructured output.
    """
    execution_id = request.execution_id
    start_time = time.time()
    from datetime import datetime, timezone
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Sarathi governance evaluation started",
        extra={
            "event_type": "sarathi_evaluate_start",
            "execution_id": execution_id,
            "actor": request.actor,
            "source_system": request.source_system.value,
        },
    )

    # Step 1: Trace hash (computed FIRST — before any processing)
    trace_hash = compute_trace_hash(request)

    # Step 2: Ingest and freeze DGIC snapshot
    try:
        snapshot = ingest_dgic_snapshot(
            epistemic_state=request.dgic_epistemic_state.epistemic_state,
            entropy_score=request.dgic_epistemic_state.entropy_score,
            contradiction_flag=request.dgic_epistemic_state.contradiction_flag,
            lineage_hash=request.dgic_epistemic_state.lineage_hash,
            envelope_hash=request.dgic_epistemic_state.envelope_hash,
        )
    except DGICSnapshotError as e:
        logger.warning(
            f"DGIC snapshot ingestion failed | execution_id={execution_id}",
            extra={
                "execution_id": execution_id,
                "event_type": "sarathi_snapshot_error",
                "details": str(e),
            },
        )
        return SarathiEvaluateResponse(
            execution_id=execution_id,
            risk_score=0.0,
            sarathi_decision=SarathiDecision.ABSTAIN,
            confidence=0.0,
            failure_reason=f"DGIC snapshot rejected: {str(e)}",
            trace_hash=trace_hash,
        )

    # Step 3: Map epistemic state to scoring modifiers
    adapter_result = adapt_dgic(snapshot.dgic_input)

    # Step 4: Check for epistemic ABSTAIN (UNKNOWN state)
    if adapter_result.abstain:
        logger.info(
            f"Epistemic abstention | execution_id={execution_id}",
            extra={
                "execution_id": execution_id,
                "event_type": "sarathi_abstain",
                "epistemic_state": adapter_result.epistemic_state.value,
            },
        )
        return SarathiEvaluateResponse(
            execution_id=execution_id,
            risk_score=0.0,
            sarathi_decision=SarathiDecision.ABSTAIN,
            confidence=0.0,
            failure_reason="Epistemic abstention: no grounded evidence available (DGIC UNKNOWN state). Caller must handle conservatively.",
            trace_hash=trace_hash,
        )

    # Step 5: Analyze proposed action text for risk
    base_result = analyze_text(request.proposed_action, execution_id=execution_id)

    # Step 6: Apply DGIC epistemic modifiers
    modified_result = apply_dgic_modifiers(base_result, adapter_result=adapter_result)
    text_risk = modified_result["risk_score"]
    confidence = modified_result["confidence_score"]

    # Step 7: Aggregate context signals
    context_risk = aggregate_context_signals(request)

    # Step 8: Final risk = max(text_risk, context_risk) — fail-high
    final_risk = round(max(text_risk, context_risk), 2)

    # Clamp to [0.0, 1.0]
    final_risk = max(0.0, min(1.0, final_risk))

    # Step 9: Deterministic decision
    decision: SarathiDecision
    failure_reason: Optional[str] = None

    if final_risk >= DENY_RISK_THRESHOLD:
        decision = SarathiDecision.DENY
        failure_reason = f"Risk score {final_risk} exceeds governance threshold {DENY_RISK_THRESHOLD}"
    elif snapshot.entropy_boundary == EntropyBoundary.CRITICAL:
        decision = SarathiDecision.DENY
        failure_reason = (
            f"CRITICAL entropy boundary exceeded. "
            "Action denied as fail-safe."
        )
    elif (
        adapter_result.epistemic_state.value == "AMBIGUOUS"
        and final_risk >= AMBIGUOUS_DENY_THRESHOLD
    ):
        decision = SarathiDecision.DENY
        failure_reason = (
            f"Ambiguous epistemic state with risk {final_risk} >= "
            f"conservative threshold {AMBIGUOUS_DENY_THRESHOLD}. "
            "Cannot allow action under epistemic uncertainty."
        )
    else:
        decision = SarathiDecision.ALLOW

    processing_time = time.time() - start_time

    # Construct the response
    response = SarathiEvaluateResponse(
        execution_id=execution_id,
        risk_score=final_risk,
        sarathi_decision=decision,
        confidence=confidence,
        failure_reason=failure_reason,
        trace_hash=trace_hash,
    )

    # Step 10: Verify snapshot immutability
    verify_snapshot_integrity(snapshot)

    # Step 11: Log decision
    logger.info(
        f"Sarathi decision: {decision.value}",
        extra={
            "execution_id": execution_id,
            "event_type": "sarathi_decision",
            "actor": request.actor,
            "source_system": request.source_system.value,
            "risk_score": final_risk,
            "confidence": confidence,
            "sarathi_decision": decision.value,
            "failure_reason": failure_reason,
            "trace_hash": trace_hash,
            "epistemic_state": adapter_result.epistemic_state.value,
            "entropy_boundary": snapshot.entropy_boundary.value,
            "context_signal_count": len(request.context_signals),
            "snapshot_id": snapshot.snapshot_id,
            "processing_time_ms": round(processing_time * 1000, 2),
        },
    )

    return response


# ============================================================
# SarathiGovernanceOutput — Clean Governance Contract
# ============================================================

from dataclasses import dataclass as _governance_dataclass

@_governance_dataclass(frozen=True)
class SarathiGovernanceOutput:
    """
    The canonical, frozen governance output of Sarathi (Layer 1).

    This is the ONLY output that downstream layers should consume.
    It is framework-independent (no Pydantic dependency), frozen (immutable),
    and contains exactly the fields the BHIV ecosystem needs.

    Fields:
        execution_id : Global execution ID propagated across all layers.
        decision     : ALLOW | DENY | ABSTAIN — the authoritative governance decision.
        confidence   : [0.0, 1.0] — decision confidence, scaled by epistemic state.
        reason       : None on ALLOW. Structured reason string on DENY/ABSTAIN.
        risk_score   : [0.0, 1.0] — the final computed risk score.
        trace_hash   : SHA-256 of all inputs — deterministic replay verification key.
    """
    execution_id: str
    decision: str
    confidence: float
    reason: Optional[str]
    risk_score: float
    trace_hash: str


def govern(request: EvaluateActionRequest) -> SarathiGovernanceOutput:
    """
    The clean governance entry point for Sarathi (Layer 1).

    Returns a frozen, deterministic SarathiGovernanceOutput.
    Internally delegates to evaluate_action() — preserving all existing
    risk scoring, DGIC validation, and decision logic.

    Downstream layers (Core, Enforcement, Bucket, InsightBridge) should
    consume this output — NOT call evaluate_action() directly.
    """
    response = evaluate_action(request)
    return SarathiGovernanceOutput(
        execution_id=response.execution_id,
        decision=response.sarathi_decision.value,
        confidence=response.confidence,
        reason=response.failure_reason,
        risk_score=response.risk_score,
        trace_hash=response.trace_hash,
    )
