import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import concurrent.futures
import time
import statistics
import random
from app.engine import analyze_text, MAX_TEXT_LENGTH

# Simulation parameters
CONCURRENT_REQUESTS = 50
TOTAL_REQUESTS = 1000
TEXT_SAMPLES = [
    "safe text",
    "kill " * 50, # High CPU
    "fraud " * 20,
    "short",
    "A" * MAX_TEXT_LENGTH
]

def make_request(req_id):
    text = random.choice(TEXT_SAMPLES)
    start = time.time()
    try:
        res = analyze_text(text)
        duration = time.time() - start
        return duration, None
    except Exception as e:
        return 0, str(e)

def run_stress_test():
    print(f"Starting Concurrency Stress Test: {TOTAL_REQUESTS} total requests, {CONCURRENT_REQUESTS} concurrent threads")
    
    latencies = []
    errors = []
    
    start_global = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(make_request, i) for i in range(TOTAL_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            duration, error = future.result()
            if error:
                errors.append(error)
            else:
                latencies.append(duration * 1000) # Convert to ms

    total_time = time.time() - start_global
    
    if not latencies:
        print("No successful requests!")
        return

    # Calculate Verification Metrics
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]
    p99 = statistics.quantiles(latencies, n=100)[98]
    max_lat = max(latencies)
    
    print("-" * 40)
    print(f"Total Time: {total_time:.2f}s")
    print(f"Throughput: {TOTAL_REQUESTS / total_time:.2f} req/s")
    print(f"Errors: {len(errors)}")
    print("-" * 40)
    print(f"Latency P50: {p50:.2f}ms")
    print(f"Latency P95: {p95:.2f}ms")
    print(f"Latency P99: {p99:.2f}ms")
    print(f"Latency Max: {max_lat:.2f}ms")
    print("-" * 40)

    if len(errors) > 0:
        print("FAILURE: Concurrent errors detected.")
        exit(1)
    else:
        print("SUCCESS: Concurrency test passed.")

if __name__ == "__main__":
    run_stress_test()
