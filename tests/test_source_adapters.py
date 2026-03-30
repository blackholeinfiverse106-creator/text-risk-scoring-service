"""
Tests for Source Adapters
=========================
Validates deterministic mathematical weighting for Marine, AIAIC, and C4S signals.
Verifies that these systems can successfully pass through the enforcement gate 
and core execution pipeline.
"""

import pytest

from app.enforcement_schemas import ContextSignal, SourceSystem, EvaluateActionRequest
from app.marine_rules import calculate_marine_signal
from app.aiaic_rules import calculate_aiaic_signal
from app.c4s_rules import calculate_c4s_signal
from app.sarathi_governance import aggregate_context_signals


# ============================================================
# Marine Intelligence Tests
# ============================================================

class TestMarineAdapter:
    def test_marine_environmental_hazard(self):
        signal = ContextSignal(
            signal_id="m-1",
            source=SourceSystem.MARINE_INTELLIGENCE.value,
            signal_type="environmental_hazard",
            value=1.0,  # Value is ignored by the adapter, type determines weight
        )
        assert calculate_marine_signal(signal) == 0.85

    def test_marine_navigation_warning(self):
        signal = ContextSignal(
            signal_id="m-2",
            source=SourceSystem.MARINE_INTELLIGENCE.value,
            signal_type="navigation_warning",
            value=1.0,
        )
        assert calculate_marine_signal(signal) == 0.6

    def test_marine_weather_anomaly(self):
        signal = ContextSignal(
            signal_id="m-3",
            source=SourceSystem.MARINE_INTELLIGENCE.value,
            signal_type="weather_anomaly",
            value=1.0,
        )
        assert calculate_marine_signal(signal) == 0.4

    def test_marine_unknown_signal(self):
        signal = ContextSignal(
            signal_id="m-4",
            source=SourceSystem.MARINE_INTELLIGENCE.value,
            signal_type="alien_fish_spotted",
            value=1.0,
        )
        assert calculate_marine_signal(signal) == 0.1


# ============================================================
# AIAIC Agricultural Intelligence Tests
# ============================================================

class TestAIAICAdapter:
    def test_aiaic_biosphere_critical(self):
        signal = ContextSignal(
            signal_id="a-1",
            source=SourceSystem.AIAIC.value,
            signal_type="biosphere_critical",
            value=1.0,
        )
        assert calculate_aiaic_signal(signal) == 0.9

    def test_aiaic_crop_failure_risk(self):
        signal = ContextSignal(
            signal_id="a-2",
            source=SourceSystem.AIAIC.value,
            signal_type="crop_failure_risk",
            value=1.0,
        )
        assert calculate_aiaic_signal(signal) == 0.7

    def test_aiaic_soil_anomaly(self):
        signal = ContextSignal(
            signal_id="a-3",
            source=SourceSystem.AIAIC.value,
            signal_type="soil_anomaly",
            value=1.0,
        )
        assert calculate_aiaic_signal(signal) == 0.3

    def test_aiaic_unknown_signal(self):
        signal = ContextSignal(
            signal_id="a-4",
            source=SourceSystem.AIAIC.value,
            signal_type="too_many_cows",
            value=1.0,
        )
        assert calculate_aiaic_signal(signal) == 0.1


# ============================================================
# C4S Strategic Simulation Tests
# ============================================================

class TestC4SAdapter:
    def test_c4s_geopolitical_escalation(self):
        signal = ContextSignal(
            signal_id="c-1",
            source=SourceSystem.C4S.value,
            signal_type="geopolitical_escalation",
            value=1.0,
        )
        assert calculate_c4s_signal(signal) == 0.95

    def test_c4s_border_anomaly(self):
        signal = ContextSignal(
            signal_id="c-2",
            source=SourceSystem.C4S.value,
            signal_type="border_anomaly",
            value=1.0,
        )
        assert calculate_c4s_signal(signal) == 0.75

    def test_c4s_strategic_recommendation(self):
        signal = ContextSignal(
            signal_id="c-3",
            source=SourceSystem.C4S.value,
            signal_type="strategic_recommendation",
            value=1.0,
        )
        assert calculate_c4s_signal(signal) == 0.5

    def test_c4s_unknown_signal(self):
        signal = ContextSignal(
            signal_id="c-4",
            source=SourceSystem.C4S.value,
            signal_type="general_wants_coffee",
            value=1.0,
        )
        assert calculate_c4s_signal(signal) == 0.1


# ============================================================
# Enforcement Gate Aggregation Tests
# ============================================================

class TestGateAggregation:
    def test_aggregate_max_fail_high_routing(self):
        """Verify the gate correctly routes to adapters and uses max() fail-high strategy."""
        
        # Geopolitical escalation = 0.95
        c4s_signal = ContextSignal(
            signal_id="agg-1",
            source=SourceSystem.C4S.value,
            signal_type="geopolitical_escalation",
            value=1.0,
        )
        
        # Weather anomaly = 0.4
        marine_signal = ContextSignal(
            signal_id="agg-2",
            source=SourceSystem.MARINE_INTELLIGENCE.value,
            signal_type="weather_anomaly",
            value=1.0,
        )
        
        # Unknown signal = 0.1
        aiaic_signal = ContextSignal(
            signal_id="agg-3",
            source=SourceSystem.AIAIC.value,
            signal_type="unknown",
            value=1.0,
        )

        from app.enforcement_schemas import DGICEpistemicStateInput
        # Create a dummy request just to test the signal aggregation
        request = EvaluateActionRequest(
            execution_id="test",
            actor="test",
            proposed_action="test",
            context_signals=[c4s_signal, marine_signal, aiaic_signal],
            dgic_epistemic_state=DGICEpistemicStateInput(
                epistemic_state="KNOWN",
                entropy_score=0.1,
                contradiction_flag=False,
                lineage_hash="d" * 64,
                envelope_hash="d" * 64
            ),
            source_system=SourceSystem.C4S
        )

        # The maximum value out of 0.95, 0.4, 0.1 should be 0.95
        max_signal = aggregate_context_signals(request)
        assert max_signal == 0.95

    def test_aggregate_unknown_source_fallback(self):
        """Test a signal from an unknown/unmapped source system defaults to raw value multiplier."""
        raw_signal = ContextSignal(
            signal_id="agg-4",
            source="SOME_EXTERNAL_SYSTEM",
            signal_type="unknown",
            value=0.6,
        )
        
        from app.enforcement_schemas import DGICEpistemicStateInput
        request = EvaluateActionRequest(
            execution_id="test",
            actor="test",
            proposed_action="test",
            context_signals=[raw_signal],
            dgic_epistemic_state=DGICEpistemicStateInput(
                epistemic_state="KNOWN",
                entropy_score=0.1,
                contradiction_flag=False,
                lineage_hash="d" * 64,
                envelope_hash="d" * 64
            ),
            source_system=SourceSystem.C4S
        )

        # Unknown source should just return the raw `value` (0.6)
        max_signal = aggregate_context_signals(request)
        assert max_signal == 0.6
