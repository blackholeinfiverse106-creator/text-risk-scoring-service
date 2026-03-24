"""
C4S Strategic Simulation Rules
==============================
Deterministic mathematical weighting for C4S (Brigadier-level Strategic Simulation) actions.
Ensures that simulated geopolitical intelligence recommendations systematically influence enforcement.
"""

from app.enforcement_schemas import ContextSignal

# ============================================================
# C4S Signal Weights
# ============================================================

C4S_WEIGHTS = {
    "geopolitical_escalation": 0.95,
    "border_anomaly": 0.75,
    "strategic_recommendation": 0.5,
}

UNKNOWN_C4S_SIGNAL_WEIGHT = 0.1

def calculate_c4s_signal(signal: ContextSignal) -> float:
    """
    Apply a deterministic mathematical weight to a C4S context signal.
    """
    return C4S_WEIGHTS.get(signal.signal_type, UNKNOWN_C4S_SIGNAL_WEIGHT)
