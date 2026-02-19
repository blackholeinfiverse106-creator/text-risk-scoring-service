"""
Test: Improper Combination Scenarios
Validates proper handling of score aggregation and multi-signal use
"""
import pytest
from app.engine import analyze_text

class TestImproperCombination:
    """Test resistance to improper signal combination"""
    
    def test_confidence_must_be_considered_in_aggregation(self):
        """Low confidence signals should not be aggregated blindly"""
        # Single keyword = low confidence
        result1 = analyze_text("kill")
        
        # Multiple keywords = higher confidence
        result2 = analyze_text("kill murder attack bomb terrorist")
        
        # Confidence should differ
        assert result1["confidence_score"] < result2["confidence_score"]
        
        # Low confidence should warn against blind aggregation
        assert result1["confidence_score"] < 0.8
    
    def test_each_signal_declares_non_authority(self):
        """Every response must declare non-authority for proper combination"""
        texts = [
            "kill",
            "attack",
            "murder",
            "safe content"
        ]
        
        for text in texts:
            result = analyze_text(text)
            # Each signal must declare it's not a decision
            assert result["safety_metadata"]["is_decision"] is False
            assert result["safety_metadata"]["authority"] == "NONE"
    
    def test_scores_are_not_probabilities(self):
        """Risk scores are heuristic, not probabilistic"""
        result = analyze_text("kill attack")
        
        # Score is between 0-1 but not a probability
        assert 0 <= result["risk_score"] <= 1
        
        # Cannot be combined using probability math
        # (documented limitation)
    
    def test_temporal_aggregation_not_supported(self):
        """System does not support temporal aggregation"""
        # Same user, different times
        result1 = analyze_text("bad content")
        result2 = analyze_text("more bad content")
        
        # Each request is independent
        # No user_id, no session, no history
        assert "user_id" not in result1
        assert "session_id" not in result1
        assert "history" not in result1
        
        # System is stateless by design
    
    def test_cross_domain_reuse_warning(self):
        """Same text in different domains may have different risk"""
        # "attack" in gaming vs. violence context
        gaming_text = "attack the enemy base"
        violence_text = "attack the person"
        
        result1 = analyze_text(gaming_text)
        result2 = analyze_text(violence_text)
        
        # System treats both the same (context-agnostic)
        # This is why cross-domain cache reuse is dangerous
        assert result1["risk_score"] > 0
        assert result2["risk_score"] > 0
        
        # Both detect "attack" keyword
        assert any("attack" in r.lower() for r in result1["trigger_reasons"])
        assert any("attack" in r.lower() for r in result2["trigger_reasons"])
    
    def test_multi_signal_requires_policy_layer(self):
        """Combining multiple signals requires policy interpretation"""
        result = analyze_text("suspicious content")
        
        # Response structure does not support multi-signal combination
        assert "combined_score" not in result
        assert "other_signals" not in result
        assert "final_decision" not in result
        
        # Each signal stands alone, policy layer must combine
