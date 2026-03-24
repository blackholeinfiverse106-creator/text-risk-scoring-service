"""
Tests for InsightBridge Rule Weightings
=======================================
Validates the correct calculation of deterministic weighted context risks.
"""

import pytest
from app.enforcement_schemas import ContextSignal
from app.insightbridge_rules import calculate_weighted_signal

# ============================================================
# Helpers
# ============================================================

def _make_signal(signal_type: str, value: float) -> ContextSignal:
    return ContextSignal(
        signal_id="test",
        signal_type=signal_type,
        value=value,
        source="INSIGHTBRIDGE"
    )

class TestCalculateWeightedSignal:
    
    def test_security_alert_weight_is_full(self):
        """Security alerts receive 1.0 multiplier (no reduction)."""
        signal = _make_signal("security_alert", 0.6)
        assert calculate_weighted_signal(signal) == 0.6
        
    def test_policy_violation_weight_is_eighty_percent(self):
        """Policy violations receive 0.8 multiplier."""
        signal = _make_signal("policy_violation", 1.0)
        assert calculate_weighted_signal(signal) == 0.8
        
        signal2 = _make_signal("policy_violation", 0.5)
        assert calculate_weighted_signal(signal2) == 0.4
        
    def test_external_threat_weight_is_seventy_percent(self):
        """External threats receive 0.7 multiplier."""
        signal = _make_signal("external_threat", 1.0)
        assert calculate_weighted_signal(signal) == 0.7
        
        signal2 = _make_signal("external_threat", 0.5)
        assert calculate_weighted_signal(signal2) == 0.35
        
    def test_anomaly_signal_weight_is_fifty_percent(self):
        """Anomaly signals receive 0.5 multiplier."""
        signal = _make_signal("anomaly_signal", 1.0)
        assert calculate_weighted_signal(signal) == 0.5
        
        signal2 = _make_signal("anomaly_signal", 0.8)
        assert calculate_weighted_signal(signal2) == 0.4
        
    def test_unknown_signal_type_is_fail_safe_ten_percent(self):
        """Unrecognized signal types fallback to 0.1 weight."""
        signal = _make_signal("made_up_signal", 1.0)
        assert calculate_weighted_signal(signal) == 0.1
        
        signal2 = _make_signal("custom_sensor", 0.5)
        assert calculate_weighted_signal(signal2) == 0.05
    
    def test_calculation_handles_zero_safely(self):
        signal = _make_signal("security_alert", 0.0)
        assert calculate_weighted_signal(signal) == 0.0
