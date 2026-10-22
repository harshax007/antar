"""
Is this build ready to demo or deploy?
=====================================
One command that answers it, before a demo day or a Catalyst deploy:

    python scripts/release_check.py            # everything below
    python scripts/release_check.py --quick    # skip the test suite and the eval
    python scripts/release_check.py --save-baseline   # record today's eval scores

Checks, each PASS / WARN / FAIL:
  data        the FIR register is there and sane: row count, real vs demonstration rows,
              usable coordinates, the coordinate clean-up recorded
  agents      AGENTS.md and the compiled graph agree; the agent lock is in step
  tests       the core suites pass (on a copy of main.db: tests/conftest.py)
  eval        the golden question set (tests/golden_queries.py, EN + KN) answers at least as
              well as the saved baseline (scripts/eval_baseline.json); --save-baseline
              records the current scores after a deliberate change
  config      the language model is configured; open-web search has a reliable key; the
              outbound-call mode; demo mode
  claims      no unprovable claim ("0% hallucination", "0 external dependencies") on screen

Exit code 1 if anything FAILs, so it can gate a deploy script.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PY = sys.executable

CORE_TESTS = [
    "tests/test_agents_manifest.py", "tests/test_answer_guardrails.py", "tests/test_egress.py",
    "tests/test_llm_security.py", "tests/test_hitl.py", "tests/test_policy_context.py",
    "tests/test_query_agent.py", "tests/test_heuristics_kannada.py", "tests/test_forecast_model.py",
    "tests/test_osint.py", "tests/test_osint_checks.py", "tests/test_kannada_names_and_recall.py", "tests/test_repeat_locations.py",
    "tests/test_sessions_durable.py", "tests/test_alerts_durable.py", "tests/test_zz_uses_db_copy.py",
]
BASELINE = ROOT / "scripts" / "eval_baseline.json"
CLAIMS = [r"0%\s*hallucination", r"zero[- ]hallucination", r"0\s+external\s+dependenc", r"HALLUCINATION RATE"]

results: list[tuple[str, str, str]] = []


def mark(area: str, state: str, say: str) -> None:
    results.append((area, state, say))


def check_data() -> None:
    from app.core.db_path import DB_PATH
    if not Path(DB_PATH).exists():
        mark("data", "FAIL", f"database not found: {DB_PATH}")
        return
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    total = con.execute("SELECT COUNT(*) FROM FIRs").fetchone()[0]
    demo = con.execute("SELECT COALESCE(SUM(is_synthetic_row), 0) FROM FIRs").fetchone()[0]
    geo = con.execute("SELECT COUNT(*) FROM FIRs WHERE geo_ok").fetchone()[0]
    span = con.execute("SELECT MIN(SUBSTR(date,1,10)), MAX(SUBSTR(date,1,10)) FROM FIRs").fetchone()
    mark("data", "PASS" if total >= 900_000 else "WARN", f"{total:,} FIRs, {span[0]} to {span[1]}; {demo:,} demonstration rows")
    cleaned = con.execute("SELECT name FROM sqlite_master WHERE name='fir_geo_original'").fetchone()
    n_clean = con.execute("SELECT COUNT(*) FROM fir_geo_original").fetchone()[0] if cleaned else 0
    mark("data", "PASS" if n_clean else "WARN",
         f"{geo:,} FIRs with a usable point; " + (f"{n_clean:,} bad points cleared (scripts/clean_fir_coordinates.py)"
                                                  if n_clean else "coordinates not cleaned yet: run scripts/clean_fir_coordinates.py"))


def check_agents() -> None:
    from app.agents import manifest
    m = manifest.load()
    errors = list(getattr(m, "errors", []) or [])
    mark("agents", "FAIL" if errors else "PASS",
         f"{len(m.agents)} agents in AGENTS.md" + (f"; problems: {errors[:3]}" if errors else ", manifest consistent"))
    r = subprocess.run([PY, "scripts/lock_agents.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip().splitlines()
    ok = r.returncode == 0 and any("in step" in line for line in out)
    mark("agents", "PASS" if ok else "FAIL", out[-1] if out else "lock check gave no output")


def check_tests() -> None:
    files = [f for f in CORE_TESTS if (ROOT / f).exists()]
    env = {**os.environ, "OBS_ENABLED": "0"}
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files], cwd=ROOT,
                       capture_output=True, text=True, env=env)
    tail = [line for line in (r.stdout + r.stderr).splitlines() if re.search(r"passed|failed|error", line)]
    mark("tests", "PASS" if r.returncode == 0 else "FAIL", (tail[-1] if tail else "no result") + f" ({len(files)} core files)")


def check_eval(save: bool = False) -> None:
    """Deterministic (offline router), so a lower score is a real regression, not noise."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "golden.json"
        env = {**os.environ, "OBS_ENABLED": "0", "ANTAR_GOLDEN_OUT": str(out)}
        subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/golden_queries.py"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
        if not out.exists():
            mark("eval", "FAIL", "golden question set did not run")
            return
        summary = json.loads(out.read_text(encoding="utf-8"))
    now = {}
    for lng in ("en", "kn"):
        rows = [r for r in summary["results"] if r["lang"] == lng]
        now[lng] = {"passed": sum(1 for r in rows if r["pass"]), "total": len(rows)}
    if save:
        BASELINE.write_text(json.dumps(now, indent=2) + "\n", encoding="utf-8")
    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    for lng, v in now.items():
        say = f"{lng.upper()} golden questions: {v['passed']}/{v['total']} answered by the right template"
        if not base or lng not in base:
            mark("eval", "WARN", say + "; no baseline yet (run with --save-baseline)")
        elif v["passed"] < base[lng]["passed"]:
            failing = [r["q"] for r in summary["results"] if r["lang"] == lng and not r["pass"]][:3]
            mark("eval", "FAIL", say + f", baseline {base[lng]['passed']}; now failing: {failing}")
        else:
            mark("eval", "PASS", say + f" (baseline {base[lng]['passed']})")


def check_config() -> None:
    from app.core.settings import settings
    from app.core import egress
    provider = (getattr(settings, "ANTAR_LLM_PROVIDER", "") or "quickml").lower()
    llm_ok = bool(settings.QUICKML_CLIENT_ID and settings.QUICKML_CLIENT_SECRET) if provider == "quickml" \
        else bool(getattr(settings, "ANTAR_LLM_BASE_URL", ""))
    mark("config", "PASS" if llm_ok else "WARN",
         f"language model ({provider}) " + ("configured" if llm_ok else "not configured: answers fall back to the record-based writer"))
    mark("config", "PASS" if settings.BRAVE_SEARCH_API_KEY else "WARN",
         "open-web search: Brave key set" if settings.BRAVE_SEARCH_API_KEY
         else "open-web search has no Brave key: DuckDuckGo / Bing throttle bursts (set BRAVE_SEARCH_API_KEY)")
    mark("config", "PASS", f"outbound calls: {egress.mode()} mode")
    demo = str(getattr(settings, "DEMO_MODE", "")).lower() in ("1", "true", "yes")
    mark("config", "PASS", f"demo mode {'on' if demo else 'off'}")


def check_claims() -> None:
    hits = []
    for base in ("antar-frontend/app", "antar-frontend/components"):
        for path in (ROOT / base).rglob("*.jsx"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pat in CLAIMS:
                if re.search(pat, text, re.I):
                    hits.append(f"{path.relative_to(ROOT)}: {pat}")
    mark("claims", "FAIL" if hits else "PASS", "; ".join(hits[:4]) if hits else "no unprovable claims on screen")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the test suite and the eval")
    ap.add_argument("--save-baseline", action="store_true", help="record the current eval scores as the baseline")
    a = ap.parse_args()
    run_eval = None if a.quick and not a.save_baseline else (lambda: check_eval(a.save_baseline))
    if run_eval:
        run_eval.__name__ = "check_eval"
    for fn in (check_data, check_agents, None if a.quick else check_tests, run_eval, check_config, check_claims):
        if fn is None:
            continue
        try:
            fn()
        except Exception as e:          # a check that cannot run is itself a finding
            mark(fn.__name__.replace("check_", ""), "FAIL", f"could not run: {type(e).__name__}: {e}")
    width = max(len(r[0]) for r in results)
    for area, state, say in results:
        print(f"{state:4s}  {area:{width}s}  {say}")
    fails = sum(1 for r in results if r[1] == "FAIL")
    warns = sum(1 for r in results if r[1] == "WARN")
    print(f"\n{'NOT READY' if fails else 'READY'}: {fails} fail, {warns} warn")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
