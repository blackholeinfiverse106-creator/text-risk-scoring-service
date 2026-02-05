"""
Exhaustive Boundary Test Suite
Tests all failure modes, boundary conditions, and extreme score edges
"""
import pytest
import json
import hashlib
from app.engine import analyze_text

class TestInputFailures:
    """Test all INPUT_FAILURE modes"""
    
    def test_f01_empty_input_variations(self):
        """F-01: Test all empty input variations"""
        empty_inputs = [
            "",           # Truly empty
            " ",          # Single space
            "   ",        # Multiple spaces
            "\t",         # Tab
            "\n",         # Newline
            "\r\n",       # Windows newline
            "  \t\n  ",   # Mixed whitespace
        ]
        
        for empty_input in empty_inputs:
            result = analyze_text(empty_input)
            assert result["errors"]["error_code"] == "EMPTY_INPUT"
            assert result["risk_score"] == 0.0
            assert result["risk_category"] == "LOW"
            assert result["trigger_reasons"] == []
            assert result["processed_length"] == 0
    
    def test_f02_invalid_type_exhaustive(self):
        """F-02: Test all invalid input types"""
        invalid_inputs = [
            123,                    # Integer
            123.45,                 # Float
            True,                   # Boolean True
            False,                  # Boolean False
            None,                   # None
            [],                     # Empty list
            [1, 2, 3],             # List with items
            {},                     # Empty dict
            {"key": "value"},       # Dict with items
            set(),                  # Empty set
            {1, 2, 3},             # Set with items
            lambda x: x,           # Function
        ]
        
        for invalid_input in invalid_inputs:
            result = analyze_text(invalid_input)
            assert result["errors"]["error_code"] == "INVALID_TYPE"
            assert result["risk_score"] == 0.0
            assert result["risk_category"] == "LOW"
    
    def test_f03_length_boundaries(self):
        """F-03: Test length boundary conditions"""
        # Exactly at limit
        text_5000 = "a" * 5000
        result = analyze_text(text_5000)
        assert result["processed_length"] == 5000
        assert "truncated" not in " ".join(result["trigger_reasons"]).lower()
        
        # Just over limit
        text_5001 = "a" * 5001
        result = analyze_text(text_5001)
        assert result["processed_length"] == 5000
        assert any("truncated" in reason.lower() for reason in result["trigger_reasons"])
        
        # Extremely long
        text_huge = "scam " * 10000  # 50,000 chars
        result = analyze_text(text_huge)
        assert result["processed_length"] == 5000
        assert any("truncated" in reason.lower() for reason in result["trigger_reasons"])

class TestScoringFailures:
    """Test all SCORING_FAILURE modes"""
    
    def test_f04_category_saturation_boundaries(self):
        """F-04: Test category saturation at exact boundaries"""
        # Exactly 3 keywords from same category = 0.6 (at cap)
        text_3_keywords = "kill murder attack"
        result = analyze_text(text_3_keywords)
        assert result["risk_score"] == 0.6
        
        # 4 keywords from same category should still cap at 0.6
        text_4_keywords = "kill murder attack assault"
        result = analyze_text(text_4_keywords)
        assert result["risk_score"] == 0.6
        
        # Many keywords from multiple categories will exceed 0.6 due to cross-category matches
        text_10_keywords = "kill murder attack assault stab shoot bomb explode terror gun"
        result = analyze_text(text_10_keywords)
        # This will be > 0.6 because "gun" and "bomb" are in both violence and weapons categories
        assert result["risk_score"] >= 0.6
        assert result["risk_score"] <= 1.0  # But still capped at 1.0
    
    def test_f06_score_overflow_boundaries(self):
        """F-06: Test score overflow at exact boundaries"""
        # Multiple categories hitting caps
        violence_keywords = "kill murder attack"  # 0.6
        fraud_keywords = "scam hack phish"        # 0.6
        
        combined_text = f"{violence_keywords} {fraud_keywords}"
        result = analyze_text(combined_text)
        
        # Should be clamped to 1.0, not 1.2
        assert result["risk_score"] == 1.0
        assert result["risk_category"] == "HIGH"
    
    def test_f09_confidence_score_boundaries(self):
        """F-09: Test confidence score boundary conditions"""
        # Single keyword, single category
        result = analyze_text("kill")
        assert 0.0 <= result["confidence_score"] <= 1.0
        
        # Multiple keywords, multiple categories
        result = analyze_text("kill scam")
        assert 0.0 <= result["confidence_score"] <= 1.0
        
        # No keywords
        result = analyze_text("hello world")
        assert result["confidence_score"] == 1.0

class TestProcessingFailures:
    """Test all PROCESSING_FAILURE modes"""
    
    def test_f05_substring_false_positives(self):
        """F-05: Test substring false positive prevention"""
        false_positive_cases = [
            ("studies", "die", False),      # "die" should NOT match in "studies"
            ("killed", "kill", False),      # "kill" should NOT match in "killed" (not word boundary)
            ("killer", "kill", False),      # "kill" should NOT match in "killer" (not word boundary)
            ("overkill", "kill", False),    # "kill" should NOT match in "overkill" (not word boundary)
            ("discarded", "scar", False),   # "scar" should NOT match in "discarded"
            ("scared", "scar", False),      # "scar" should NOT match in "scared"
            ("kill me", "kill", True),      # "kill" SHOULD match as separate word
            ("this scam", "scam", True),    # "scam" SHOULD match as separate word
            ("scammer here", "scammer", True),  # "scammer" is a separate keyword, should match
        ]
        
        for text, keyword, should_match in false_positive_cases:
            result = analyze_text(text)
            has_match = any(keyword in reason for reason in result["trigger_reasons"])
            
            if should_match:
                assert has_match, f"Expected '{keyword}' to match in '{text}' but it didn't"
            else:
                assert not has_match, f"Expected '{keyword}' NOT to match in '{text}' but it did"
    
    def test_f07_exception_handling(self):
        """F-07: Test that exceptions are caught and handled"""
        # This test verifies the try/catch works
        # We can't easily force an exception, but we can verify
        # that the error response structure is correct
        
        # Test with potentially problematic inputs
        problematic_inputs = [
            "\\x00\\x01\\x02",  # Control characters
            "🔥💀☠️",           # Unicode emojis
            "kill" * 1000,      # Repetitive pattern
        ]
        
        for problematic_input in problematic_inputs:
            result = analyze_text(problematic_input)
            # Should not crash, should return valid structure
            assert "risk_score" in result
            assert "risk_category" in result
            assert "trigger_reasons" in result
            assert "processed_length" in result
            assert "errors" in result
    
    def test_f08_determinism_validation(self):
        """F-08: Test determinism across multiple executions"""
        test_cases = [
            "hello world",
            "this is a scam",
            "kill attack bomb",
            "",
            "a" * 6000,
            123,
        ]
        
        for test_input in test_cases:
            # Run same input 50 times
            results = []
            for _ in range(50):
                result = analyze_text(test_input)
                # Convert to JSON string for comparison
                result_str = json.dumps(result, sort_keys=True)
                results.append(result_str)
            
            # All results should be identical
            unique_results = set(results)
            assert len(unique_results) == 1, f"Non-deterministic behavior for input: {test_input}"

class TestExtremeScoreEdges:
    """Test extreme scoring edge cases"""
    
    def test_minimum_score_boundary(self):
        """Test minimum possible score (0.0)"""
        result = analyze_text("hello beautiful world")
        assert result["risk_score"] == 0.0
        assert result["risk_category"] == "LOW"
    
    def test_maximum_score_boundary(self):
        """Test maximum possible score (1.0)"""
        # Create text that would exceed 1.0 without capping
        all_categories = [
            "kill murder attack",      # violence: 0.6
            "scam hack fraud",         # fraud: 0.6  
            "hate stupid idiot",       # abuse: 0.6
            "sex porn explicit",       # sexual: 0.6
            "drugs cocaine heroin",    # drugs: 0.6
        ]
        
        combined_text = " ".join(all_categories)
        result = analyze_text(combined_text)
        
        assert result["risk_score"] == 1.0  # Capped at 1.0
        assert result["risk_category"] == "HIGH"
    
    def test_threshold_boundaries(self):
        """Test exact threshold boundaries"""
        # Test LOW/MEDIUM boundary (0.3)
        # Need exactly 0.3: 1.5 keywords = impossible, so test around boundary
        
        # Just under MEDIUM threshold
        result_low = analyze_text("kill")  # 0.2
        assert result_low["risk_score"] == 0.2
        assert result_low["risk_category"] == "LOW"
        
        # At MEDIUM threshold
        result_medium = analyze_text("kill murder")  # 0.4
        assert result_medium["risk_score"] == 0.4
        assert result_medium["risk_category"] == "MEDIUM"
        
        # Just under HIGH threshold
        result_medium_high = analyze_text("kill murder attack")  # 0.6
        assert result_medium_high["risk_score"] == 0.6
        assert result_medium_high["risk_category"] == "MEDIUM"
        
        # At HIGH threshold (need 0.7+)
        result_high = analyze_text("kill murder attack scam")  # 0.8
        assert result_high["risk_score"] == 0.8
        assert result_high["risk_category"] == "HIGH"

class TestCaseVariations:
    """Test case sensitivity and normalization"""
    
    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive"""
        variations = [
            "kill",
            "KILL", 
            "Kill",
            "kIlL",
        ]
        
        expected_score = 0.2
        for variation in variations:
            result = analyze_text(variation)
            assert result["risk_score"] == expected_score
            assert result["risk_category"] == "LOW"
    
    def test_whitespace_normalization(self):
        """Test whitespace handling"""
        variations = [
            "kill scam",
            "  kill   scam  ",
            "\tkill\tscam\t",
            "\nkill\nscam\n",
            "kill    scam",
        ]
        
        expected_score = 0.4  # kill + scam
        for variation in variations:
            result = analyze_text(variation)
            assert result["risk_score"] == expected_score

class TestConcurrencyAndStress:
    """Test system behavior under stress"""
    
    def test_repeated_identical_requests(self):
        """Test 1000 identical requests for determinism"""
        test_input = "kill and scam attempt"
        
        results = []
        for _ in range(1000):
            result = analyze_text(test_input)
            result_hash = hashlib.sha256(
                json.dumps(result, sort_keys=True).encode()
            ).hexdigest()
            results.append(result_hash)
        
        # All hashes should be identical
        unique_hashes = set(results)
        assert len(unique_hashes) == 1, "Non-deterministic behavior detected"
    
    def test_boundary_stress_combinations(self):
        """Test combinations of boundary conditions"""
        stress_cases = [
            # Empty + invalid type (can't combine, but test sequence)
            ("", "EMPTY_INPUT"),
            (123, "INVALID_TYPE"),
            
            # Long + high risk
            ("kill scam " * 1000, None),  # Should truncate and score
            
            # Saturation + multiple categories
            ("kill murder attack assault stab shoot bomb explode scam hack fraud phish", None),
        ]
        
        for test_input, expected_error in stress_cases:
            result = analyze_text(test_input)
            
            if expected_error:
                assert result["errors"]["error_code"] == expected_error
            else:
                assert result["errors"] is None
                assert 0.0 <= result["risk_score"] <= 1.0
                assert result["risk_category"] in ["LOW", "MEDIUM", "HIGH"]

class TestErrorResponseStructure:
    """Test error response structure consistency"""
    
    def test_error_response_structure(self):
        """Test that all error responses have consistent structure"""
        error_cases = [
            ("", "EMPTY_INPUT"),
            (123, "INVALID_TYPE"),
        ]
        
        for test_input, expected_code in error_cases:
            result = analyze_text(test_input)
            
            # Verify structure
            assert "risk_score" in result
            assert "confidence_score" in result
            assert "risk_category" in result
            assert "trigger_reasons" in result
            assert "processed_length" in result
            assert "errors" in result
            
            # Verify error structure
            assert result["errors"]["error_code"] == expected_code
            assert "message" in result["errors"]
            
            # Verify safe defaults
            assert result["risk_score"] == 0.0
            assert result["risk_category"] == "LOW"
            assert result["trigger_reasons"] == []
            assert result["processed_length"] == 0

# Utility function for running all tests
def run_exhaustive_tests():
    """Run all boundary tests and report results"""
    import sys
    
    test_classes = [
        TestInputFailures,
        TestScoringFailures, 
        TestProcessingFailures,
        TestExtremeScoreEdges,
        TestCaseVariations,
        TestConcurrencyAndStress,
        TestErrorResponseStructure,
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n🧪 Running {test_class.__name__}...")
        
        instance = test_class()
        methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                print(f"  ✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All boundary tests passed!")
        return True
    else:
        print("⚠️  Some tests failed!")
        return False

if __name__ == "__main__":
    run_exhaustive_tests()