import asyncio
import httpx
import time
import json
import statistics
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

import random

BASE_URL = "http://localhost:9000"
CONCURRENCY = 500
REQUESTS_PER_WORKER = 2  # Total requests = CONCURRENCY * REQUESTS_PER_WORKER

QUERIES = [
    "Show me the most recent thefts in Rajajinagar",
    "Who are the top 5 suspects by risk score?",
    "What crime anomalies are detected this week?",
    "Show the criminal network for suspect S0001",
    "How many chain snatching incidents happened in the last 30 days?",
    "ರಾಜಾಜಿನಗರದಲ್ಲಿ ಇತ್ತೀಚಿನ ಕಳ್ಳತನಗಳನ್ನು ತೋರಿಸಿ"
]

async def worker(worker_id: int, client: httpx.AsyncClient, results: list):
    for i in range(REQUESTS_PER_WORKER):
        q = random.choice(QUERIES)
        payload = {
            "text": q,
            "session_id": f"loadtest-w{worker_id}-r{i}",
            "lang": "kn" if "ರಾಜಾ" in q else "en"
        }
        
        t0 = time.time()
        try:
            r = await client.post(f"{BASE_URL}/api/chat", json=payload, timeout=60.0)
            elapsed = time.time() - t0
            
            if r.status_code == 200:
                results.append({"status": "OK", "latency": elapsed})
            else:
                results.append({"status": f"ERR_{r.status_code}", "latency": elapsed})
        except Exception as e:
            elapsed = time.time() - t0
            results.append({"status": "ERR_EXCEPTION", "latency": elapsed})


async def main():
    print("=" * 60)
    print(f" Antar High-Concurrency Load Test ({CONCURRENCY} Users)")
    print("=" * 60)
    
    # Warmup check
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{BASE_URL}/api/health")
        except:
            print("[ERROR] Server is not reachable at", BASE_URL)
            sys.exit(1)
            
    print(f"Targeting {BASE_URL}/api/chat")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Total Requests: {CONCURRENCY * REQUESTS_PER_WORKER}")
    
    results = []
    
    t0 = time.time()
    
    # Run workers
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=CONCURRENCY + 50)) as client:
        tasks = [worker(i, client, results) for i in range(CONCURRENCY)]
        await asyncio.gather(*tasks)
        
    total_time = time.time() - t0
    
    print("\n--- Load Test Results ---")
    
    total_requests = len(results)
    success = [r for r in results if r["status"] == "OK"]
    errors = [r for r in results if r["status"] != "OK"]
    
    if success:
        latencies = [r["latency"] * 1000 for r in success]
        avg_lat = statistics.mean(latencies)
        p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
        max_lat = max(latencies)
    else:
        avg_lat = p95_lat = max_lat = 0.0
        
    qps = total_requests / total_time
    
    print(f"Total Time:       {total_time:.2f} seconds")
    print(f"Total Requests:   {total_requests}")
    print(f"Success Rate:     {(len(success)/total_requests)*100:.1f}% ({len(success)} OK, {len(errors)} ERR)")
    print(f"Throughput (QPS): {qps:.2f} req/s")
    print(f"Avg Latency:      {avg_lat:.1f} ms")
    print(f"p95 Latency:      {p95_lat:.1f} ms")
    print(f"Max Latency:      {max_lat:.1f} ms")
    
    if qps >= 30:
        print("\n✅ QPS target achieved (>= 30)")
    else:
        print("\n⚠️ QPS target missed (< 30)")

if __name__ == "__main__":
    asyncio.run(main())
