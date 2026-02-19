"""
Test: Caching Misuse Scenarios
Validates determinism and proper caching behavior
"""
import pytest
import time
from app.engine import analyze_text

class TestCachingMisuse:
    """Test resistance to caching misuse"""
    
    def test_deterministic_output_for_caching(self):
        """Same input must produce same output (cacheable)"""
        text = "kill attack murder"
        
        result1 = analyze_text(text)
        result2 = analyze_text(text)
        
        # Remove non-deterministic fields for comparison
        def normalize(r):
            return {
                "risk_score": r["risk_score"],
                "confidence_score": r["confidence_score"],
                "risk_category": r["risk_category"],
                "processed_length": r["processed_length"],
                "safety_metadata": r["safety_metadata"]
            }
        
        assert normalize(result1) == normalize(result2)
    
    def test_context_agnostic_warning(self):
        """System should be context-agnostic (documented limitation)"""
        # "kill time" and "kill person" get same treatment
        result1 = analyze_text("kill time")
        result2 = analyze_text("kill person")
        
        # Both detect "kill" keyword
        assert result1["risk_score"] > 0
        assert result2["risk_score"] > 0
        
        # System cannot distinguish context (documented limitation)
        # This is why downstream needs policy layer
    
    def test_full_text_required_for_cache_key(self):
        """Cache key should be full text, not keywords"""
        # Different texts with same keyword
        text1 = "I will kill you"
        text2 = "This movie will kill at the box office"
        
        result1 = analyze_text(text1)
        result2 = analyze_text(text2)
        
        # Both contain "kill" but are different texts
        # System treats them the same (context-agnostic)
        # But cache key should be full text hash
        assert result1["processed_length"] != result2["processed_length"]
    
    def test_no_state_between_requests(self):
        """Request N should not affect request N+1"""
        # High risk request
        result1 = analyze_text("kill murder attack bomb")
        
        # Safe request
        result2 = analyze_text("hello world")
        
        # Low risk request
        result3 = analyze_text("hello world")
        
        # Result2 and Result3 should be identical (no state leakage)
        assert result2["risk_score"] == result3["risk_score"]
        assert result2["risk_category"] == result3["risk_category"]
    
    def test_interleaved_requests_independent(self):
        """Interleaved requests should not affect each other"""
        texts = [
            "kill attack",
            "hello world",
            "murder bomb",
            "nice day",
            "terrorist threat"
        ]
        
        # Run once
        results1 = [analyze_text(t) for t in texts]
        
        # Run again in different order
        import random
        shuffled = texts.copy()
        random.shuffle(shuffled)
        results2 = {t: analyze_text(t) for t in shuffled}
        
        # Results should match regardless of order
        for i, text in enumerate(texts):
            assert results1[i]["risk_score"] == results2[text]["risk_score"]
    
    def test_rapid_fire_determinism(self):
        """Rapid repeated requests should be deterministic"""
        text = "dangerous content kill"
        results = [analyze_text(text) for _ in range(10)]
        
        # All results should be identical
        first = results[0]
        for result in results[1:]:
            assert result["risk_score"] == first["risk_score"]
            assert result["risk_category"] == first["risk_category"]
            assert result["confidence_score"] == first["confidence_score"]
