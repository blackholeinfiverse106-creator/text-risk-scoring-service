from copy import deepcopy
from .policy_state import PolicyState

MAX_DELTA = 0.05
MIN_WEIGHT = 0.1
MAX_WEIGHT = 1.0


def update_policy(
    current_policy: PolicyState,
    affected_category: str,
    reward: float
) -> PolicyState:
    new_weights = deepcopy(current_policy.category_weights)

    delta = MAX_DELTA if reward > 0 else -MAX_DELTA
    delta = max(-MAX_DELTA, min(MAX_DELTA, delta))

    old_weight = new_weights.get(affected_category, 0.5)
    new_weight = old_weight + delta
    new_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, new_weight))

    new_weights[affected_category] = new_weight

    return PolicyState(
        policy_version=current_policy.policy_version + 1,
        category_weights=new_weights,
        confidence_multiplier=current_policy.confidence_multiplier,
        update_count=current_policy.update_count + 1
    )
