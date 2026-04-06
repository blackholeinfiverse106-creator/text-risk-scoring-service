import logging

logger = logging.getLogger(__name__)

def execute_action(action: str, execution_id: str):
    """
    Execution Owner Logic:
    Physically execute the sovereign-approved operation.
    """
    logger.info(
        f"Core executing action: {action} | execution_id={execution_id}", 
        extra={"event_type": "core_action_executed", "action": action, "execution_id": execution_id}
    )

def block_execution(action: str, execution_id: str, reason: str):
    """
    Execution Owner Logic:
    Deterministically block sovereign-denied or sovereign-abstained operations.
    """
    logger.warning(
        f"Core blocked execution: {action} | execution_id={execution_id} | reason={reason}", 
        extra={"event_type": "core_action_blocked", "action": action, "execution_id": execution_id}
    )
