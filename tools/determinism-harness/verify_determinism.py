import sys
import os
import hashlib
import json
import logging
from datetime import datetime

# -------------------------------------------------
# PROJECT ROOT IMPORT
# -------------------------------------------------

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine import analyze_text  # Your scoring function

# -------------------------------------------------
# LOGGING SETUP
# -------------------------------------------------

LOG_DIR = "replay-test-logs"
os.makedirs(LOG_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(LOG_DIR, f"determinism_run_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("DeterminismHarness")

# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------

ITERATIONS = 1000

TEST_CASES = [
    "Safe content with no risk keywords.",
    "kill attack bomb - High risk content",
    "scam fraud - Medium risk content",
    "",
    "   whitespace   ",
    "A" * 5000,
    "A" * 5001,
    "Mixed CASE InPuT",
    "Special chars @#$%^&*",
    "Multi\nline\ninput"
]

# -------------------------------------------------
# HASH FUNCTION
# -------------------------------------------------

def get_hash(data):
    """
    Stable SHA256 hash of JSON-serializable object.
    Ensures deterministic ordering.
    """
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()

# -------------------------------------------------
# SAFE EXECUTION WRAPPER
# -------------------------------------------------

def safe_analyze(text):
    """
    Wrap analyze_text to ensure exceptions
    are treated deterministically.
    """
    try:
        result = analyze_text(text)
        return {"status": "success", "output": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# -------------------------------------------------
# DETERMINISM HARNESS
# -------------------------------------------------

def run_harness():
    logger.info("Starting Determinism Certification Run")
    logger.info(f"Iterations per test case: {ITERATIONS}")

    all_passed = True
    results_snapshot = []

    for idx, test_input in enumerate(TEST_CASES):
        logger.info(f"\nTesting Case {idx+1}/{len(TEST_CASES)}")

        baseline_result = safe_analyze(test_input)
        baseline_hash = get_hash(baseline_result)

        divergence_detected = False

        for i in range(ITERATIONS):
            current_result = safe_analyze(test_input)
            current_hash = get_hash(current_result)

            if current_hash != baseline_hash:
                logger.error(f"DIVERGENCE DETECTED at iteration {i}")
                logger.error(f"Expected Hash: {baseline_hash}")
                logger.error(f"Current  Hash: {current_hash}")
                divergence_detected = True
                all_passed = False
                break

        if not divergence_detected:
            logger.info(f"PASS: {ITERATIONS} identical executions.")
            results_snapshot.append({
                "input": test_input,
                "hash": baseline_hash,
                "iterations": ITERATIONS,
                "output_sample": baseline_result
            })
        else:
            logger.error("FAIL: Determinism violated.")

    # Save certification snapshot
    snapshot_file = os.path.join(LOG_DIR, "determinism_snapshot.json")
    with open(snapshot_file, "w") as f:
        json.dump(results_snapshot, f, indent=4)

    # Final result
    if all_passed:
        logger.info("\nDETERMINISM CERTIFIED: Zero divergence detected.")
        print("\nDeterminism verification SUCCESS.")
        print(f"Logs written to: {LOG_DIR}/")
    else:
        logger.error("\nDETERMINISM FAILURE: Divergence detected.")
        print("\nDeterminism verification FAILED.")
        print(f"Check logs in: {LOG_DIR}/")
        sys.exit(1)


if __name__ == "__main__":
    run_harness()






# import sys
# import os
# import hashlib
# import json
# import logging
# from datetime import datetime

# # Add project root to path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from app.engine import analyze_text

# # Configure logging
# LOG_DIR = "replay-test-logs"
# os.makedirs(LOG_DIR, exist_ok=True)
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# log_file = os.path.join(LOG_DIR, f"determinism_run_{timestamp}.log")

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(message)s",
#     handlers=[
#         logging.FileHandler(log_file),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger("DeterminismHarness")

# def get_hash(data):
#     """Generate SHA-256 hash of a dictionary."""
#     return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

# def run_harness():
#     logger.info("Starting Determinism Certification Run (1000+ Iterations)")
    
#     test_cases = [
#         "Safe content with no risk keywords.",
#         "kill attack bomb - High risk content",
#         "scam fraud - Medium risk content",
#         "",  # Empty string
#         "   whitespace   ",  # Whitespace
#         "A" * 5000,  # Max length
#         "A" * 5001,  # Over max length
#         "Mixed CASE InPuT",
#         "Special chars @#$%^&*",
#         "Multi\nline\ninput"
#     ]
    
#     iterations = 1000
#     all_passed = True
    
#     for idx, test_input in enumerate(test_cases):
#         logger.info(f"Testing Case {idx+1}/{len(test_cases)}: {repr(test_input)[:50]}...")
        
#         # Initial run to establish baseline
#         baseline = analyze_text(test_input)
#         baseline_hash = get_hash(baseline)
        
#         divergence_count = 0
        
#         for i in range(iterations):
#             current = analyze_text(test_input)
#             current_hash = get_hash(current)
            
#             if current_hash != baseline_hash:
#                 divergence_count += 1
#                 logger.error(f"DIVERGENCE DETECTED at iteration {i} for input: {repr(test_input)}")
#                 logger.error(f"Expected hash: {baseline_hash}")
#                 logger.error(f"Got hash: {current_hash}")
#                 all_passed = False
#                 break
        
#         if divergence_count == 0:
#             logger.info(f"  PASS: {iterations} runs identical. Hash: {baseline_hash}")
#         else:
#             logger.error(f"  FAIL: Divergence detected.")
            
#     if all_passed:
#         logger.info("DETERMINISM CERTIFIED: Zero divergence across all test cases.")
#         print("\nDeterminism verification SUCCESS. Logs written to replay-test-logs/")
#     else:
#         logger.error("DETERMINISM FAILURE: Divergence detected.")
#         print("\nDeterminism verification FAILED. Check logs in replay-test-logs/")
#         sys.exit(1)

# if __name__ == "__main__":
#     run_harness()
