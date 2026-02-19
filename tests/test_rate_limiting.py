import pytest
import time
import tracemalloc
from app.engine import analyze_text, MAX_TEXT_LENGTH

class MockRateLimiter:
    """
    Simulates a Token Bucket limiter for infrastructure protection.
    Capacity: 100 tokens
    Refill: 50 tokens/sec
    """
    def __init__(self):
        self.capacity = 100
        self.tokens = 100
        self.last_refill = time.time()
        self.refill_rate = 50 # tokens/sec
        
    def allow_request(self):
        now = time.time()
        elapsed = now - self.last_refill
        
        # Refill
        if elapsed > 0.1:
            refill = int(elapsed * self.refill_rate)
            self.tokens = min(self.capacity, self.tokens + refill)
            self.last_refill = now
            
        if self.tokens > 0:
            self.tokens -= 1
            return True
        return False

def test_memory_growth_under_stress():
    """
    Verifies that processing a large input doesn't spike memory usage unreasonably.
    """
    tracemalloc.start()
    
    # Baseline
    snapshot1 = tracemalloc.take_snapshot()
    
    # Stress Input (5000 chars of keywords)
    text = "kill " * 1000
    analyze_text(text)
    
    # Peak
    snapshot2 = tracemalloc.take_snapshot()
    
    # Calculate Diff
    stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    total_diff = sum(stat.size_diff for stat in stats)
    mem_mb = total_diff / (1024 * 1024)
    
    tracemalloc.stop()
    
    # Assert that memory growth is less than 5MB
    # This ensures no massive leaks or allocations per request
    print(f"Memory Alloc Delta: {mem_mb:.4f} MB")
    assert mem_mb < 5.0, f"Memory spike too high: {mem_mb:.2f} MB"

def test_rate_limiter_simulation():
    """
    Simulates a flood of 1000 requests against a rate-limited host.
    Ensures that the limiter actually rejects requests when overwhelmed.
    """
    limiter = MockRateLimiter()
    accepted = 0
    rejected = 0
    
    start = time.time()
    # Burst 1000 requests
    for _ in range(1000):
        if limiter.allow_request():
            analyze_text("test")
            accepted += 1
        else:
            rejected += 1
            
    duration = time.time() - start
    
    print(f"Accepted: {accepted}, Rejected: {rejected}")
    
    # We expect significant rejection in a flood scenario
    assert rejected > 0
    assert accepted < 1000
