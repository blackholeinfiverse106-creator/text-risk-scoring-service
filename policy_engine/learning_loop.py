from .reward_model import calculate_reward
from .policy_update import update_policy


def learning_step(
    policy_state,
    predicted_category,
    actual_outcome,
    affected_category
):
    reward = calculate_reward(predicted_category, actual_outcome)

    new_policy = update_policy(
        current_policy=policy_state,
        affected_category=affected_category,
        reward=reward
    )

    return new_policy, reward
