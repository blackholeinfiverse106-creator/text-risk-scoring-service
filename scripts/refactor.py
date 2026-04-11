import os
import re

def write_intelligence():
    content = """from __future__ import annotations

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
    "violence": ["kill", "killing", "murder", "attack", "assault"],
    "fraud": ["scam", "fraud", "hack", "phish", "identity theft"],
    "abuse": ["idiot", "stupid", "moron", "hate", "harass"],
    "sexual": ["sex", "porn", "nude", "explicit", "adult content"],
    "drugs": ["drug", "heroin", "meth", "weed", "overdose"],
    "extremism": ["terrorism", "extremist", "radicalize"],
    "self_harm": ["suicide", "self harm", "cut myself", "want to die"],
    "cybercrime": ["ddos", "malware", "ransomware", "virus", "trojan"],
    "weapons": ["gun", "firearm", "explosive", "bomb", "knife"],
    "threats": ["i will kill you", "i will hurt you", "threaten"]
}

@dataclass
class IntelligencePayload:
    text_risk: float
    context_risk: float
    confidence: float
    final_risk: float
    trigger_reasons: List[str]
    processing_time_ms: float

def analyze_text(text: str, execution_id: str = "UNKNOWN") -> Dict[str, Any]:
    start_time = time.time()
    
    if not isinstance(text, str):
        return {"risk_score": 0.0, "confidence_score": 0.0, "trigger_reasons": ["INVALID_TYPE"]}
    
    text = text.strip().lower()
    if not text:
        return {"risk_score": 0.0, "confidence_score": 0.0, "trigger_reasons": ["EMPTY_INPUT"]}
        
    truncated = False
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
        truncated = True

    total_score = 0.0
    reasons = []
    keyword_count = 0
    matched_categories = set()

    for category, keywords in sorted(RISK_KEYWORDS.items()):
        category_score = 0.0
        for keyword in keywords:
            pattern = r"\\b" + re.escape(keyword) + r"\\b"
            if re.search(pattern, text):
                category_score += KEYWORD_WEIGHT
                keyword_count += 1
                matched_categories.add(category)
                reasons.append(f"Detected {category} keyword: {keyword}")

        if category_score > MAX_CATEGORY_SCORE:
            category_score = MAX_CATEGORY_SCORE
        total_score += category_score

    if total_score > 1.0:
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

    return {
        "risk_score": round(total_score, 2),
        "confidence_score": round(confidence, 2),
        "trigger_reasons": reasons
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
"""
    with open('app/layer0_intelligence.py', 'w', encoding='utf-8') as f:
        f.write(content)

write_intelligence()
print("Wrote app/layer0_intelligence.py")
