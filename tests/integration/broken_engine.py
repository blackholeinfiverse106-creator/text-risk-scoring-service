#!/usr/bin/env python3
"""
determinism_failure_sim/broken_engine.py
=========================================
SIMULATION ONLY — NOT FOR PRODUCTION USE.

A deliberately broken version of app/engine.py.
Injects controlled non-determinism via random.random() added to risk_score.
Used to prove that replay_harness.py has TRUE detection sensitivity.
"""

import re
import logging
import time
import random
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 5000
KEYWORD_WEIGHT = 0.2
MAX_CATEGORY_SCORE = 0.6

RISK_KEYWORDS = {
    "violence": ["kill", "murder", "attack", "bomb", "assault", "shoot"],
    "fraud":    ["scam", "fraud", "hack", "phish", "fake", "forgery"],
    "abuse":    ["idiot", "stupid", "hate", "trash"],
    "threat":   ["threat", "threaten", "intimidate", "coerce"],
}

def error_response(code: str, message: str) -> Dict[str, Any]:
    return {
        "risk_score": 0.0,
        "confidence_score": 0.0,
        "risk_category": "LOW",
        "trigger_reasons": [],
        "processed_length": 0,
        "safety_metadata": {"is_decision": False, "authority": "NONE", "actionable": False},
        "errors": {"error_code": code, "message": message},
    }

def analyze_text(text: str, correlation_id: str = "UNKNOWN") -> Dict[str, Any]:
    """
    BROKEN VERSION: Adds a small random float to risk_score.
    This simulates a hidden non-deterministic state leak.
    """
    try:
        if not isinstance(text, str):
            return error_response("INVALID_TYPE", "Input must be a string")

        text = text.strip().lower()

        if not text:
            return error_response("EMPTY_INPUT", "Text is empty")

        truncated = False
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
            truncated = True

        total_score = 0.0
        reasons = []
        matched_keywords = []
        matched_categories = set()

        for category, keywords in sorted(RISK_KEYWORDS.items()):
            category_score = 0.0
            for keyword in keywords:
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, text):
                    category_score += KEYWORD_WEIGHT
                    matched_keywords.append(keyword)
                    matched_categories.add(category)
                    reasons.append(f"Detected {category} keyword: {keyword}")

            if category_score > MAX_CATEGORY_SCORE:
                category_score = MAX_CATEGORY_SCORE
            total_score += category_score

        # ─────────────────────────────────────────────────────────
        # ☣  INJECTED NON-DETERMINISM — THIS IS THE BUG
        # ─────────────────────────────────────────────────────────
        # Adds noise that is guaranteed to exceed round(..., 2) absorption.
        # 0.001 would be absorbed by round; 0.1 will always flip the hash.
        noise = random.uniform(0.05, 0.1)   # Always > 2nd decimal place
        total_score += noise
        # ─────────────────────────────────────────────────────────

        if total_score > 1.0:
            total_score = 1.0

        if total_score < 0.3:
            risk_category = "LOW"
        elif 0.3 <= total_score < 0.7:
            risk_category = "MEDIUM"
        else:
            risk_category = "HIGH"

        confidence = 1.0
        kw_count = len(matched_keywords)
        if kw_count == 0:
            confidence = 1.0
        else:
            if kw_count == 1:
                confidence -= 0.3
            if len(matched_categories) > 1:
                confidence -= 0.2
            if kw_count <= 2:
                confidence -= 0.2
        confidence = max(0.0, min(confidence, 1.0))

        if truncated:
            reasons.append("Input text was truncated to safe maximum length")

        return {
            "risk_score":       round(total_score, 2),
            "confidence_score": round(confidence, 2),
            "risk_category":    risk_category,
            "trigger_reasons":  reasons,
            "processed_length": len(text),
            "safety_metadata":  {"is_decision": False, "authority": "NONE", "actionable": False},
            "errors":           None,
        }

    except Exception:
        return error_response("INTERNAL_ERROR", "Unexpected error")
