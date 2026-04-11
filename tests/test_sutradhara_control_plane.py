import pytest

from app.sutradhara_control_plane import (
    invoke_agent,
    verify_agent_capabilities,
    AgentVerificationError,
    ControlPlaneHardFailure,
)
from app.enforcement_schemas import KSMLInput, ContextSignal, DGICEpistemicStateInput

def test_verify_agent_capabilities_enforcement_gate():
    """Phase 7: Ensure enforcement_gate guarantees NO_EXECUTION_RIGHTS."""
    # This should pass without raising an exception
    verify_agent_capabilities("enforcement_gate_v1", "enforcement_gate")

def test_verify_agent_capabilities_missing_agent():
    with pytest.raises(AgentVerificationError, match="not registered in Sūtradhāra"):
        verify_agent_capabilities("unknown_agent", "enforcement_gate")

def test_invoke_agent_requires_ksml_input():
    """Phase 6: Ensure raw dicts fail pydantic validation for KSMLInput mapping."""
    with pytest.raises(ControlPlaneHardFailure, match="NON_KSML_INPUT_DETACHED"):
        # Raw dict passed instead of KSMLInput object
        invoke_agent({"execution_id": "test", "structured_signals": [], "metadata": {}})

def test_invoke_agent_valid_ksml_payload():
    """Phase 6: A valid KSMLInput object should process through invoke_agent."""
    ksml = KSMLInput(
        execution_id="exec-1234567890ab",
        structured_signals=[],
        metadata={
            "actor": "user_123",
            "proposed_action": "delete internal log",
            "source_system": "MARINE_INTELLIGENCE",
            "dgic_epistemic_state": {
                "epistemic_state": "KNOWN",
                "entropy_score": 0.1,
                "contradiction_flag": False,
                "lineage_hash": "a" * 64,
                "envelope_hash": "b" * 64
            }
        }
    )
    
    # Should not raise any KSML validation or agent verification errors.
    # It will hit the mock-less invoke_mandala and should return MandalaInvocationResult.
    result = invoke_agent(ksml)
    
    assert result.execution_id == "exec-1234567890ab"
    # Result decision will be DENY or ALLOW depending on raw ML model result running behind it.
