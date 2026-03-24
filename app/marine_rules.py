"""
Marine Intelligence Rules
=========================
Deterministic mathematical weighting for Marine environmental signals.
Ensures that marine signals systematically influence the enforcement risk score.
"""

from app.enforcement_schemas import ContextSignal

# ============================================================
# Marine Signal Weights
# ============================================================

MARINE_WEIGHTS = {
    "environmental_hazard": 0.85,
    "navigation_warning": 0.6,
    "weather_anomaly": 0.4,
}

UNKNOWN_MARINE_SIGNAL_WEIGHT = 0.1

def calculate_marine_signal(signal: ContextSignal) -> float:
    """
    Apply a deterministic mathematical weight to a Marine context signal.
    """
    return MARINE_WEIGHTS.get(signal.signal_type, UNKNOWN_MARINE_SIGNAL_WEIGHT)
