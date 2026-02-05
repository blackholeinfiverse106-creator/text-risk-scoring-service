import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from app.engine import analyze_text

class TestSystemGuarantees:
    """
    Comprehensive tests that validate ALL system guarantees
    under normal and stress conditions.
    """

    def test_determinism_guarantee_exhaustive(self):
        """Verify determinism across all input types and edge cases"""
        test_cases = [
            "",  # Empty
            "normal text",  # Clean
            "kill scam hack",  # Multiple keywords
            "a" * 5000,  # Max length
            "a" * 6000,  # Over max length
            "kill " * 100,  # Saturation
            "studies",  # Substring false positive
            123,  # Invalid type
            None,  # Null
        ]
        
        for test_input in test_cases:
            result1 = analyze_text(test_input)
            result2 = analyze_text(test_input)
            assert result1 == result2, f"Determinism failed for input: {test_input}"

    def test_structured_response_guarantee(self):
        """Verify structured response under ALL conditions"""
        required_fields = ["risk_score", "risk_category", "trigger_reasons", 
                          "confidence_score", "processed_length", "errors"]
        
        test_inputs = ["", "normal", "kill", 123, None, "x" * 10000]
        
        for test_input in test_inputs:
            result = analyze_text(test_input)
            assert isinstance(result, dict), f"Response not dict for: {test_input}"
            
            for field in required_fields:
                assert field in result, f"Missing field {field} for input: {test_input}"

    def test_no_crash_guarantee_stress(self):
        """Verify system never crashes under stress conditions"""
        stress_inputs = [
            "",
            None,
            123,
            [],
            {},
            "kill " * 1000,
            "x" * 100000,  # Excessive length
            "\x00\x01\x02",  # Binary data
            "🔥💀☠️" * 100,  # Unicode stress
        ]
        
        for stress_input in stress_inputs:
            try:
                result = analyze_text(stress_input)
                assert isinstance(result, dict), "System crashed or returned invalid response"
            except Exception as e:
                pytest.fail(f"System crashed with input {stress_input}: {e}")

    def test_bounded_score_guarantee(self):
        """Verify risk_score is ALWAYS between 0.0 and 1.0"""
        extreme_inputs = [
            "kill murder attack bomb gun knife death execute " * 50,  # Extreme saturation
            "",  # Empty
            "normal text",  # Clean
        ]
        
        for test_input in extreme_inputs:
            result = analyze_text(test_input)
            score = result["risk_score"]
            assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for: {test_input}"

    def test_explainable_decisions_guarantee(self):
        """Verify ALL decisions include explanations"""
        test_cases = [
            ("kill", True),  # Should have reasons
            ("normal text", False),  # Should have no reasons
            ("", False),  # Error case
        ]
        
        for test_input, should_have_reasons in test_cases:
            result = analyze_text(test_input)
            reasons = result["trigger_reasons"]
            
            if should_have_reasons:
                assert len(reasons) > 0, f"Missing explanations for: {test_input}"
            
            # All reasons must be strings
            for reason in reasons:
                assert isinstance(reason, str), f"Non-string reason for: {test_input}"

    def test_concurrent_determinism_guarantee(self):
        """Verify determinism under concurrent execution"""
        test_input = "kill scam hack"
        num_threads = 10
        results = []
        
        def worker():
            results.append(analyze_text(test_input))
        
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All results must be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result == first_result, f"Concurrent determinism failed at thread {i}"

    def test_failure_mode_coverage(self):
        """Verify all documented failure modes are handled"""
        failure_test_cases = [
            ("", "EMPTY_INPUT"),
            (123, "INVALID_TYPE"),
            (None, "INVALID_TYPE"),
            ([], "INVALID_TYPE"),
            ({}, "INVALID_TYPE"),
        ]
        
        for test_input, expected_error in failure_test_cases:
            result = analyze_text(test_input)
            assert result["errors"] is not None, f"No error for invalid input: {test_input}"
            assert result["errors"]["error_code"] == expected_error, \
                f"Wrong error code for {test_input}: got {result['errors']['error_code']}, expected {expected_error}"

    def test_performance_bounds_guarantee(self):
        """Verify processing time is bounded"""
        large_input = "kill scam hack " * 1000
        
        start_time = time.time()
        result = analyze_text(large_input)
        processing_time = time.time() - start_time
        
        # Should complete within reasonable time (1 second)
        assert processing_time < 1.0, f"Processing took too long: {processing_time}s"
        assert isinstance(result, dict), "Failed to return valid result"

    def test_memory_bounds_guarantee(self):
        """Verify memory usage is bounded"""
        # Test with very large input that should be truncated
        huge_input = "kill " * 10000  # Much larger than MAX_TEXT_LENGTH
        
        result = analyze_text(huge_input)
        
        # Should handle gracefully without memory issues
        assert result["processed_length"] <= 5000, "Input not properly truncated"
        assert "truncated" in " ".join(result["trigger_reasons"]).lower(), "Truncation not reported"

class TestStressConditions:
    """Tests specifically for stress and boundary conditions"""
    
    def test_rapid_fire_requests(self):
        """Test system stability under rapid requests"""
        def make_request():
            return analyze_text("kill scam")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [future.result() for future in futures]
        
        # All results should be identical (determinism under load)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Determinism failed under load"

    def test_edge_case_combinations(self):
        """Test combinations of edge cases"""
        edge_cases = [
            ("", "EMPTY_INPUT"),
            ("   ", "EMPTY_INPUT"),  # Whitespace only
            ("kill" * 2000, None),  # Long with keywords
            ("normal" * 2000, None),  # Long without keywords
        ]
        
        for test_input, expected_error in edge_cases:
            result = analyze_text(test_input)
            
            # Should always return structured response
            assert isinstance(result, dict)
            assert "risk_score" in result
            assert "risk_category" in result
            
            if expected_error:
                assert result["errors"]["error_code"] == expected_error