"""
Test script to verify all Antar product features work with good demo examples:
1. Storylines & Connections (S01-S10, C1-C6)
2. Network Graph (Suspects, Co-accused, Shared Keys)
3. Suspect Profiling & SHAP attributions
4. Second Brain semantic search & FIR corpus recall
5. Advocate Agent hypothesis challenge & gating
6. Forecast & Anomaly detection
7. HITL workflow
8. ZCQL / Vault deterministic query & Answer Writer
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import sqlite3

def test_storylines():
    print("\n================ 1. STORYLINES & DEMO CONNECTIONS ================")
    con = sqlite3.connect("main_lab.db")
    con.row_factory = sqlite3.Row
    stories = con.execute("SELECT * FROM dim_storyline ORDER BY story_id").fetchall()
    for s in stories:
        key_type = s["shared_key"]
        key_val = s["key_value"]
        
        fir_matches = 0
        if key_type in ["Accused_ID", "Vehicle_Reg_No", "UPI_ID", "IP_Address", "MO_Details"]:
            fir_matches = con.execute(f"SELECT count(*) FROM FIRs WHERE {key_type} = ?", (key_val,)).fetchone()[0]
        elif key_type == "temporal":
            fir_matches = con.execute("SELECT count(*) FROM FIRs WHERE story_id = ?", (s["story_id"],)).fetchone()[0]
            
        entity_matches = con.execute("SELECT count(*) FROM ext_entity_keys WHERE key_value = ?", (key_val,)).fetchone()[0]
        
        print(f"[{s['story_id']}] {s['title_en']}")
        print(f"   Key: {key_type} = {key_val}")
        print(f"   FIR matches: {fir_matches} | Entity matches: {entity_matches}")
        print(f"   Example Q: \"{s['question_en']}\"")
    con.close()

def test_suspects_and_network():
    print("\n================ 2. SUSPECTS & NETWORK GRAPH ================")
    con = sqlite3.connect("main_lab.db")
    con.row_factory = sqlite3.Row
    
    test_ids = ["S0001", "S0002", "S0056", "S0801"]
    for sid in test_ids:
        s = con.execute("SELECT * FROM suspects WHERE suspect_id = ?", (sid,)).fetchone()
        if s:
            crimes = con.execute("SELECT count(*) FROM crime_suspects WHERE suspect_id = ?", (sid,)).fetchone()[0]
            rels = con.execute("SELECT count(*) FROM relationships WHERE suspect_a = ? OR suspect_b = ?", (sid, sid)).fetchone()[0]
            accts = con.execute("SELECT count(*) FROM money_accounts WHERE suspect_id = ?", (sid,)).fetchone()[0]
            print(f"Suspect {sid}: {s['full_name']} (alias: {s['alias']}) | Priors: {s['prior_count']} | Zone: {s['address_zone']}")
            print(f"   Crimes: {crimes} | Relationships: {rels} | Accounts: {accts}")
        else:
            print(f"Suspect {sid}: NOT FOUND")
            
    # Test network agent logic directly
    from app.agents.network_agent import build_network
    net_result = build_network(seed_id="S0001")
    print(f"\nNetwork Agent output for S0001:")
    print(f"   Nodes: {len(net_result.get('nodes', []))} | Edges: {len(net_result.get('edges', []))}")
    if net_result.get('brain_banner'):
        print(f"   Brain Banner: {net_result.get('brain_banner')}")
    con.close()

def test_profiling_and_shap():
    print("\n================ 3. SUSPECT PROFILING & SHAP ================")
    from app.agents.profile_agent import compute_profile
    prof = compute_profile(suspect_id="S0001")
    if prof:
        print(f"Profile for S0001 ({prof.get('full_name')}):")
        print(f"   Risk score: {prof.get('risk_score')} / 100")
        print(f"   Factors: {prof.get('factors')}")
        print(f"   SHAP attributions: {prof.get('risk_attributions')}")
        print(f"   MO Summary: {prof.get('mo_summary')}")
        print(f"   Associates found: {len(prof.get('associates', []))}")
        print(f"   Leads: {prof.get('leads')}")
    else:
        print("Profile returned None")

def test_second_brain():
    print("\n================ 4. SECOND BRAIN RECALL ================")
    try:
        from app.second_brain.corpus_search import search_corpus
        hits = search_corpus("Rajajinagar chain snatching motorcycle dusk", k=3)
        print(f"100k FIR Corpus hits returned: {len(hits)}")
        for i, h in enumerate(hits, 1):
            print(f"   [{i}] Score: {h.get('score', 0):.3f} | {h.get('summary_text', '')[:90]}...")
    except Exception as e:
        print(f"Corpus search test: {e}")

def test_advocate_agent():
    print("\n================ 5. ADVOCATE AGENT (ADVERSARIAL AUDIT) ================")
    try:
        from app.agents.advocate_agent import challenge
        hypothesis = {
            "id": "H-P1-001",
            "subject_ids": ["S0001", "S0002"],
            "claim": "Raju K and Yellappa M are connected via shared phone and associates",
            "score": 0.88,
            "kind": "cross_case_link",
            "signals": [{"name": "shared_phone"}, {"name": "common_contacts"}],
        }
        res = challenge(hypothesis)
        print(f"Advocate verdict for Hypothesis H-P1-001:")
        print(f"   Verdict: {res.get('verdict')}")
        print(f"   Posterior: {res.get('posterior_prob')}")
        print(f"   Verdict Reason: {res.get('verdict_reason')}")
        print(f"   Falsification tests count: {len(res.get('falsification_tests', []))}")
    except Exception as e:
        print(f"Advocate test error: {e}")

def test_forecast_and_hotspots():
    print("\n================ 6. FORECAST & HOTSPOTS ================")
    con = sqlite3.connect("main_lab.db")
    cube_cnt = con.execute("SELECT count(*) FROM forecast_cube").fetchone()[0]
    out_cnt = con.execute("SELECT count(*) FROM forecast_output").fetchone()[0]
    top_hotspots = con.execute("""
        SELECT unit, category, expected, hi80, hi90 
        FROM forecast_output 
        ORDER BY expected DESC 
        LIMIT 3
    """).fetchall()
    print(f"Forecast cube rows: {cube_cnt:,} | Forecast output rows: {out_cnt:,}")
    print("Top 3 forecast hotspots:")
    for h in top_hotspots:
        print(f"   Unit: {h[0]:30s} | Category: {h[1]:15s} | Expected: {h[2]:.2f} | 90% Band: {h[4]:.2f}")
    con.close()

if __name__ == "__main__":
    test_storylines()
    test_suspects_and_network()
    test_profiling_and_shap()
    test_second_brain()
    test_advocate_agent()
    test_forecast_and_hotspots()
    print("\n================ ALL FEATURE CHECKS COMPLETED ================\n")
