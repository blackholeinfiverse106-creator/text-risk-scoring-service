"""
AIAIC Agricultural Intelligence Rules
====================================
Deterministic mathematical weighting for AIAIC biosphere and agricultural signals.
Ensures that agricultural recommendations systematically influence the enforcement risk score.
"""

from app.enforcement_schemas import ContextSignal

# ============================================================
# AIAIC Signal Weights
# ============================================================

AIAIC_WEIGHTS = {
    "biosphere_critical": 0.9,
    "crop_failure_risk": 0.7,
    "soil_anomaly": 0.3,
}

UNKNOWN_AIAIC_SIGNAL_WEIGHT = 0.1

def calculate_aiaic_signal(signal: ContextSignal) -> float:
    """
    Apply a deterministic mathematical weight to an AIAIC context signal.
    """
    return AIAIC_WEIGHTS.get(signal.signal_type, UNKNOWN_AIAIC_SIGNAL_WEIGHT)
