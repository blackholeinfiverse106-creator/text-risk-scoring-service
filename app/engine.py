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
def error_response(code: str, message: str, correlation_id: str = "UNKNOWN") -> Dict[str, Any]:
    logger.error(
        f"Error response generated: {code}",
        extra={"correlation_id": correlation_id, "event_type": "error_response_generated", "details": {"code": code, "message": message}}
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
def analyze_text(text: str, correlation_id: str = "UNKNOWN") -> Dict[str, Any]:
    try:
        start_time = time.time()
        
        logger.info("Request started", extra={"correlation_id": correlation_id, "event_type": "analysis_start"})
        # =========================
        # F-02: INVALID TYPE
        # =========================
        if not isinstance(text, str):
            return error_response("INVALID_TYPE", "Input must be a string", correlation_id)

        logger.info(f"Received text for analysis | len={len(text)}", extra={"correlation_id": correlation_id, "event_type": "input_received", "details": {"raw_length": len(text)}})

        # Normalize input
        text = text.strip().lower()

        # =========================
        # F-01: EMPTY INPUT
        # =========================
        if not text:
            return error_response("EMPTY_INPUT", "Text is empty", correlation_id)

        # =========================
        # F-03: EXCESSIVE LENGTH
        # =========================
        truncated = False
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(
                "Input truncated",
                extra={"correlation_id": correlation_id, "event_type": "input_truncated", "details": {"original_length": len(text), "max_length": MAX_TEXT_LENGTH}}
            )
            text = text[:MAX_TEXT_LENGTH]
            truncated = True

        total_score = 0.0
        reasons = []

        matched_keywords = []
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
                        extra={"correlation_id": correlation_id, "event_type": "keyword_detected", "details": {"category": category, "keyword": keyword}}
                    )
                    category_score += KEYWORD_WEIGHT
                    matched_keywords.append(keyword)
                    matched_categories.add(category)
                    reasons.append(f"Detected {category} keyword: {keyword}")

            # =========================
            # F-04: CATEGORY SATURATION
            # =========================
            if category_score > MAX_CATEGORY_SCORE:
                logger.warning(
                    f"Category score capped for {category}",
                    extra={"correlation_id": correlation_id, "event_type": "category_capped", "details": {"category": category, "raw_score": category_score, "cap": MAX_CATEGORY_SCORE}}
                )
                category_score = MAX_CATEGORY_SCORE

            total_score += category_score

        # =========================
        # F-06: SCORE CLAMPING
        # =========================
        if total_score > 1.0:
            logger.warning(
                "Total score clamped",
                extra={"correlation_id": correlation_id, "event_type": "score_clamped", "details": {"raw_score": total_score, "cap": 1.0}}
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
        # INVARIANT ENFORCEMENT (FAIL-SAFE)
        # =========================
        # F-02: Score/Category Mismatch Prevention
        if total_score >= 0.7 and risk_category != "HIGH":
             logger.error("Invariant violation detected", extra={"correlation_id": correlation_id, "event_type": "invariant_correction", "details": {"score": total_score, "category": risk_category, "correction": "HIGH"}})
             risk_category = "HIGH"
        
        if total_score < 0.3 and risk_category == "HIGH":
             logger.error("Invariant violation detected", extra={"correlation_id": correlation_id, "event_type": "invariant_correction", "details": {"score": total_score, "category": "HIGH", "correction": "LOW"}})
             risk_category = "LOW"

        # =========================
        # CONFIDENCE LOGIC (TASK 3 - DAY 2)
        # =========================
        confidence = 1.0
        keyword_count = len(matched_keywords)
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
            extra={"correlation_id": correlation_id, "event_type": "analysis_complete", "details": {"score": total_score, "confidence": confidence, "category": risk_category, "processing_time_ms": processing_time * 1000}}
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
            extra={"correlation_id": correlation_id, "event_type": "unhandled_exception"}
        )
        return error_response(
            "INTERNAL_ERROR",
            "Unexpected processing error",
            correlation_id
        )

