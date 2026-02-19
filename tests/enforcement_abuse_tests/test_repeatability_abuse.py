"""
Test: Repeatability Under Abuse
Validates deterministic behavior under stress and abuse
"""
import pytest
import concurrent.futures
from app.engine import analyze_text

class TestRepeatabilityUnderAbuse:
    """Test deterministic behavior under abuse conditions"""
    
    def test_repeated_identical_requests(self):
        """Hammering with identical requests should produce identical results"""
        text = "kill murder attack"
        results = [analyze_text(text) for _ in range(100)]
        
        # All results should be identical
        first = results[0]
        for result in results[1:]:
            assert result["risk_score"] == first["risk_score"]
            assert result["risk_category"] == first["risk_category"]
            assert result["confidence_score"] == first["confidence_score"]
    
    def test_concurrent_requests_deterministic(self):
        """Concurrent requests should not affect each other"""
        text = "dangerous content"
        
        def make_request():
            return analyze_text(text)
        
        # Run 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # All results should be identical
        first = results[0]
        for result in results[1:]:
            assert result["risk_score"] == first["risk_score"]
            assert result["risk_category"] == first["risk_category"]
    
    def test_alternating_requests_independent(self):
        """Alternating between different requests should be independent"""
        text_a = "kill attack"
        text_b = "hello world"
        
        # Alternate 50 times
        results_a = []
        results_b = []
        
        for i in range(50):
            if i % 2 == 0:
                results_a.append(analyze_text(text_a))
            else:
                results_b.append(analyze_text(text_b))
        
        # All A results should be identical
        first_a = results_a[0]
        for result in results_a[1:]:
            assert result["risk_score"] == first_a["risk_score"]
        
        # All B results should be identical
        first_b = results_b[0]
        for result in results_b[1:]:
            assert result["risk_score"] == first_b["risk_score"]
    
    def test_no_memory_leakage_under_load(self):
        """Repeated requests should not leak state"""
        # Run many requests with different content
        for i in range(100):
            text = f"test content {i} kill attack"
            result = analyze_text(text)
            
            # Each request should be independent
            assert "risk_score" in result
            assert result["safety_metadata"]["is_decision"] is False
    
    def test_error_requests_dont_affect_valid_requests(self):
        """Error requests should not corrupt subsequent valid requests"""
        # Error request
        error_result = analyze_text("")
        assert error_result["errors"] is not None
        
        # Valid request should work normally
        valid_result = analyze_text("test content")
        assert valid_result["errors"] is None
        assert valid_result["risk_score"] >= 0
        
        # Another error
        error_result2 = analyze_text(123)
        assert error_result2["errors"] is not None
        
        # Another valid request
        valid_result2 = analyze_text("test content")
        assert valid_result2["errors"] is None
        
        # Valid results should be identical
        assert valid_result["risk_score"] == valid_result2["risk_score"]
    
    def test_boundary_cases_deterministic(self):
        """Boundary cases should be deterministic"""
        boundary_cases = [
            "",  # Empty
            " ",  # Whitespace
            "a",  # Single char
            "a" * 5000,  # Exact limit
            "a" * 5001,  # Over limit
        ]
        
        # Run each case multiple times
        for case in boundary_cases:
            results = [analyze_text(case) for _ in range(5)]
            
            # All results for same case should be identical
            first = results[0]
            for result in results[1:]:
                assert result["risk_score"] == first["risk_score"]
                assert result["errors"] == first["errors"]
    
    def test_unicode_handling_deterministic(self):
        """Unicode content should be handled deterministically"""
        unicode_texts = [
            "kill 你好",
            "attack مرحبا",
            "murder здравствуй",
        ]
        
        for text in unicode_texts:
            results = [analyze_text(text) for _ in range(5)]
            
            # Should be deterministic
            first = results[0]
            for result in results[1:]:
                assert result["risk_score"] == first["risk_score"]
