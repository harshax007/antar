"""
Antar — Golden Query Suite (F1 acceptance referee)
=======================================================
The 40-query bilingual suite is the acceptance gate for F1 (Strategy §4.2).
M2 owns the final 40; this is a STARTER set (~22 EN+KN) covering every template +
the demo flow. Expand/correct the GOLDEN list as M2 finalizes it.

Two run modes:
  • OFFLINE (default): deterministic heuristic router — runs with no Catalyst/LLM.
    Sanity gate while building (Phase 2).
  • LLM: set QuickML creds in .env + USE_LLM=1 — measures the REAL ≥90% F1 gate (Phase 3).

Usage:
  python -m tests.golden_queries            # run + write docs/golden_report.md
  python -m pytest tests/golden_queries.py  # pytest gate (lenient offline threshold)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.query_agent import query_agent_run
from app.agents.heuristics import heuristic_select

REPORT = Path(__file__).resolve().parent.parent / "docs" / "golden_report.md"

# q, lang, expected template_id, expects ≥1 row
GOLDEN: list[tuple[str, str, str, bool]] = [
    # ── English ──
    ("show chain snatching in Rajajinagar", "en", "T1", True),
    ("list robberies in Bengaluru North", "en", "T1", True),
    ("show robbery trend in Bengaluru North last 3 months", "en", "T3", True),
    ("theft trend over time", "en", "T3", True),
    ("where are the theft hotspots", "en", "T11", True),
    # Was CLARIFY ("which crime type?"). Product requirement (owner, 2026-09-11): a
    # superlative question gets a direct answer — "most crimes?" → the district ranking
    # across ALL crime types, not a follow-up question.
    ("which zones have the most crime", "en", "T11", True),
    ("who are the repeat offenders", "en", "T5", True),
    ("find suspect Yellappa", "en", "T2", True),
    ("who is Raju", "en", "T2", True),
    ("top suspects in Rajajinagar", "en", "T4", True),
    ("victim gender breakdown", "en", "T7", True),
    ("age breakdown of suspects", "en", "T7", True),
    ("how many open cases by status", "en", "T8", True),
    ("recent crimes in Whitefield", "en", "T12", True),
    ("where should I increase patrols this weekend", "en", "CLARIFY", False),
    ("vehicle theft this month where", "en", "T11", True),
    # ── Kannada ── (script-range detected; the offline router now handles KN intent
    #    keywords + crime/zone synonyms, so these route deterministically even when the
    #    live LLM 500s and the turn falls back to the heuristic path)
    ("ರಾಜಾಜಿನಗರದಲ್ಲಿ ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು", "kn", "T1", True),      # chain snatching in Rajajinagar
    ("ದರೋಡೆ ಪ್ರವೃತ್ತಿ ತೋರಿಸಿ", "kn", "T3", True),                  # robbery trend
    ("ಅಪರಾಧ ಹಾಟ್‌ಸ್ಪಾಟ್ ಎಲ್ಲಿ", "kn", "CLARIFY", False),                # where are crime hotspots
    ("ಕಳ್ಳತನದ ಪ್ರಮುಖ ಸ್ಥಳಗಳು ಎಲ್ಲಿವೆ", "kn", "T11", True),          # theft hotspots
    ("ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಗಳು ಯಾರು", "kn", "T5", True),              # repeat offenders
    ("ಸಂತ್ರಸ್ತರ ಲಿಂಗ ವಿಭಜನೆ", "kn", "T7", True),                   # victim gender breakdown
    ("ತೆರೆದ ಪ್ರಕರಣಗಳು ಎಷ್ಟು", "kn", "T8", True),                   # how many open cases
    ("ಇತ್ತೀಚಿನ ಪ್ರಕರಣಗಳು", "kn", "T12", True),                     # recent cases
    # ── Cross-station intelligence & outcomes (T19–T23) and the T8 / T12 filters ──
    ("which UPI IDs are used in more than one district", "en", "T19", True),
    ("FIRs for UPI geetha.achar40@okicici", "en", "T20", True),
    ("cases for accused ACC-KA-500777", "en", "T21", True),
    ("conviction rate by district in 2023", "en", "T22", True),
    ("top beats for theft in Bengaluru City", "en", "T23", True),
    ("open theft cases by status in 2024", "en", "T8", True),
    ("recent burglary cases in Whitefield", "en", "T12", True),
    ("ಹಲವು ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಬಳಸಿದ UPI ಐಡಿಗಳು", "kn", "T19", True),     # UPI IDs used in many districts
    ("ACC-KA-500777 ಆರೋಪಿಯ ಪ್ರಕರಣಗಳು", "kn", "T21", True),          # cases of accused ACC-KA-500777
    ("ಜಿಲ್ಲಾವಾರು ಶಿಕ್ಷೆ ಪ್ರಮಾಣ", "kn", "T22", True),                 # conviction rate by district
    ("ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಹೆಚ್ಚು ಇರುವ ಬೀಟ್‌ಗಳು", "kn", "T23", True),  # top theft beats in Bengaluru City
]


async def run_suite(use_llm: bool = False) -> dict:
    from app.services.quickml import quickml_generate
    results = []
    for q, lang, expected, expects_rows in GOLDEN:
        try:
            if use_llm:
                out = await query_agent_run(q, lang=lang, select_llm=quickml_generate,
                                            compose_llm=quickml_generate)
            else:
                out = await query_agent_run(q, lang=lang, selector=heuristic_select,
                                            compose_llm=None)
            tmpl_ok = out["template_id"] == expected
            rows_ok = (len(out["rows"]) > 0) == expects_rows
            results.append({"q": q, "lang": lang, "expected": expected,
                            "got": out["template_id"], "tmpl_ok": tmpl_ok,
                            "rows": len(out["rows"]), "rows_ok": rows_ok,
                            "pass": tmpl_ok and rows_ok})
        except Exception as e:
            results.append({"q": q, "lang": lang, "expected": expected, "got": f"ERR:{e}",
                            "tmpl_ok": False, "rows": 0, "rows_ok": False, "pass": False})
    passed = sum(1 for r in results if r["pass"])
    return {"results": results, "passed": passed, "total": len(results),
            "accuracy": round(100 * passed / len(results), 1),
            "mode": "llm" if use_llm else "offline"}


def write_report(summary: dict) -> None:
    lines = [f"# Golden Query Report — mode: {summary['mode']}",
             f"**Accuracy: {summary['passed']}/{summary['total']} = {summary['accuracy']}%**",
             "(F1 gate = ≥90% on the LLM path. Offline = build-time sanity only.)", "",
             "| ✓ | Query | lang | expected | got | rows |", "|---|---|---|---|---|---|"]
    for r in summary["results"]:
        mark = "✅" if r["pass"] else "❌"
        lines.append(f"| {mark} | {r['q']} | {r['lang']} | {r['expected']} | {r['got']} | {r['rows']} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def test_offline_sanity_gate():
    """Build-time gate: demo-critical EN + KN queries route correctly offline — this is the
    deterministic path the live LLM degrades to on a 500, so both languages must hold."""
    summary = asyncio.run(run_suite(use_llm=False))
    write_report(summary)
    if os.getenv("ANTAR_GOLDEN_OUT"):          # scripts/release_check.py compares this to its baseline
        import json
        Path(os.environ["ANTAR_GOLDEN_OUT"]).write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    for lng, threshold in (("en", 0.9), ("kn", 0.9)):
        rows = [r for r in summary["results"] if r["lang"] == lng]
        passed = sum(1 for r in rows if r["pass"])
        assert passed / len(rows) >= threshold, \
            f"offline {lng.upper()} accuracy {passed}/{len(rows)} < {int(threshold * 100)}%"


if __name__ == "__main__":
    s = asyncio.run(run_suite(use_llm=os.getenv("USE_LLM") == "1"))
    write_report(s)
    print(f"Golden suite ({s['mode']}): {s['passed']}/{s['total']} = {s['accuracy']}%")
    print(f"Report → {REPORT}")
    for r in s["results"]:
        if not r["pass"]:
            print(f"  ❌ [{r['lang']}] {r['q']!r} expected {r['expected']} got {r['got']} rows={r['rows']}")
