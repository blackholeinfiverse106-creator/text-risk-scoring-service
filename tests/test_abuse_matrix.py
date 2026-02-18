import pytest
from app.engine import analyze_text

def test_abuse_zalgo():
    """
    Zalgo text should not crash the engine. 
    It might not match keywords if normalization is simple, but MUST NOT CRASH.
    """
    zalgo = "k҉i҉l҉l҉" 
    # Our regex is \bkill\b. Zalgo chars might break the match, which is fine (safe fail), 
    # but we verify it runs.
    res = analyze_text(zalgo)
    assert res["processed_length"] > 0
    assert res["errors"] is None

def test_abuse_emoji_flood():
    """
    Emojis should not match any risk categories.
    """
    flood = "🔪" * 100 # Knife emoji 
    # We do NOT match emojis currently, only text keywords.
    res = analyze_text(flood)
    assert res["risk_score"] == 0.0
    assert res["risk_category"] == "LOW"

def test_abuse_rtl_override():
    """
    RTL overrides should not confuse the tokenizer.
    """
    rtl = "\u202E" + "kill"
    res = analyze_text(rtl)
    assert res["errors"] is None
    # \b matches word boundaries, \u202E is non-word, so "kill" might match if regex engine handles it.
    # We primarily care about NO CRASH.

def test_abuse_null_bytes():
    """
    Null bytes should not cause C-style string termination issues in Python.
    """
    text = "kill\x00me"
    res = analyze_text(text)
    assert "violence" in str(res["trigger_reasons"]).lower()
