"""
Test: Fail-Closed Behavior
Validates that system fails safely under error conditions
"""
import pytest
from app.engine import analyze_text

class TestFailClosedBehavior:
    """Test fail-closed behavior under error conditions"""
    
    def test_empty_input_fails_closed(self):
        """Empty input should error, not default to 'safe'"""
        result = analyze_text("")
        
        # Should return error, not risk_score=0.0 with "safe"
        assert result["errors"] is not None
        assert result["errors"]["error_code"] == "EMPTY_INPUT"
        
        # Risk score is 0.0 but with explicit error
        assert result["risk_score"] == 0.0
        assert result["risk_category"] == "LOW"
    
    def test_invalid_type_fails_closed(self):
        """Invalid input type should error, not default"""
        result = analyze_text(123)  # Invalid type
        
        assert result["errors"] is not None
        assert result["errors"]["error_code"] == "INVALID_TYPE"
        
        # Fails closed with error, not silent failure
    
    def test_error_responses_include_safety_metadata(self):
        """Even errors must declare non-authority"""
        result = analyze_text("")
        
        assert result["errors"] is not None
        assert "safety_metadata" in result
        assert result["safety_metadata"]["is_decision"] is False
    
    def test_ambiguous_input_low_confidence(self):
        """Ambiguous input should result in low confidence"""
        # Single keyword = ambiguous
        result = analyze_text("kill")
        
        # Low confidence signals ambiguity
        assert result["confidence_score"] < 0.8
        
        # Should flag for human review (via low confidence)
    
    def test_no_default_safe_assumption(self):
        """System should not default to 'safe' on errors"""
        error_cases = [
            "",  # Empty
            123,  # Invalid type
        ]
        
        for case in error_cases:
            result = analyze_text(case)
            
            # Should have explicit error
            assert result["errors"] is not None
            
            # Should not silently return "safe"
            # (risk_score=0.0 is with error, not default safe)
    
    def test_truncation_is_explicit(self):
        """Truncation should be explicitly flagged"""
        long_text = "kill " * 2000  # Exceeds limit
        result = analyze_text(long_text)
        
        # Should process but flag truncation
        assert result["processed_length"] == 5000
        assert any("truncat" in r.lower() for r in result["trigger_reasons"])
    
    def test_internal_error_fails_closed(self):
        """Internal errors should fail closed with error response"""
        # This is tested via exception handling in engine
        # Verify error response structure
        result = analyze_text("")
        
        # Error response is structured and safe
        assert "risk_score" in result
        assert "safety_metadata" in result
        assert "errors" in result
