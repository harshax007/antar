"""
Test end-to-end demo questions through Antar's query agent & services.
"""
import sys
import asyncio
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import os
os.environ["ANTAR_EDITION"] = "lab"
os.environ["ANTAR_DB"] = str(ROOT / "main_lab.db")

from app.agents.query_agent import query_agent_run
from app.agents.network_agent import build_network
from app.agents.profile_agent import compute_profile
import sqlite3

async def run_test():
    print("================ TESTING CHAT / QUERY AGENT ON STORYLINES ================")
    
    questions = [
        "Show me every FIR connected to accused ACC-KA-100017",
        "Which FIRs share vehicle KA-25-EH-4471?",
        "Who else paid into rakesh.pay@ybl?",
        "How many FIRs are registered in Bengaluru City in 2023?",
        "What is the conviction rate for theft in Bengaluru City?",
    ]
    
    for q in questions:
        print(f"\n--- Testing Query: \"{q}\" ---")
        try:
            res = await query_agent_run(q)
            text = res.get("text", "")
            citations = res.get("citations", [])
            print(f"Result (first 250 chars):\n{text[:250]}...")
            print(f"Citations count: {len(citations)}")
            if citations:
                print(f"Sample citation: {citations[0]}")
        except Exception as e:
            print(f"Query error: {e}")

    print("\n================ TESTING NETWORK & PROFILE FOR DEMO ================")
    print("Testing Suspect S0001 (Raju K.):")
    prof = compute_profile("S0001")
    print(f"Profile: Name={prof['full_name']}, Risk={prof['risk_score']}, Associates={len(prof['associates'])}")
    print(f"MO Summary: {prof['mo_summary']}")
    print(f"Leads: {prof['leads']}")
    
    net = build_network("S0001")
    print(f"Network: Nodes={len(net['nodes'])}, Edges={len(net['edges'])}, Banner={net.get('brain_banner')}")

if __name__ == "__main__":
    asyncio.run(run_test())
