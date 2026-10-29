"""
Antar — is every demo scenario live for a given day?
===================================================

    python scripts/demo_check.py                      # today
    python scripts/demo_check.py --date 2026-10-29    # preview demo day from any day
    python scripts/demo_check.py --full               # also load the embedder (Kannada recall)

Read-only: it reads the register, runs the anomaly scan and the question router, and
writes nothing (no chat turns, no audit rows). Each line is PASS / WARN / FAIL with what
it measured; exit code 1 on any FAIL. Run it every morning of demo week, and the morning of
29 Oct before anything else.

The run-sheet questions it routes are the ones in docs/DEMO_DAY_29OCT.md.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# (question, language, template it must route to) - the run sheet, in order
RUN_SHEET = [
    ("Which districts had the most murders in 2022?", "en", "T11"),
    ("Top beats for burglary in Bengaluru City", "en", "T23"),
    ("chain snatching in Rajajinagar last month", "en", "T1"),
    ("ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು", "kn", "T1"),
    ("who is Raju K", "en", "T2"),
    ("FIRs for UPI suman68@ybl", "en", "T20"),
    ("FIRs for IP 103.32.58.79", "en", "T20"),
    ("which UPI IDs are used in more than one district", "en", "T19"),
    ("what spikes before Deepavali, and where", "en", "T30"),
    ("conviction rate by district in 2023", "en", "T22"),
]

results: list[tuple[str, str, str]] = []
DEMO_DAY = date(2026, 10, 29)


def mark(area: str, ok: bool | None, say: str) -> None:
    results.append((area, "PASS" if ok else ("WARN" if ok is None else "FAIL"), say))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--full", action="store_true", help="also check Kannada Brain recall (loads the embedder)")
    a = ap.parse_args()
    day = date.fromisoformat(a.date)
    early = day < DEMO_DAY            # rehearsal days: demo-day items are scheduled, not missing
    os.environ["ANTAR_FORECAST_AS_OF"] = day.isoformat()     # the scan sees this day as today
    os.environ.setdefault("ANTAR_SESSIONS", "memory")

    from app.core.db_path import DB_PATH
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    # 1. the published count
    n = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    mark("data", n in (1_000_000, 2_040_002), f"{n:,} FIRs (published figure: 10,00,000 / 20,40,002 Lab)")

    # 2. no day in the week ending `day` looks like a reporting collapse
    lo = day - timedelta(days=27)
    counts = dict(con.execute("SELECT substr(date,1,10), COUNT(*) FROM FIRs WHERE date >= ? AND date <= ? GROUP BY 1",
                              (lo.isoformat(), day.isoformat() + " 23:59")).fetchall())
    med = statistics.median(counts.values()) if counts else 0
    week = [(day - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    low = [d for d in week if counts.get(d, 0) < 0.6 * med]
    mark("data", not low, f"daily FIRs, 7 days to {day}: {[counts.get(d, 0) for d in week]} (median {med:.0f})"
         + (f"; LOW on {low}" if low else ""))

    # 3. WOW-3: the planted spike is found by the scanner on this day
    from app.services import anomaly
    try:
        found = [r for r in anomaly.scan() if r.get("zone") == "Rajajinagar" and r.get("crime_type") == "chain_snatching"]
        if found:
            r = found[0]
            z = r.get("z_mad") or r.get("z_score") or 0
            mark("spike", True if z >= 2.5 else (None if early else False),
                 f"Rajajinagar chain snatching flagged: {r.get('observed')} cases, z {z:.2f}"
                 + ("" if z >= 2.5 else f" - set for {DEMO_DAY} (python scripts/replant_p2.py --anchor {day} to rehearse today)"))
        else:
            mark("spike", None if early else False, "Rajajinagar chain snatching NOT flagged - run: python scripts/replant_p2.py --anchor " + day.isoformat())
    except Exception as e:
        mark("spike", False, f"scan failed: {type(e).__name__}: {e}")

    # 4. the live story cases and the links behind them
    for label, ktype, kval, want in [("C3 UPI mule ring", "UPI_ID", "suman68@ybl", 10),
                                     ("C4 digital arrest", "IP_Address", "103.32.58.79", 8),
                                     ("C2 snatching crew", "Vehicle_Reg_No", "KA-06-AH-5331", 6)]:
        firs, last, dists = con.execute(
            "SELECT COUNT(DISTINCT f.rowid), MAX(substr(f.date,1,10)), COUNT(DISTINCT f.district_norm) "
            "FROM ext_entity_keys k JOIN FIRs f ON f.id = k.CaseMasterID WHERE k.key_type = ? AND k.key_value = ?",
            (ktype, kval)).fetchone()
        ld = date.fromisoformat(last) if last else None
        live = bool(ld) and day - timedelta(days=7) <= ld <= day
        scheduled = bool(ld) and day < ld <= DEMO_DAY
        mark("story", True if (firs >= want and live) else (None if (firs >= want and scheduled) else False),
             f"{label} ({kval}): {firs} FIRs in {dists} districts, latest {last}"
             + (" (scheduled: shows from that day)" if scheduled and not live else ""))

    # 5. the alias reveal (P1) and the five syndicates are in the world the agents read
    from app.services.zcql_local import _world
    w = _world()
    s1 = next((s for s in w["suspects"] if s["suspect_id"] == "S0001"), {})
    s2 = next((s for s in w["suspects"] if s["suspect_id"] == "S0002"), {})
    mark("story", s1.get("alias") == "Yellappa" and s1.get("phone_hash") == s2.get("phone_hash"),
         f"P1 alias link: {s1.get('full_name')} alias {s1.get('alias')} shares a phone with {s2.get('full_name')}")
    synd = [sid for sid in ("S0801", "S0803", "S0805", "S0807", "S0809") if any(s["suspect_id"] == sid for s in w["suspects"])]
    mark("story", len(synd) == 5, f"evidence syndicates present: {len(synd)}/5")

    # 6. the graph's "close to serious cases" list (Brain > Layers & Filters > Serious)
    from app.services import graph_cache
    st = graph_cache.refresh()["stats"]
    mark("graph", bool(st.get("hidden_near_serious")),
         f"near serious cases: {len(st.get('hidden_near_serious') or [])} leads, "
         f"{st.get('serious_seeds')} seeds; boss {st['top_boss']['name'] if st.get('top_boss') else '-'}")

    # 7. every run-sheet question routes to its template (offline router, no LLM)
    from app.agents.heuristics import heuristic_select
    for q, lang, want in RUN_SHEET:
        try:
            got = asyncio.run(heuristic_select(q, lang, {})).get("template_id")
        except Exception as e:
            got = f"error {type(e).__name__}"
        mark("route", got == want, f"{want} <- {q}" + ("" if got == want else f"   (got {got})"))

    # 8. tamper-evident audit chain
    try:
        from app.services.audit_store import verify_chain_report
        rep = verify_chain_report()
        ok = bool(rep.get("ok", rep.get("valid", rep.get("intact"))))
        mark("audit", ok, f"audit chain: {'intact' if ok else 'BROKEN'} - {rep.get('verified', '?'):,} of "
                          f"{rep.get('total_entries', '?'):,} entries verified")
    except Exception as e:
        mark("audit", None, f"audit check skipped: {type(e).__name__}")

    # 9. Kannada question reaches the English records (optional: loads the embedder). In its
    #    own process: ONNX Runtime loaded after the scan's numerical libraries in one process
    #    segfaults on this machine (two OpenMP runtimes).
    if a.full:
        import json, subprocess
        code = ("import json; from app.second_brain.retrieval import corpus_recall as r; "
                "e=r('chain snatching near bus stand',k=1); k=r('ಬಸ್ ನಿಲ್ದಾಣದ "
                "ಬಳಿ ಸರಗಳ್ಳತನ',k=1); "
                "print('RESULT', json.dumps([e[0]['score'] if e else 0, k[0]['score'] if k else 0]))")
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=300)
        line = next((l for l in out.stdout.splitlines() if l.startswith("RESULT ")), None)
        if line:
            se, sk = json.loads(line[7:])
            mark("kannada", sk >= 0.6 and sk >= se - 0.05, f"Brain recall EN {se:.2f} / KN {sk:.2f}")
        else:
            mark("kannada", False, f"recall check failed: {(out.stderr or '').strip().splitlines()[-1:] }")

    width = max(len(r[0]) for r in results)
    for area, state, say in results:
        print(f"{state:4s}  {area:{width}s}  {say}")
    fails = sum(1 for r in results if r[1] == "FAIL")
    print(f"\n{'NOT READY' if fails else 'READY'} for {day}: {fails} fail, {sum(1 for r in results if r[1] == 'WARN')} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
