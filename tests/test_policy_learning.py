from policy_engine.policy_state import PolicyState
from policy_engine.learning_loop import learning_step


def test_policy_determinism():
    policy = PolicyState(
        policy_version=1,
        category_weights={"fraud": 0.5},
        confidence_multiplier=1.0,
        update_count=0
    )

    new_policy_1, reward_1 = learning_step(
        policy, "HIGH", "RISK_CONFIRMED", "fraud"
    )

    new_policy_2, reward_2 = learning_step(
        policy, "HIGH", "RISK_CONFIRMED", "fraud"
    )

    assert new_policy_1 == new_policy_2
    assert reward_1 == reward_2
