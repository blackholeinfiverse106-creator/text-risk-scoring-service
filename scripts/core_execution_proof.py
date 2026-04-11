import sys
import os
import logging
from unittest.mock import patch
from app.sutradhara_control_plane import invoke_mandala, MandalaInvocationResult
from app.enforcement_schemas import (
    SourceSystem,
    DGICEpistemicStateInput,
    ContextSignal,
)
from tests.test_core_execution_gate import _make_dgic_state

logging.basicConfig(level=logging.ERROR)

def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f" {title} ".center(60, '='))
    print(f"{'='*60}\n")

def print_result(result: MandalaInvocationResult, executed: bool):
    print(f"  Result : {result.enforcement_decision.value}")
    if executed:
        print(f"  Actions: [EXECUTE_ACTION] triggered")
    else:
        print(f"  Actions: [BLOCK_EXECUTION] triggered")
    if result.failure_reason:
        print(f"  Reason : {result.failure_reason}")
    print()

def main():
    print_separator("REAL EXECUTION PROOF")

    # Mock bucket write globally for clean output
    patch("app.layer4_core.write_execution_record").start()

    # Case 1: ALLOW
    print("--- CASE 1: ALLOW ---")
    with patch("app.layer4_core.execute_action") as mock_exec:
        result = invoke_mandala(
            execution_id="auth-001",
            actor="sys-admin",
            proposed_action="Generate standard dashboard report",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.C4S,
        )
        print_result(result, executed=mock_exec.called)

    # Case 2: DENY
    print("--- CASE 2: DENY ---")
    with patch("app.layer4_core.block_execution") as mock_block:
        result = invoke_mandala(
            execution_id="auth-002",
            actor="sys-admin",
            proposed_action="explode the headquarters",
            context_signals=[
                ContextSignal(signal_id="threat-1", signal_type="security_alert", value=0.99, source="insightbridge")
            ],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.SOVEREIGN_CORE,
        )
        print_result(result, executed=not mock_block.called)

    # Case 3: ABSTAIN
    print("--- CASE 3: ABSTAIN ---")
    with patch("app.layer4_core.block_execution") as mock_block:
        # Pass an UNKNOWN state to trigger ABSTAIN
        result = invoke_mandala(
            execution_id="auth-003",
            actor="sys-admin",
            proposed_action="Execute diagnostic tool",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(epistemic_state="UNKNOWN", entropy_score=0.0),
            source_system=SourceSystem.MARINE_INTELLIGENCE,
        )
        print_result(result, executed=not mock_block.called)


    print_separator("FAILURE CASES (CORE GUARDS)")

    # Failure 1: Enforcement decision missing
    print("--- FAILURE CASE 1: Enforcement decision missing ---")
    with patch("app.layer4_core.enforce", return_value={"execution_id": "fail-1", "confidence": 0.0}):
        result = invoke_mandala(
            execution_id="fail-001",
            actor="user",
            proposed_action="action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        print("  JSON Output:")
        print(result.model_dump_json(indent=2))
        print()

    # Failure 2: execution_id mismatch
    print("--- FAILURE CASE 2: execution_id mismatch ---")
    with patch("app.layer4_core.sarathi_evaluate") as mock_sarathi:
        # Mock sarathi returning a different execution_id
        class FakeResponse:
            execution_id = "WRONG_ID"
            sarathi_decision = type("Enum", (), {"value": "ALLOW"})
            confidence = 0.9
            trace_hash = "a" * 64
            failure_reason = None
            risk_score = 0.1
        mock_sarathi.return_value = FakeResponse()
        result = invoke_mandala(
            execution_id="fail-002",
            actor="user",
            proposed_action="action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        print("  JSON Output:")
        print(result.model_dump_json(indent=2))
        print()

    # Failure 3: Invalid enforcement output
    print("--- FAILURE CASE 3: Invalid enforcement output ---")
    with patch("app.layer4_core.enforce", return_value="INVALID_STRING_OUTPUT"):
        result = invoke_mandala(
            execution_id="fail-003",
            actor="user",
            proposed_action="action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        print("  JSON Output:")
        print(result.model_dump_json(indent=2))
        print()

    # Failure 4: Sarathi missing
    print("--- FAILURE CASE 4: Sarathi missing ---")
    with patch("app.layer4_core.sarathi_evaluate", return_value=None):
        result = invoke_mandala(
            execution_id="fail-004",
            actor="user",
            proposed_action="action",
            context_signals=[],
            dgic_epistemic_state=_make_dgic_state(),
            source_system=SourceSystem.AI_BEING,
        )
        print("  JSON Output:")
        print(result.model_dump_json(indent=2))
        print()

if __name__ == "__main__":
    main()
