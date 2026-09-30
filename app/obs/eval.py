import time
import json
from pathlib import Path

from app.obs.store import conn
from app.core.settings import settings
from app.agents.query_agent import query_agent_run, _QUERY_CACHE

EVALSET_PATH = Path(__file__).resolve().parent / "evalset.jsonl"

async def run_evaluation_suite(run_id: str) -> None:
    if not EVALSET_PATH.exists():
        print(f"Eval set not found at {EVALSET_PATH}")
        return

    cases = []
    with open(EVALSET_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    
    passed = 0
    total_grounded = 0.0
    latencies = []
    
    print(f"Running Eval Suite ({len(cases)} cases) for version {getattr(settings, 'PROMPT_VERSION', 'v1')}...")
    
    for case in cases:
        _QUERY_CACHE.clear() # clear cache to get true latency
        t0 = time.time()
        
        try:
            res = await query_agent_run(case["question"], lang=case.get("lang", "en"), session_id=f"eval-{run_id}")
            ms = int((time.time() - t0) * 1000)
            latencies.append(ms)
            
            # Simple offline checks
            template_match = (res.get("template_id") == case["expect_template"])
            disclaim_match = bool(res.get("entity_not_found")) == case.get("must_disclaim", False)
            
            # Simulate a quick groundedness score for the eval
            grounded_score = 1.0 if not res.get("guardrail_violations") and not res.get("entity_not_found") else 0.5
            if disclaim_match and case.get("must_disclaim"):
                grounded_score = 1.0
            
            is_pass = template_match and disclaim_match
            if is_pass:
                passed += 1
            total_grounded += grounded_score
            
            with conn() as c:
                c.execute("""
                    INSERT INTO eval_cases (run_id, case_id, question, expected, got, passed, grounded)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (run_id, case["case_id"], case["question"], case["expect_template"], res.get("template_id"), int(is_pass), grounded_score))
                
            print(f"  [{'PASS' if is_pass else 'FAIL'}] {case['case_id']} - {ms}ms")
            
        except Exception as e:
            print(f"  [ERR] {case['case_id']}: {e}")
            with conn() as c:
                c.execute("""
                    INSERT INTO eval_cases (run_id, case_id, question, expected, got, passed, grounded)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (run_id, case["case_id"], case["question"], case["expect_template"], "ERROR", 0, 0.0))
    
    pass_rate = passed / len(cases) if cases else 0.0
    avg_grounded = total_grounded / len(cases) if cases else 0.0
    latencies.sort()
    p95_ms = latencies[int(len(latencies)*0.95)] if latencies else 0.0
    
    ts = int(time.time() * 1000)
    with conn() as c:
        c.execute("""
            INSERT INTO eval_runs (run_id, prompt_version, model, ts, n, pass_rate, avg_grounded, p95_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, getattr(settings, "PROMPT_VERSION", "v1"), settings.QUICKML_CHAT_MODEL, ts, len(cases), pass_rate, avg_grounded, p95_ms))
        
    print(f"\n✅ Eval Run Complete: {pass_rate*100:.1f}% pass | Avg Grounded: {avg_grounded:.2f} | P95: {p95_ms}ms")
