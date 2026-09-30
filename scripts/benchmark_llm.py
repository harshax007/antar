import time
import numpy as np
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app

# ponytail: minimal script to measure backend processing latency locally

def run_benchmarks():
    client = TestClient(app)
    latencies = []
    
    print("Running benchmarks...")
    for _ in range(10):
        start = time.perf_counter()
        resp = client.post("/api/chat", json={"text": "show chain snatching in Rajajinagar"})
        latencies.append(time.perf_counter() - start)
        assert resp.status_code == 200
        
    p50 = np.percentile(latencies, 50) * 1000
    p95 = np.percentile(latencies, 95) * 1000
    
    res = f"Latency for /api/chat: p50={p50:.2f}ms, p95={p95:.2f}ms\n"
    print(res)
    
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs"))
    os.makedirs(docs_dir, exist_ok=True)
    with open(os.path.join(docs_dir, "benchmarks.md"), "a", encoding="utf-8") as f:
        f.write("\n## Local Backend Benchmark\n" + res)

if __name__ == "__main__":
    run_benchmarks()
