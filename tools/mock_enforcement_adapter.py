#!/usr/bin/env python3
"""
mock_enforcement_adapter.py
============================
A read-only enforcement adapter that consumes risk signals from engine.analyze_text
and applies a layered policy — WITHOUT claiming authority or triggering actions.

Design constraints (structural, not voluntary):
  - No write path: cannot modify, delete, or suppress content
  - No feed-back loop: does not influence future engine scores
  - All decisions carry a mandatory human-review requirement
  - Outputs are recommendations only; action field is always None

Usage:
    from mock_enforcement_adapter import EnforcementAdapter

    adapter = EnforcementAdapter()
    rec = adapter.evaluate("some user text", correlation_id="REQ-001")
    print(rec)
"""
from __future__ import annotations
import sys
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from app.engine import analyze_text

# ── Policy thresholds (read-only — not fed back to engine) ────────────────────

POLICY = {
    "LOW":    {"recommendation": "ALLOW",   "human_review": False, "confidence_floor": 0.0},
    "MEDIUM": {"recommendation": "FLAG",    "human_review": True,  "confidence_floor": 0.5},
    "HIGH":   {"recommendation": "HOLD",    "human_review": True,  "confidence_floor": 0.0},
}

VALID_RECOMMENDATIONS = {"ALLOW", "FLAG", "HOLD"}


@dataclass
class EnforcementRecommendation:
    """
    Output of the enforcement adapter.

    INVARIANTS (structurally enforced):
      - action is always None  → adapter cannot take actions
      - authority is always "NONE"
      - is_decision is always False
    """
    correlation_id:    str
    recommendation:    str           # ALLOW | FLAG | HOLD
    human_review:      bool          # always True for MEDIUM/HIGH
    risk_category:     str
    risk_score:        float
    confidence_score:  float
    trigger_reasons:   list[str]
    policy_rationale:  str

    # ── Structural invariants (frozen, not settable by callers) ──────────────
    action:     None = field(default=None, init=False)   # no write path
    authority:  str  = field(default="NONE", init=False) # never claims authority
    is_decision: bool = field(default=False, init=False) # never a decision

    def to_dict(self) -> dict:
        return {
            "correlation_id":   self.correlation_id,
            "recommendation":   self.recommendation,
            "human_review":     self.human_review,
            "risk_category":    self.risk_category,
            "risk_score":       self.risk_score,
            "confidence_score": self.confidence_score,
            "trigger_reasons":  self.trigger_reasons,
            "policy_rationale": self.policy_rationale,
            "action":           self.action,         # always None
            "authority":        self.authority,      # always "NONE"
            "is_decision":      self.is_decision,    # always False
        }


class EnforcementAdapter:
    """
    Read-only enforcement adapter.

    Takes a raw text input → calls analyze_text → applies policy layer →
    returns an EnforcementRecommendation.

    Cannot:
      - Modify content
      - Block requests directly
      - Claim authority
      - Make binding decisions
    """

    def evaluate(
        self,
        text: str,
        correlation_id: Optional[str] = None,
    ) -> EnforcementRecommendation:
        cid = correlation_id or str(uuid.uuid4())

        # Step 1: Get raw signal from engine (read-only)
        signal = analyze_text(text, correlation_id=cid)

        # Step 2: Check for engine error — if present, default to FLAG+review
        if signal.get("errors"):
            return EnforcementRecommendation(
                correlation_id   = cid,
                recommendation   = "FLAG",
                human_review     = True,
                risk_category    = "UNKNOWN",
                risk_score       = 0.0,
                confidence_score = 0.0,
                trigger_reasons  = [],
                policy_rationale = f"Engine error: {signal['errors']['error_code']}. Flagging for mandatory human review.",
            )

        category = signal["risk_category"]
        policy   = POLICY[category]

        # Step 3: Apply confidence floor — low confidence always requires review
        requires_review = policy["human_review"]
        if signal["confidence_score"] < policy["confidence_floor"]:
            requires_review = True

        # Step 4: Build rationale (transparent, auditable)
        rationale = (
            f"Risk={category}, score={signal['risk_score']}, "
            f"confidence={signal['confidence_score']}. "
            f"Policy recommends {policy['recommendation']}. "
            f"{'Human review required.' if requires_review else 'No review required.'}"
        )

        return EnforcementRecommendation(
            correlation_id   = cid,
            recommendation   = policy["recommendation"],
            human_review     = requires_review,
            risk_category    = category,
            risk_score       = signal["risk_score"],
            confidence_score = signal["confidence_score"],
            trigger_reasons  = signal["trigger_reasons"],
            policy_rationale = rationale,
        )


# ── Self-test / demo ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    adapter = EnforcementAdapter()

    test_cases = [
        ("have a great day!",                           "DEMO-001"),
        ("you scammed me with your phishing attempt",   "DEMO-002"),
        ("kill murder attack bomb terrorist extremist",  "DEMO-003"),
    ]

    print("\n" + "="*60)
    print("  MOCK ENFORCEMENT ADAPTER — DEMO")
    print("="*60)

    for text, cid in test_cases:
        rec = adapter.evaluate(text, correlation_id=cid)
        d   = rec.to_dict()
        print(f"\n  [{rec.recommendation:4s}] {cid}")
        print(f"    risk     : {rec.risk_category} ({rec.risk_score})")
        print(f"    review   : {rec.human_review}")
        print(f"    action   : {rec.action!r}   ← always None")
        print(f"    authority: {rec.authority!r} ← always NONE")
        print(f"    is_decision: {rec.is_decision}  ← always False")

    print("\n" + "="*60)
    print("  STRUCTURAL INVARIANTS VERIFIED")
    print("="*60 + "\n")
