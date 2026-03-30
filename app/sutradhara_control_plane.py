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
)
from app.core_execution_gate import submit_proposal, CoreExecutionResult

logger = logging.getLogger(__name__)


class AgentVerificationError(Exception):
    """Exception raised when an unregistered agent attempts invocation."""
    pass


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


def invoke_agent(
    source_system: str,
    actor: str,
    proposed_action: str,
    dgic_epistemic_state: DGICEpistemicStateInput,
    context_signals: Optional[List[ContextSignal]] = None,
    execution_id: Optional[str] = None,
) -> CoreExecutionResult:
    """
    The unified invocation point for any agent interacting with enforcement.
    Pipeline:
      1. Verify Agent identity
      2. Guarantee global Execution ID
      3. Route to Core Execution Gate for the Sarathi/Enforcement lifecycle
    """
    canonical_system = verify_agent(source_system)
    canonical_exec_id = provision_execution_id(execution_id)
    signals = context_signals or []

    logger.info(
        f"Sūtradhāra: Agent {canonical_system.value} authenticated. Dispatching payload.",
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
        context_signals=signals,
        dgic_epistemic_state=dgic_epistemic_state,
        source_system=canonical_system
    )

    return result
