import re
import logging
import uuid
import time
from typing import Dict, Any

# =========================
# Logging Setup (STEP 3.1)
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

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
def error_response(code: str, message: str, correlation_id: str = None) -> Dict[str, Any]:
    if correlation_id:
        logger.error("Error response generated | correlation_id=%s | code=%s | message=%s", correlation_id, code, message)
    else:
        logger.error("Error response generated | code=%s | message=%s", code, message)
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
def analyze_text(text: str) -> Dict[str, Any]:
    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info("Request started | correlation_id=%s", correlation_id)
    
    try:
        # =========================
        # F-02: INVALID TYPE
        # =========================
        if not isinstance(text, str):
            return error_response("INVALID_TYPE", "Input must be a string", correlation_id)

        logger.info("Received text for analysis | correlation_id=%s | raw_length=%d", correlation_id, len(text))

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
                "Input truncated | correlation_id=%s | original_length=%d | max_length=%d",
                correlation_id, len(text), MAX_TEXT_LENGTH
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
        for category, keywords in RISK_KEYWORDS.items():
            category_score = 0.0

            for keyword in keywords:
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, text):
                    logger.info(
                        "Keyword detected | correlation_id=%s | category=%s | keyword=%s",
                        correlation_id, category, keyword
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
                    "Category score capped | correlation_id=%s | category=%s | raw_score=%.2f | cap=%.2f",
                    correlation_id, category, category_score, MAX_CATEGORY_SCORE
                )
                category_score = MAX_CATEGORY_SCORE

            total_score += category_score

        # =========================
        # F-06: SCORE CLAMPING
        # =========================
        if total_score > 1.0:
            logger.warning(
                "Total score clamped | correlation_id=%s | raw_score=%.2f | cap=1.0",
                correlation_id, total_score
            )
            total_score = 1.0

        # =========================
        # RISK THRESHOLDS
        # =========================
        if total_score < 0.3:
            risk_category = "LOW"
        elif total_score < 0.7:
            risk_category = "MEDIUM"
        else:
            risk_category = "HIGH"

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
            "Final decision | correlation_id=%s | score=%.2f | confidence=%.2f | category=%s | processing_time=%.3fms",
            correlation_id, total_score, confidence, risk_category, processing_time * 1000
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
            "Unexpected runtime error during text analysis | correlation_id=%s",
            correlation_id,
            exc_info=True
        )
        return error_response(
            "INTERNAL_ERROR",
            "Unexpected processing error",
            correlation_id
        )

