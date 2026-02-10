"""
Stress Test Suite - Push System to Actual Limits
Tests system behavior under extreme conditions
"""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.engine import analyze_text

class TestSystemLimits:
    """Test system at breaking points"""
    
    def test_maximum_input_length(self):
        """Test at exact maximum length"""
        text = "a" * 5000
        result = analyze_text(text)
        assert result["processed_length"] == 5000
        assert result["errors"] is None
    
    def test_beyond_maximum_length(self):
        """Test truncation at 10x max length"""
        text = "scam " * 2000  # 10,000 chars
        result = analyze_text(text)
        assert result["processed_length"] == 5000
        assert any("truncated" in r.lower() for r in result["trigger_reasons"])
    
    def test_extreme_keyword_saturation(self):
        """Test with 100 keyword matches"""
        text = " ".join(["kill", "scam", "hack", "bomb", "drug"] * 20)
        result = analyze_text(text)
        assert result["risk_score"] == 1.0  # Clamped
        assert result["risk_category"] == "HIGH"
    
    def test_single_category_saturation(self):
        """Test category cap - single category maxes at 0.6"""
        # Use many violence keywords - should cap at 0.6 per category
        text = "kill murder attack assault stab shoot"  # 6 keywords * 0.2 = 1.2, capped at 0.6
        result = analyze_text(text)
        # Single category (violence) capped at 0.6
        assert result["risk_score"] == 0.6
        assert result["risk_category"] == "MEDIUM"
    
    def test_all_categories_triggered(self):
        """Test with keywords from all 10 categories"""
        text = "kill scam idiot sex drug terrorist suicide hack gun threaten"
        result = analyze_text(text)
        assert result["risk_category"] == "HIGH"
        assert len(result["trigger_reasons"]) >= 10
    
    def test_concurrent_load_100_threads(self):
        """Test with 100 concurrent requests"""
        inputs = ["test scam"] * 100
        results = []
        
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(analyze_text, inp) for inp in inputs]
            for future in as_completed(futures):
                results.append(future.result())
        
        # All should be identical (determinism)
        assert len(set(str(r) for r in results)) == 1
        assert len(results) == 100
    
    def test_rapid_sequential_requests(self):
        """Test 1000 sequential requests"""
        start = time.time()
        for _ in range(1000):
            result = analyze_text("test")
        duration = time.time() - start
        
        # Should complete in reasonable time
        assert duration < 10.0  # 10 seconds for 1000 requests
        assert result["errors"] is None
    
    def test_alternating_valid_invalid_1000_times(self):
        """Test error handling under stress"""
        for i in range(1000):
            if i % 2 == 0:
                result = analyze_text("test")
                assert result["errors"] is None
            else:
                result = analyze_text("")
                assert result["errors"]["error_code"] == "EMPTY_INPUT"
    
    def test_unicode_stress(self):
        """Test with various Unicode characters"""
        unicode_tests = [
            "测试 scam 测试",  # Chinese
            "тест scam тест",  # Cyrillic
            "🔥 scam 🔥",  # Emoji
            "café scam café",  # Accented
            "א scam א",  # Hebrew
        ]
        
        for text in unicode_tests:
            result = analyze_text(text)
            # Should not crash
            assert "risk_score" in result
    
    def test_special_characters_stress(self):
        """Test with special characters"""
        special = "!@#$%^&*()_+-=[]{}|;:',.<>?/~` scam"
        result = analyze_text(special)
        assert result["errors"] is None
        assert "scam" in str(result["trigger_reasons"])
    
    def test_whitespace_variations(self):
        """Test various whitespace patterns"""
        whitespace_tests = [
            "scam\t\t\thack",  # Tabs
            "scam\n\n\nhack",  # Newlines
            "scam     hack",  # Multiple spaces
            "scam\r\nhack",  # CRLF
        ]
        
        for text in whitespace_tests:
            result = analyze_text(text)
            assert result["errors"] is None
    
    def test_boundary_score_0_3(self):
        """Test exact threshold boundary"""
        # 0.2 * 1 = 0.2 (LOW), 0.2 * 2 = 0.4 (MEDIUM)
        text = "kill scam"  # Should be 0.4
        result = analyze_text(text)
        assert result["risk_category"] == "MEDIUM"
    
    def test_boundary_score_0_7(self):
        """Test high threshold boundary"""
        # Need score >= 0.7
        text = "kill scam hack bomb"  # 0.8
        result = analyze_text(text)
        assert result["risk_category"] == "HIGH"
    
    def test_memory_stress_large_reasons_list(self):
        """Test with input that generates many trigger reasons"""
        # Create text with 50 unique keywords
        keywords = ["kill", "murder", "attack", "assault", "stab", 
                   "scam", "fraud", "hack", "phish", "fake",
                   "idiot", "stupid", "hate", "trash", "racist",
                   "sex", "porn", "nude", "rape", "molest",
                   "drug", "cocaine", "heroin", "weed", "lsd"]
        text = " ".join(keywords * 2)
        result = analyze_text(text)
        assert len(result["trigger_reasons"]) >= 25
    
    def test_determinism_under_load(self):
        """Test determinism with concurrent varied inputs"""
        test_cases = [
            "kill",
            "scam",
            "hack bomb",
            "normal text",
            ""
        ]
        
        # Run each test case 20 times concurrently
        for test_input in test_cases:
            results = []
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(analyze_text, test_input) for _ in range(20)]
                for future in as_completed(futures):
                    results.append(future.result())
            
            # All results should be identical
            if test_input:  # Skip empty string
                unique_results = len(set(str(r) for r in results))
                assert unique_results == 1, f"Non-deterministic for input: {test_input}"


class TestEdgeCases:
    """Test extreme edge cases"""
    
    def test_only_keywords_no_other_text(self):
        """Test input that is only keywords"""
        text = "kill scam hack bomb drug"
        result = analyze_text(text)
        assert result["risk_category"] == "HIGH"
    
    def test_single_character(self):
        """Test minimal valid input"""
        result = analyze_text("a")
        assert result["risk_category"] == "LOW"
        assert result["processed_length"] == 1
    
    def test_repeated_same_keyword(self):
        """Test same keyword repeated"""
        text = "kill " * 100
        result = analyze_text(text)
        # Should be capped
        assert result["risk_score"] <= 0.6
    
    def test_case_insensitivity_stress(self):
        """Test various case combinations"""
        cases = ["KILL", "Kill", "kIlL", "KiLl"]
        results = [analyze_text(c) for c in cases]
        # All should be identical
        assert len(set(str(r) for r in results)) == 1
    
    def test_mixed_valid_invalid_keywords(self):
        """Test with both matching and non-matching words"""
        text = "hello kill world scam test hack normal"
        result = analyze_text(text)
        assert result["risk_category"] in ["MEDIUM", "HIGH"]


class TestPerformanceLimits:
    """Test performance boundaries"""
    
    def test_processing_time_max_input(self):
        """Test processing time for maximum input"""
        text = "a" * 5000
        start = time.time()
        result = analyze_text(text)
        duration = time.time() - start
        
        # Should complete in under 100ms
        assert duration < 0.1
        assert result["errors"] is None
    
    def test_processing_time_keyword_heavy(self):
        """Test processing time with many keywords"""
        text = " ".join(["kill", "scam", "hack"] * 100)
        start = time.time()
        result = analyze_text(text)
        duration = time.time() - start
        
        # Should still be fast
        assert duration < 0.5
    
    def test_throughput_measurement(self):
        """Measure actual throughput"""
        iterations = 100
        start = time.time()
        
        for _ in range(iterations):
            analyze_text("test scam")
        
        duration = time.time() - start
        throughput = iterations / duration
        
        # Should handle at least 100 req/sec
        assert throughput > 100, f"Throughput: {throughput:.2f} req/sec"


class TestFailureRecovery:
    """Test system recovery from failures"""
    
    def test_recovery_after_error(self):
        """Test that system recovers after error"""
        # Cause error
        result1 = analyze_text("")
        assert result1["errors"] is not None
        
        # Should work normally after
        result2 = analyze_text("test")
        assert result2["errors"] is None
    
    def test_interleaved_errors_and_success(self):
        """Test alternating errors and successes"""
        for i in range(100):
            if i % 3 == 0:
                result = analyze_text("")
                assert result["errors"] is not None
            else:
                result = analyze_text("test")
                assert result["errors"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
