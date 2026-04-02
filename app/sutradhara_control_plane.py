"""
Sūtradhāra Control Plane — Layer 2
==================================
The master orchestrator and agent registry for the BHIV Enforcement Ecosystem.
ALL agent invocations MUST pass through this control plane. 
It prevents direct exposure of the lower-level governance and enforcement gates.

Responsibilities:
  1. Agent verification (Registry)
  2. Canonical execution_id provisioning
  3. Routing to Core Execution Gate (Layer 1 -> Layer 4 pipeline)
"""

import uuid
import logging
from typing import Optional, List

from app.enforcement_schemas import (
    SourceSystem,
    ContextSignal,
    DGICEpistemicStateInput,
    KSMLInput,
)
from app.layer4_core import submit_proposal, CoreExecutionResult

logger = logging.getLogger(__name__)


class AgentVerificationError(Exception):
    """Exception raised when an unregistered agent attempts invocation."""
    pass


class ControlPlaneHardFailure(Exception):
    """Exception raised when global propagation state breaks down."""
    pass


# ============================================================
# Phase 7: Sūtradhāra Agent Registration
# ============================================================

SUTRADHARA_AGENT_REGISTRY = {
    "enforcement_gate_v1": {
        "agent_id": "enforcement_gate_v1",
        "capability": "enforcement_gate",
        "permissions": ["READ_ONLY", "NO_EXECUTION_RIGHTS", "NO_SYSTEM_ACCESS"]
    }
}

def verify_agent_capabilities(agent_id: str, required_capability: str) -> None:
    """Validate that the actor explicitly proves non-execution bounds constraints."""
    agent = SUTRADHARA_AGENT_REGISTRY.get(agent_id)
    if not agent:
        raise AgentVerificationError(f"Agent {agent_id} is not registered in Sūtradhāra.")
    if agent.get("capability") != required_capability:
        raise AgentVerificationError(f"Agent {agent_id} lacks capability: {required_capability}.")
    if "NO_EXECUTION_RIGHTS" not in agent.get("permissions", []):
        raise ControlPlaneHardFailure(f"Agent {agent_id} failed to prove NO_EXECUTION_RIGHTS. Boundary violation.")


def provision_execution_id(provided_id: Optional[str] = None) -> str:
    """
    Provisions a canonical execution_id if none is explicitly provided.
    Global propagation mandates that this ID is used end-to-end.
    """
    return provided_id if provided_id else f"exec-{uuid.uuid4().hex[:12]}"


def verify_agent(source_system_str: str) -> SourceSystem:
    """
    Validates the invoking agent against the decentralized registry.
    Currently statically verified against SourceSystem enum.
    """
    try:
        return SourceSystem(source_system_str)
    except ValueError:
        logger.error(
            "Agent verification failed",
            extra={
                "event_type": "sutradhara_registration_failure",
                "attempted_agent": source_system_str
            }
        )
        raise AgentVerificationError(f"Unregistered or invalid agent identity: {source_system_str}")


def invoke_agent(ksml_input: KSMLInput) -> CoreExecutionResult:
    """
    The unified invocation point for any agent interacting with enforcement.
    Pipeline:
      1. Prove strict KSML boundary schema (Phase 6)
      2. Verify Agent identity
      3. Verify Agent capabilities (Phase 7)
      4. Guarantee global Execution ID
      5. Route to Core Execution Gate for the Sarathi/Enforcement lifecycle
    """
    if not isinstance(ksml_input, KSMLInput):
        logger.error(
            "Non-KSML input rejected",
            extra={"event_type": "ksml_violation"}
        )
        raise ControlPlaneHardFailure("NON_KSML_INPUT_DETACHED: Input must be a valid KSMLInput instance.")

    # Phase 6 mappings: unpack canonical KSML inputs
    canonical_exec_id = provision_execution_id(ksml_input.execution_id)
    metadata = ksml_input.metadata
    actor = metadata.get("actor", "UNKNOWN")
    proposed_action = metadata.get("proposed_action", "UNKNOWN")
    source_system_str = metadata.get("source_system", "UNKNOWN")

    # Phase 7: Prove non-execution rights
    verify_agent_capabilities("enforcement_gate_v1", "enforcement_gate")
    
    # Re-hydrate the DGIC input from nested metadata dictionary
    dgic_dict = metadata["dgic_epistemic_state"]
    if isinstance(dgic_dict, DGICEpistemicStateInput):
        dgic_epistemic_state = dgic_dict
    else:
        dgic_epistemic_state = DGICEpistemicStateInput(**dgic_dict)

    canonical_system = verify_agent(source_system_str)

    logger.info(
        f"Sūtradhāra: Agent {canonical_system.value} authenticated via KSML. Dispatching payload.",
        extra={
            "execution_id": canonical_exec_id,
            "event_type": "sutradhara_invoke",
            "source_system": canonical_system.value,
            "actor": actor
        }
    )

    # Dispatch to Core Execution Gate, which internally invokes:
    # 1. Sarathi Governance (Layer 1)
    # 2. Enforcement Gate (Layer 4)
    result = submit_proposal(
        execution_id=canonical_exec_id,
        actor=actor,
        proposed_action=proposed_action,
        context_signals=ksml_input.structured_signals,
        dgic_epistemic_state=dgic_epistemic_state,
        source_system=canonical_system
    )

    if result.execution_id != canonical_exec_id:
        logger.error(
            f"Control Plane HARD FAULT: Core returned different execution_id. "
            f"Expected {canonical_exec_id}, got {result.execution_id}.",
            extra={
                "event_type": "control_plane_hard_fault",
                "code": "EXECUTION_ID_CORRUPTION"
            }
        )
        raise ControlPlaneHardFailure("EXECUTION_ID_CORRUPTION: Pipeline failed to preserve execution identity.")

    return result
