"""
InsightBridge Deterministic Rules
=================================
Defines strict, deterministic mathematical weighting for InsightBridge telemetry.

InsightBridge signals have different semantic severities.
We apply a static multiplier to the raw signal value to compute a "weighted risk".
This ensures highly critical signals (like security alerts) drive denial
over high-value but lower-severity structural signals (like anomalies).
"""

from typing import Dict
from app.enforcement_schemas import ContextSignal

# ============================================================
# Deterministic Signal Weights
# ============================================================

# Security Alert: Direct, critical impact (e.g., active exploit attempt)
SECURITY_ALERT_WEIGHT = 1.0

# Policy Violation: High impact, definitive breach of rules
POLICY_VIOLATION_WEIGHT = 0.8

# External Threat: Moderate-High impact, contextual threat intelligence
EXTERNAL_THREAT_WEIGHT = 0.7

# Anomaly Signal: Moderate impact, unusual behavior but not definitively malicious
ANOMALY_SIGNAL_WEIGHT = 0.5

# Fail-safe / Unknown: Low impact to prevent unknown signal types from causing
# unjustified immediate denial, while still registering presence.
UNKNOWN_SIGNAL_WEIGHT = 0.1

# Strict mapping of signal_type to its deterministic multiplier
INSIGHTBRIDGE_WEIGHTS: Dict[str, float] = {
    "security_alert": SECURITY_ALERT_WEIGHT,
    "policy_violation": POLICY_VIOLATION_WEIGHT,
    "external_threat": EXTERNAL_THREAT_WEIGHT,
    "anomaly_signal": ANOMALY_SIGNAL_WEIGHT,
}


def calculate_weighted_signal(signal: ContextSignal) -> float:
    """
    Computes the deterministic weighted risk for an InsightBridge context signal.
    
    Formula: raw_value * weight
    Result is guaranteed to be in [0.0, 1.0].
    """
    weight = INSIGHTBRIDGE_WEIGHTS.get(signal.signal_type, UNKNOWN_SIGNAL_WEIGHT)
    
    # Calculate weighted risk and round to 2 decimals for deterministic precision
    weighted_risk = round(signal.value * weight, 2)
    
    # Clamp to [0.0, 1.0] just in case of floating point quirks,
    # though inputs are validated to [0.0, 1.0] and weights are <= 1.0
    return max(0.0, min(1.0, weighted_risk))
