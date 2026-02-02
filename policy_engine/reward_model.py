def calculate_reward(predicted_category: str, actual_outcome: str) -> float:
    """
    Deterministic reward mapping.

    predicted_category: LOW | MEDIUM | HIGH
    actual_outcome: SAFE | RISK_CONFIRMED
    """

    if predicted_category == "HIGH" and actual_outcome == "RISK_CONFIRMED":
        return +1.0

    if predicted_category == "LOW" and actual_outcome == "SAFE":
        return +0.5

    if predicted_category == "HIGH" and actual_outcome == "SAFE":
        return -1.0  # false positive

    if predicted_category == "LOW" and actual_outcome == "RISK_CONFIRMED":
        return -1.0  # missed risk

    return -0.2  # ambiguous cases
