def test_contradictory_feedback_does_not_break_policy():
    policy = PolicyState(
        policy_version=1,
        category_weights={"violence": 0.6},
        confidence_multiplier=1.0,
        update_count=0
    )

    for _ in range(10):
        policy, _ = learning_step(
            policy,
            predicted_category="HIGH",
            actual_outcome="SAFE",
            affected_category="violence"
        )

    assert policy.category_weights["violence"] >= 0.1
