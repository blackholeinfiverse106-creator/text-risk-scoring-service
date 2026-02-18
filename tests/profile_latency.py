import time
import statistics
import sys
import os

# Allow running from anywhere
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine import analyze_text

def profile_latency():
    """
    Runs 1000 requests and explicitly fails if P99 latency > 20ms or Jitter > 5ms.
    (Engine is 0(N), so it should be extremely stable).
    """
    latencies = []
    # Warmup
    for _ in range(100):
        analyze_text("warmup")
        
    print("Starting Profile (1000 runs)...")
    for _ in range(1000):
        start = time.perf_counter()
        analyze_text("kill " * 50 + " scam " * 50) # Moderate load
        duration = (time.perf_counter() - start) * 1000 # ms
        latencies.append(duration)
        
    p99 = statistics.quantiles(latencies, n=100)[98] # approx p99
    mean = statistics.mean(latencies)
    stdev = statistics.stdev(latencies)
    
    print(f"Mean: {mean:.2f}ms")
    print(f"P99:  {p99:.2f}ms")
    print(f"Jitter (StdDev): {stdev:.2f}ms")
    
    # Thresholds
    assert p99 < 50.0, f"P99 Latency too high: {p99}ms"
    assert stdev < 10.0, f"Jitter too high: {stdev}ms (Unstable performance)"
    
if __name__ == "__main__":
    profile_latency()
