from app.engine import analyze_text

def test_determinism():
    text = "This is a scam message"
    assert analyze_text(text) == analyze_text(text)

def test_empty_input():
    result = analyze_text("")
    assert result["errors"]["error_code"] == "EMPTY_INPUT"

def test_high_risk():
    result = analyze_text("kill and scam")
    assert result["risk_category"] == "HIGH"
