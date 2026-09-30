"""
Antar — does the near-repeat feature actually help? (final_backend.md §6 P1-1)

Mohler et al. (JASA 2011) show a self-exciting point process beating a prospective
hotspot map by ~21% at 10% of area flagged. Antar's panel is weekly, so the part of that
effect it can carry honestly is short-horizon SPATIAL excitation — neighbours' last week
(`nbr1`) rather than their four-week mean, which smooths the spike away. That feature is
implemented behind `ANTAR_FORECAST_NEAR_REPEAT`.

This script decides whether it ships, on the rolling back-test the forecast is already
judged by — same 23 weekly origins, same refit schedule, same PAI and hit-rate
definitions. The commitment in the plan is to prove it or record the null result, so this
prints both arms and the delta either way.

    python scripts/ab_near_repeat.py                 # all-crime, both unit types
    python scripts/ab_near_repeat.py --cats ALL,PROPERTY

Each arm runs in its own process because the feature set is fixed at import time. Neither
arm calls save() or report.write(): the official docs/FORECAST_BACKTEST.md is left alone
until a winner is chosen.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MARK = "@@AB_RESULT@@"


def child(cats: list[str] | None) -> dict:
    from app.core.db_path import DB_PATH
    from app.forecast import backtest, features as F

    con = sqlite3.connect(DB_PATH, timeout=60)
    try:
        t0 = time.time()
        result = backtest.run(con, cats=cats, log=lambda *a, **k: None)
        return {"near_repeat": F.NEAR_REPEAT, "features": len(F.FEATURES),
                "seconds": round(time.time() - t0, 1), "headline": result["headline"]}
    finally:
        con.close()


def _num(h: dict, key: str):
    v = h.get(key)
    return v if isinstance(v, (int, float)) else None


def _flatten(h: dict) -> dict:
    """The back-test's headline is nested by slice — {"beat.ALL": {...}, ...}.

    A first version of this compared only top-level values, found none, and printed a
    confident verdict over an empty table. Flatten to "slice.metric" so every number is
    actually compared.
    """
    out = {}
    for key, value in h.items():
        if isinstance(value, dict):
            for k2, v2 in value.items():
                if isinstance(v2, (int, float)):
                    out[f"{key}.{k2}"] = float(v2)
        elif isinstance(value, (int, float)):
            out[key] = float(value)
    return out


# Differences below this are noise on a 23-week back-test, not evidence.
MATERIAL = {"top5_caught": 0.005, "top10_caught": 0.005, "pai5": 0.25,
            "weeks_model_beats_last4": 2.0, "deviance_gain": 0.01,
            "coverage80": 0.01, "coverage90": 0.01}


def compare(off: dict, on: dict) -> int:
    ho, hn = _flatten(off["headline"]), _flatten(on["headline"])
    keys = [k for k in sorted(set(ho) & set(hn))]
    if not keys:
        print("no comparable metrics — the back-test returned nothing to judge")
        return 2

    print()
    print(f"{'metric':<28} {'without':>12} {'with':>12} {'delta':>12}")
    print("-" * 68)
    better = worse = 0
    for k in keys:
        a, b = ho[k], hn[k]
        d = b - a
        metric = k.rsplit(".", 1)[-1]
        # "Improved" must mean MATERIALLY improved. A 0.0001 move on a 23-week back-test
        # is noise, and counting it would let any feature look like a win.
        # Unlisted metrics get a relative floor rather than zero, so a 0.0001 wobble is
        # not reported as a regression.
        threshold = MATERIAL.get(metric, max(0.005 * abs(a), 1e-3))
        lower_is_better = any(s in metric for s in ("mae", "error", "brier"))
        mark = ""
        if abs(d) > threshold:
            good = (d < 0) if lower_is_better else (d > 0)
            better += int(good)
            worse += int(not good)
            mark = "  BETTER" if good else "  WORSE"
        print(f"{k:<40} {a:>10.4f} {b:>10.4f} {d:>+10.4f}{mark}")
    print("-" * 68)
    print(f"materially improved: {better} · materially worsened: {worse} · "
          f"within noise: {len(keys) - better - worse}")
    print(f"runtime: without {off['seconds']}s · with {on['seconds']}s")
    print()
    if better > worse:
        print("VERDICT: the near-repeat term helps on this back-test. Ship it by setting")
        print("         ANTAR_FORECAST_NEAR_REPEAT=1, then regenerate the official report:")
        print("         python -m app.forecast.backtest")
        return 0
    print("VERDICT: no improvement. Leave ANTAR_FORECAST_NEAR_REPEAT off and record the")
    print("         null result — a plausible-sounding feature that does not measure is")
    print("         exactly what the back-test exists to catch.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cats", help="comma-separated categories (default: every category)")
    ap.add_argument("--child", choices=["0", "1"], help=argparse.SUPPRESS)
    ap.add_argument("--from-json", help="re-judge a saved run instead of refitting")
    args = ap.parse_args()
    cats = args.cats.split(",") if args.cats else None

    if args.from_json:
        saved = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        return compare(saved["0"], saved["1"])

    if args.child is not None:
        print(MARK + json.dumps(child(cats)), flush=True)
        os._exit(0)

    arms = {}
    for flag in ("0", "1"):
        label = "with near-repeat" if flag == "1" else "without (current)"
        print(f"== {label} ...", flush=True)
        env = dict(os.environ, ANTAR_FORECAST_NEAR_REPEAT=flag)
        cmd = [sys.executable, __file__, "--child", flag] + (["--cats", args.cats] if args.cats else [])
        p = subprocess.run(cmd, env=env, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        line = next((l for l in p.stdout.splitlines() if l.startswith(MARK)), None)
        if line is None:
            print(p.stdout[-2500:]); print(p.stderr[-2500:])
            return 2
        arms[flag] = json.loads(line[len(MARK):])
        h = arms[flag]["headline"]
        print(f"   {arms[flag]['features']} features · {arms[flag]['seconds']}s · "
              f"{ {k: round(v, 4) for k, v in h.items() if isinstance(v, (int, float))} }",
              flush=True)

    rc = compare(arms["0"], arms["1"])
    out = ROOT / "docs" / "footprint" / "near-repeat-ab.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(arms, indent=2), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
