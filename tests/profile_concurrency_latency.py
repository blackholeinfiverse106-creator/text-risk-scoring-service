import concurrent.futures
import time
import statistics
import json
import sys
import os

# Allow running from anywhere
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine import analyze_text

def task(i):
    start = time.perf_counter()
    # Mixed load: some short, some long
    if i % 2 == 0:
        text = "kill " * 20 + " scam " * 20
    else:
        text = "hello world " * 50
        
    analyze_text(text)
    duration = (time.perf_counter() - start) * 1000 # ms
    return duration

def profile_concurrency():
    """
    Measures latency under load: 50 threads, 1000 requests total.
    """
    latencies = []
    TOTAL_REQUESTS = 1000
    CONCURRENCY = 50
    
    print(f"Starting Concurrency Profile ({TOTAL_REQUESTS} reqs, {CONCURRENCY} threads)...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(task, i) for i in range(TOTAL_REQUESTS)]
        
        for future in concurrent.futures.as_completed(futures):
            latencies.append(future.result())
            
    # Stats
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]
    p99 = statistics.quantiles(latencies, n=100)[98]
    mean = statistics.mean(latencies)
    max_lat = max(latencies)
    
    print(f"Mean: {mean:.2f}ms")
    print(f"P50:  {p50:.2f}ms")
    print(f"P95:  {p95:.2f}ms")
    print(f"P99:  {p99:.2f}ms")
    print(f"Max:  {max_lat:.2f}ms")
    
    # Generate Artifact
    report = {
        "status": "PASSED" if p99 < 100 else "WARNING", 
        "concurrency": CONCURRENCY,
        "total_requests": TOTAL_REQUESTS,
        "mean_latency_ms": round(mean, 2),
        "p99_latency_ms": round(p99, 2),
        "max_latency_ms": round(max_lat, 2)
    }
    
    with open("concurrency_benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Artifact generated: concurrency_benchmark_report.json")

if __name__ == "__main__":
    profile_concurrency()
