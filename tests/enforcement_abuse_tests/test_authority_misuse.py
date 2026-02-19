"""
Test: Authority Misuse Scenarios
Validates that system resists being treated as decision authority
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.engine import analyze_text

class TestAuthorityMisuse:
    """Test resistance to authority misuse"""
    
    def test_high_risk_still_declares_non_authority(self):
        """Even HIGH risk must declare non-authority"""
        result = analyze_text("kill murder attack bomb terrorist")
        
        assert result["risk_category"] == "HIGH"
        assert result["safety_metadata"]["is_decision"] is False
        assert result["safety_metadata"]["authority"] == "NONE"
        assert result["safety_metadata"]["actionable"] is False
    
    def test_low_confidence_high_risk_flags_review(self):
        """High risk + low confidence should signal caution"""
        # Single keyword = low confidence
        result = analyze_text("kill")
        
        # Should be flagged but not actionable
        assert result["confidence_score"] < 0.8
        assert result["safety_metadata"]["actionable"] is False
    
    def test_safety_metadata_always_present(self):
        """safety_metadata must be in every response"""
        test_cases = [
            "safe content",
            "kill murder attack",
            "",  # Error case
            "a" * 6000,  # Truncation case
        ]
        
        for text in test_cases:
            result = analyze_text(text)
            assert "safety_metadata" in result
            assert result["safety_metadata"]["is_decision"] is False
    
    def test_cannot_output_action_commands(self):
        """Response must not contain action fields"""
        result = analyze_text("dangerous content kill attack")
        
        # Verify no action fields exist
        forbidden_fields = ["action", "command", "execute", "delete", "ban", "block"]
        for field in forbidden_fields:
            assert field not in result
    
    def test_thresholds_are_heuristic_not_policy(self):
        """Internal thresholds should not be treated as policy"""
        # Test boundary cases
        low_boundary = analyze_text("bad")  # Just below MEDIUM
        medium_boundary = analyze_text("kill attack")  # Just below HIGH
        
        # Both should declare non-authority
        assert low_boundary["safety_metadata"]["authority"] == "NONE"
        assert medium_boundary["safety_metadata"]["authority"] == "NONE"
        
        # Categories are descriptive, not prescriptive
        assert "risk_category" in low_boundary  # Describes risk
        assert "action" not in low_boundary  # Does not prescribe action
