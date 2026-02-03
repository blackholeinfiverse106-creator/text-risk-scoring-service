from copy import deepcopy
import logging
from .policy_state import PolicyState

# =========================
# Logger setup
# =========================
logger = logging.getLogger(__name__)

# =========================
# Stability constraints
# =========================
MAX_DELTA = 0.05
MIN_WEIGHT = 0.1
MAX_WEIGHT = 1.0


def update_policy(
    current_policy: PolicyState,
    affected_category: str,
    reward: float
) -> PolicyState:
    # Copy current weights to preserve immutability
    new_weights = deepcopy(current_policy.category_weights)

    # Determine update direction based on reward
    delta = MAX_DELTA if reward > 0 else -MAX_DELTA
    delta = max(-MAX_DELTA, min(MAX_DELTA, delta))

    old_weight = new_weights.get(affected_category, 0.5)
    new_weight = old_weight + delta
    new_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, new_weight))

    # =========================
    # Reasoning / Trace Logging
    # =========================
    logger.info(
        "Policy update reasoning | category=%s | reward=%.2f | "
        "old_weight=%.2f | delta=%.2f | constrained_new_weight=%.2f | "
        "constraints=[MIN_WEIGHT=%.2f, MAX_WEIGHT=%.2f, MAX_DELTA=%.2f]",
        affected_category,
        reward,
        old_weight,
        delta,
        new_weight,
        MIN_WEIGHT,
        MAX_WEIGHT,
        MAX_DELTA
    )

    new_weights[affected_category] = new_weight

    # Return a NEW immutable policy state (no mutation)
    return PolicyState(
        policy_version=current_policy.policy_version + 1,
        category_weights=new_weights,
        confidence_multiplier=current_policy.confidence_multiplier,
        update_count=current_policy.update_count + 1
    )
