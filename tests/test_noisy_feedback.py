from policy_engine.policy_state import PolicyState
from policy_engine.learning_loop import learning_step


def test_noisy_feedback_stability():
    policy = PolicyState(
        policy_version=1,
        category_weights={"fraud": 0.5},
        confidence_multiplier=1.0,
        update_count=0
    )

    outcomes = ["RISK_CONFIRMED", "SAFE"] * 5

    for outcome in outcomes:
        policy, _ = learning_step(
            policy,
            predicted_category="HIGH",
            actual_outcome=outcome,
            affected_category="fraud"
        )

    final_weight = policy.category_weights["fraud"]

    assert 0.1 <= final_weight <= 1.0
