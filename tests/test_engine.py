from app.engine import analyze_text


# =========================
# Determinism Tests
# =========================

def test_determinism_same_input():
    text = "This is a scam message"
    assert analyze_text(text) == analyze_text(text)


def test_same_input_determinism_simple():
    assert analyze_text("scam") == analyze_text("scam")


# =========================
# Input Validation Tests
# =========================

def test_empty_input():
    result = analyze_text("")
    assert result["errors"]["error_code"] == "EMPTY_INPUT"


def test_invalid_type_input():
    result = analyze_text(123)
    assert result["errors"]["error_code"] == "INVALID_TYPE"


# =========================
# Risk Classification Tests
# =========================

def test_medium_risk_multiple_categories():
    """
    'kill' (violence) + 'scam' (fraud)
    Each contributes 0.2 → total 0.4 → MEDIUM
    """
    result = analyze_text("kill and scam")
    assert result["risk_category"] == "MEDIUM"


def test_low_risk_no_keywords():
    result = analyze_text("This is a normal message")
    assert result["risk_category"] == "LOW"


# =========================
# Matching Correctness Tests
# =========================

def test_no_substring_false_positive():
    """
    'studies' should NOT match 'die'
    """
    result = analyze_text("studies")
    assert result["risk_category"] == "LOW"


# =========================
# Saturation & Boundary Tests
# =========================

def test_category_saturation_cap():
    """
    Repeated keywords from same category
    must not exceed MAX_CATEGORY_SCORE (0.6)
    """
    text = "kill kill kill kill kill"
    result = analyze_text(text)
    assert result["risk_score"] <= 0.6


def test_long_input_truncation():
    text = "scam " * 2000
    result = analyze_text(text)
    assert result["processed_length"] <= 5000

# these are test which are taken for the confidence score
def test_confidence_determinism():
    result1 = analyze_text("kill")
    result2 = analyze_text("kill")
    assert result1["confidence_score"] == result2["confidence_score"]

def test_low_confidence_ambiguous():
    result = analyze_text("kill time with friends")
    assert result["confidence_score"] < 0.7


# from app.engine import analyze_text

# def test_determinism():
#     text = "This is a scam message"
#     assert analyze_text(text) == analyze_text(text)

# def test_empty_input():
#     result = analyze_text("")
#     assert result["errors"]["error_code"] == "EMPTY_INPUT"

# def test_high_risk():
#     result = analyze_text("kill and scam")
#     assert result["risk_category"] == "HIGH"






# def test_no_substring_match():
#     result = analyze_text("studies")
#     assert result["risk_category"] == "LOW"


# def test_category_saturation_cap():
#     text = "kill kill kill kill kill"
#     result = analyze_text(text)
#     assert result["risk_score"] <= 0.6


# def test_same_input_determinism():
#     assert analyze_text("scam") == analyze_text("scam")

