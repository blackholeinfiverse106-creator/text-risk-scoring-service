from __future__ import annotations

import re
import logging
import time
from typing import Dict, Any, List
from dataclasses import dataclass

from app.enforcement_schemas import ContextSignal, SourceSystem
from app.insightbridge_rules import calculate_weighted_signal
from app.marine_rules import calculate_marine_signal
from app.aiaic_rules import calculate_aiaic_signal
from app.c4s_rules import calculate_c4s_signal
from app.layer3_dgic import apply_dgic_modifiers, DGICAdapterResult

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 5000
KEYWORD_WEIGHT = 0.2
MAX_CATEGORY_SCORE = 0.6  # Prevents saturation from one category

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

@dataclass
class IntelligencePayload:
    text_risk: float
    context_risk: float
    confidence: float
    final_risk: float
    trigger_reasons: List[str]
    processing_time_ms: float

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

def analyze_text(text: str, execution_id: str = "UNKNOWN") -> Dict[str, Any]:
    try:
        start_time = time.time()

        logger.info("Request started", extra={"execution_id": execution_id, "event_type": "analysis_start"})

        if not isinstance(text, str):
            logger.error(f"Error response generated: INVALID_TYPE", extra={"execution_id": execution_id, "event_type": "error_response_generated", "details": {"code": "INVALID_TYPE", "message": "Input must be a string"}})
            return {"risk_score": 0.0, "confidence_score": 0.0, "risk_category": "LOW", "trigger_reasons": [], "processed_length": 0, "safety_metadata": {"is_decision": False, "authority": "NONE", "actionable": False}, "errors": {"error_code": "INVALID_TYPE", "message": "Input must be a string"}}

        logger.info(f"Received text for analysis | len={len(text)}", extra={"execution_id": execution_id, "event_type": "input_received", "details": {"raw_length": len(text)}})

        text = text.strip().lower()
        if not text:
            logger.error(f"Error response generated: EMPTY_INPUT", extra={"execution_id": execution_id, "event_type": "error_response_generated", "details": {"code": "EMPTY_INPUT", "message": "Text is empty"}})
            return {"risk_score": 0.0, "confidence_score": 0.0, "risk_category": "LOW", "trigger_reasons": [], "processed_length": 0, "safety_metadata": {"is_decision": False, "authority": "NONE", "actionable": False}, "errors": {"error_code": "EMPTY_INPUT", "message": "Text is empty"}}

        truncated = False
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning("Input truncated", extra={"execution_id": execution_id, "event_type": "input_truncated", "details": {"original_length": len(text), "max_length": MAX_TEXT_LENGTH}})
            text = text[:MAX_TEXT_LENGTH]
            truncated = True

        total_score = 0.0
        reasons = []
        keyword_count = 0
        matched_categories = set()

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

            if category_score > MAX_CATEGORY_SCORE:
                logger.warning(
                    f"Category score capped for {category}",
                    extra={"execution_id": execution_id, "event_type": "category_capped", "details": {"category": category, "raw_score": category_score, "cap": MAX_CATEGORY_SCORE}}
                )
                category_score = MAX_CATEGORY_SCORE
            total_score += category_score

        if total_score > 1.0:
            logger.warning("Total score clamped", extra={"execution_id": execution_id, "event_type": "score_clamped", "details": {"raw_score": total_score, "cap": 1.0}})
            total_score = 1.0

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
        if truncated:
            reasons.append("Input text was truncated to safe maximum length")

        if total_score < 0.3:
            risk_category = "LOW"
        elif 0.3 <= total_score < 0.7:
            risk_category = "MEDIUM"
        else:
            risk_category = "HIGH"

        # Invariant checks
        if total_score >= 0.7 and risk_category != "HIGH":
            logger.error("Invariant violation detected", extra={"execution_id": execution_id, "event_type": "invariant_correction", "details": {"score": total_score, "category": risk_category, "correction": "HIGH"}})
            risk_category = "HIGH"
        if total_score < 0.3 and risk_category == "HIGH":
            logger.error("Invariant violation detected", extra={"execution_id": execution_id, "event_type": "invariant_correction", "details": {"score": total_score, "category": "HIGH", "correction": "LOW"}})
            risk_category = "LOW"

        processing_time = time.time() - start_time
        logger.info(
            f"Final decision: {risk_category}",
            extra={"execution_id": execution_id, "event_type": "analysis_complete", "details": {"score": total_score, "confidence": confidence, "category": risk_category, "processing_time_ms": processing_time * 1000}}
        )

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

    except Exception:
        logger.error(
            "Unexpected runtime error during text analysis",
            exc_info=True,
            extra={"execution_id": execution_id, "event_type": "unhandled_exception"}
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
                "error_code": "INTERNAL_ERROR",
                "message": "Unexpected processing error"
            }
        }

def aggregate_context_signals(context_signals: List[ContextSignal]) -> float:
    if not context_signals:
        return 0.0

    weighted_values = []
    for signal in context_signals:
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
            weighted_values.append(signal.value)

    return max(weighted_values)

def compute_intelligence(
    proposed_action: str, 
    context_signals: List[ContextSignal],
    adapter_result: DGICAdapterResult,
    execution_id: str
) -> IntelligencePayload:
    start_time = time.time()
    
    # 1. Base Text Risk
    base_result = analyze_text(proposed_action, execution_id)
    
    # 2. Epistemic Modifiers
    modified_result = apply_dgic_modifiers(base_result, adapter_result=adapter_result)
    text_risk = modified_result["risk_score"]
    confidence = modified_result["confidence_score"]
    
    # 3. Contextual Signals Risk
    context_risk = aggregate_context_signals(context_signals)
    
    # 4. Final Aggregation (Max)
    final_risk = round(max(text_risk, context_risk), 2)
    final_risk = max(0.0, min(1.0, final_risk))
    
    processing_time_ms = (time.time() - start_time) * 1000
    
    return IntelligencePayload(
        text_risk=text_risk,
        context_risk=context_risk,
        confidence=confidence,
        final_risk=final_risk,
        trigger_reasons=base_result.get("trigger_reasons", []),
        processing_time_ms=processing_time_ms
    )
