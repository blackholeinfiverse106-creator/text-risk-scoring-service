from app.engine import analyze_text
import time

TEST_TEXT = "kill and scam"

results = []
times = []

for i in range(100):
    start = time.time()
    result = analyze_text(TEST_TEXT)
    end = time.time()

    results.append(result)
    times.append(end - start)

# Verify determinism
all_same = all(r == results[0] for r in results)

print("Deterministic:", all_same)
print("Example result:", results[0])
print("Max time:", max(times))
print("Min time:", min(times))
