import time
import asyncio
import sys
import pathlib

# Add the backend root to the path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app.second_brain.retrieval import semantic_recall
from app.second_brain.index import brain_index

# Force index to be loaded if lazy
if hasattr(brain_index, "_matrix"):
    _ = brain_index.size

QUERIES = [
    "suspect with history of property theft",
    "cyber fraud using fake bank accounts",
    "stolen two wheeler in Jayanagar",
    "organized syndicate running illegal betting",
    "gang assault near railway station"
]

def run_benchmark(iterations: int = 100):
    print(f"Benchmarking semantic_recall with {iterations} iterations...")
    
    # Warmup
    for q in QUERIES:
        semantic_recall(q, k=3)
        
    start_time = time.time()
    
    for i in range(iterations):
        query = QUERIES[i % len(QUERIES)]
        # We set use_hybrid=False to avoid calling LLM during benchmark if it's set to True
        semantic_recall(query, k=3, use_hybrid=False)
        
    total_time = time.time() - start_time
    avg_latency_ms = (total_time / iterations) * 1000
    
    print(f"Total time: {total_time:.4f} seconds")
    print(f"Average latency per query: {avg_latency_ms:.2f} ms")
    
    if avg_latency_ms <= 30:
        print("SUCCESS: Latency is <= 30 ms")
    else:
        print("WARNING: Latency exceeds 30 ms target")

if __name__ == "__main__":
    run_benchmark()
