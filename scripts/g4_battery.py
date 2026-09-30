"""
Antar — Gate G4 Battery (QuickML LLM contract test)
========================================================
Run: python -m scripts.g4_battery        (from antar-backend/, .env filled)

Tests the LLM serving path the agents depend on. Records:
  • JSON reliability  — 10 JSON-instruction prompts → % valid after repair (target ≥ 9/10)
  • Latency           — 5 timed calls → p50/p95 (target < 4 s)
  • Kannada quality   — 5 KN generations → printed verbatim for M2 to grade 1–5

⚠️ IMPORTANT (read docs/quickml_llm_access.md first):
   This battery calls app.services.quickml.quickml_generate(), which currently uses an
   httpx REST path whose endpoint URL + response shape are [VERIFY G4]. If those calls
   fail with 404/auth errors, the LLM is likely served via the SDK
   `app.quick_ml().predict(endpoint_key, input_data)` instead — switch quickml.py to that
   path (see the doc) and re-run. Do NOT trust this battery's numbers until the calls
   actually return Qwen output.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.quickml import quickml_generate, parse_json_response

JSON_SYSTEM = "You output ONLY valid JSON. No prose, no markdown."
JSON_PROMPTS = [
    'Classify intent. Return {"intent": "<QUERY|NETWORK|PROFILE|FORECAST|SOCIAL>"}. Message: "show robbery trend in Bengaluru North"',
    'Return {"intent": "..."} for: "who are the associates of suspect Raju K"',
    'Return {"intent": "..."} for: "predict next week hotspots for theft"',
    'Return {"intent": "..."} for: "age and gender breakdown of theft victims"',
    'Return {"intent": "..."} for: "risk score of suspect S0001"',
    'Extract entities. Return {"zones":[],"crime_types":[],"date_range":null}. Message: "chain snatching in Rajajinagar last 3 months"',
    'Return {"template_id":"T3","params":{"crime_type":"robbery","zone":"Bengaluru North","months":3}} format for: "robbery trend Bengaluru North 3 months"',
    'Return {"ok": true, "count": 3} exactly.',
    'Return a JSON array of 3 crime types: ["...","...","..."]',
    'Return {"answer":"...","citations":[{"fir":"...","station":"..."}]} for a one-FIR theft answer.',
]

KN_SYSTEM = "You are a Karnataka police assistant. Reply in clear, natural Kannada."
KN_PROMPTS = [
    "ರಾಜಾಜಿನಗರದಲ್ಲಿ ಕಳೆದ ವಾರ 8 ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ ಎಂದು ಒಂದು ವಾಕ್ಯದಲ್ಲಿ ಹೇಳಿ.",
    "ಸಂಶಯಿತ ರಾಜು ಕೆ ಬಗ್ಗೆ ಒಂದು ಸಣ್ಣ ಸಾರಾಂಶ ಬರೆಯಿರಿ.",
    "ಬೆಂಗಳೂರು ಉತ್ತರದಲ್ಲಿ ದರೋಡೆ ಪ್ರಕರಣಗಳು ಹೆಚ್ಚಾಗಿವೆ ಎಂದು ಎಚ್ಚರಿಕೆ ನೀಡಿ.",
    "ಈ ವಾರಾಂತ್ಯದಲ್ಲಿ ಯಾವ ಪ್ರದೇಶದಲ್ಲಿ ಗಸ್ತು ಹೆಚ್ಚಿಸಬೇಕು ಎಂದು ಸೂಚಿಸಿ.",
    "ಸರಗಳ್ಳತನ ತಡೆಗಟ್ಟಲು ಎರಡು ಸಲಹೆಗಳನ್ನು ನೀಡಿ.",
]


async def run() -> None:
    print("=" * 60)
    print("GATE G4 BATTERY — QuickML LLM contract")
    print("=" * 60)

    # 1. JSON reliability
    print("\n[1] JSON reliability (target ≥ 9/10 valid after repair)")
    valid = 0
    for i, p in enumerate(JSON_PROMPTS, 1):
        await asyncio.sleep(0.8)   # space calls — avoid hammering the endpoint (reduces 500s)
        try:
            raw = await quickml_generate(system=JSON_SYSTEM, user=p, json_mode=True,
                                         max_tokens=256, temperature=0.1)
            try:
                parse_json_response(raw)
                valid += 1
                print(f"   {i:>2}. ✓ valid")
            except Exception:
                print(f"   {i:>2}. ✗ invalid → {raw[:80]!r}")
        except Exception as e:
            print(f"   {i:>2}. ✗ CALL FAILED → {e}")
    print(f"   → {valid}/10 valid  ({'PASS' if valid >= 9 else 'FAIL — harden repair/few-shot'})")

    # 2. Latency
    print("\n[2] Latency (target p95 < 4 s)")
    times = []
    for i in range(5):
        t0 = time.time()
        try:
            await quickml_generate(system="You are concise.", user="Say OK.", max_tokens=16)
            dt = time.time() - t0
            times.append(dt)
            print(f"   call {i+1}: {dt:.2f}s")
        except Exception as e:
            print(f"   call {i+1}: FAILED → {e}")
    if times:
        times.sort()
        p50 = statistics.median(times)
        p95 = times[int(len(times) * 0.95) - 1] if len(times) > 1 else times[0]
        print(f"   → p50={p50:.2f}s  p95={p95:.2f}s  ({'PASS' if p95 < 4 else 'FAIL'})")

    # 3. Kannada quality (M2 grades)
    print("\n[3] Kannada generation (M2 grades each 1–5 for fluency + correctness)")
    for i, p in enumerate(KN_PROMPTS, 1):
        try:
            out = await quickml_generate(system=KN_SYSTEM, user=p, max_tokens=200, temperature=0.3)
            print(f"\n   KN-{i} prompt: {p}")
            print(f"   KN-{i} output: {out}")
        except Exception as e:
            print(f"   KN-{i}: FAILED → {e}")

    print("\n" + "=" * 60)
    print("Record results + locked decision in docs/gates.md (G4 section).")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
