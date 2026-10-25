"""Forecast queries — what /api/forecast/* returns (Phase 4 of docs/MAP_FORECASTING_PLAN.md).

Pure functions over the database, all served from forecast_output / geo_units /
forecast_cube, so every request is a handful of primary-key reads.

The contract every forecast honours (the constitution, docs/ANTAR_CONSTITUTION.md):
  * evidence class **I** (Inferred) on every forecast number, with its basis stated;
  * a range, never a bare number — ICD 203 words: the 80% range is "likely", the 90%
    range "very likely" (both measured in the back-test, not assumed);
  * the as-of date and how much of the history behind it is real record;
  * places and times, never people;
  * resolve or refuse: an unknown category, district, station or unit is refused with
    the nearest valid names — never silently widened to "everywhere".
"""
from __future__ import annotations

import difflib
import json
import re
import math
import sqlite3
import threading
import time
from datetime import date, timedelta

from app.forecast import asof as asof_mod
from app.forecast import backtest as BT
from app.forecast import run as R
from app.forecast.categories import CATEGORIES, categorize
from app.forecast.features import ALL

LABELS = {ALL: "All crime", **CATEGORIES}
HORIZONS = (7, 28)
THIN_N52 = 4                      # fewer FIRs than this in a year → "thin history"
DRIVER_MIN = 0.10                 # a reason is shown when it moves the forecast ≥ 10%


class Refusal(Exception):
    """A filter that cannot be resolved. Answering without it would answer a different
    question, so the API refuses (422) and offers the nearest valid values."""

    def __init__(self, message: str, options: list[str] | None = None, field: str = ""):
        super().__init__(message)
        self.message, self.options, self.field = message, options or [], field

    def to_dict(self) -> dict:
        return {"refused": True, "field": self.field, "message": self.message,
                "options": self.options}


class NotReady(Exception):
    """No forecast has been computed for this as-of yet (it is being prepared)."""


# ── resolving what was asked ─────────────────────────────────────────────────

_CATEGORY_WORDS = {
    "all": ALL, "all crime": ALL, "any": ALL, "total": ALL, "crime": ALL,
    "theft": "PROPERTY", "thefts": "PROPERTY", "burglary": "PROPERTY", "robbery": "PROPERTY",
    "property": "PROPERTY", "chain snatching": "PROPERTY", "vehicle theft": "PROPERTY",
    "violence": "VIOLENT", "violent": "VIOLENT", "assault": "VIOLENT", "hurt": "VIOLENT",
    "murder": "MURDER", "kidnapping": "KIDNAP", "abduction": "KIDNAP",
    "women": "WOMEN", "crimes against women": "WOMEN", "children": "CHILDREN",
    "cyber": "CYBER", "cybercrime": "CYBER", "fraud": "ECONOMIC", "cheating": "ECONOMIC",
    "economic": "ECONOMIC", "drugs": "NARCOTICS", "narcotics": "NARCOTICS",
    "missing": "MISSING", "missing persons": "MISSING", "accidents": "ROAD",
    "road accidents": "ROAD", "traffic": "ROAD", "sc/st": "SCST",
}


def resolve_category(text: str | None) -> str:
    if not text:
        return ALL
    t = text.strip()
    up = t.upper()
    if up in LABELS:
        return up
    for key, label in LABELS.items():
        if label.lower() == t.lower():
            return key
    low = t.lower()
    if low in _CATEGORY_WORDS:
        return _CATEGORY_WORDS[low]
    # an official crime group name ("THEFT", "BURGLARY - NIGHT") maps through the taxonomy
    cat = categorize(t)
    if cat != "OTHER":
        return cat
    near = difflib.get_close_matches(low, list(_CATEGORY_WORDS) + [v.lower() for v in LABELS.values()],
                                     n=4, cutoff=0.6)
    raise Refusal(f"'{t}' is not a crime category the forecast covers.",
                  sorted({LABELS.get(_CATEGORY_WORDS.get(n, ""), n) for n in near}) or
                  sorted(LABELS.values()), "category")


def _names(conn, sql: str, params=()) -> list[str]:
    return [r[0] for r in conn.execute(sql, params) if r[0]]


# Names officers still use for places renamed in 2006–2014.
_OLD_NAMES = {"bangalore": "bengaluru", "mysore": "mysuru", "belgaum": "belagavi",
              "mangalore": "mangaluru", "gulbarga": "kalaburagi", "bellary": "ballari",
              "hubli": "hubballi", "shimoga": "shivamogga", "tumkur": "tumakuru",
              "bijapur": "vijayapura", "chikmagalur": "chikkamagaluru", "hospet": "hosapete"}


def resolve_district(conn: sqlite3.Connection, text: str | None) -> str | None:
    if not text:
        return None
    names = _names(conn, "SELECT DISTINCT district FROM geo_units")
    by_low = {n.lower(): n for n in names}
    t = text.strip().lower()
    for old, new in _OLD_NAMES.items():
        t = t.replace(old, new)
    for cand in (t, t.replace(" district", " dist")):
        if cand in by_low:
            return by_low[cand]
    # a bare city name ("Mysuru") resolves only when it names ONE police district;
    # City + Dist both existing is ambiguous and is refused below, never guessed
    both = [by_low[c] for c in (t + " city", t + " dist") if c in by_low]
    if len(both) == 1:
        return both[0]
    # "Mysuru" is two police districts (City and Dist): offer both, never pick one
    starts = [by_low[n] for n in by_low if n.split()[0] == t.split()[0]] if t else []
    near = starts or [by_low[n] for n in difflib.get_close_matches(t, list(by_low), n=4, cutoff=0.6)]
    raise Refusal(f"'{text}' is not a police district in the registry"
                  + (" — it matches more than one." if len(starts) > 1 else "."),
                  near, "district")


def resolve_districts(conn: sqlite3.Connection, text: str | None) -> list[str]:
    """One district, or several separated by "|" (a map district such as GADM "Mysuru" is
    two police districts: Mysuru City and Mysuru Dist). Every one must resolve."""
    if not text:
        return []
    return [resolve_district(conn, t) for t in text.split("|") if t.strip()]


def resolve_unit(conn: sqlite3.Connection, name: str, unit_type: str | None = None) -> tuple[str, str]:
    """(unit_type, unit) for a station or beat name, exact first, then case-insensitive."""
    types = [unit_type] if unit_type else (["beat", "station"] if " | " in name else ["station", "beat"])
    for ut in types:
        row = conn.execute("SELECT unit FROM geo_units WHERE unit_type = ? AND unit = ?",
                           (ut, name)).fetchone() or conn.execute(
            "SELECT unit FROM geo_units WHERE unit_type = ? AND UPPER(unit) = UPPER(TRIM(?))",
            (ut, name)).fetchone()
        if row:
            return ut, row[0]
    pool = _names(conn, "SELECT unit FROM geo_units WHERE unit_type = ?", (types[0],))
    near = difflib.get_close_matches(name, pool, n=5, cutoff=0.6)
    raise Refusal(f"'{name}' is not a police station or beat in the registry.", near, "unit")


def _as_of(conn: sqlite3.Connection, override: str | None) -> tuple[asof_mod.AsOf, dict]:
    a = asof_mod.resolve(conn, override)
    info = R.run_info(conn, a.history_end.isoformat())
    if not info:
        _prepare_async(override)
        raise NotReady(f"Forecasts as of {a.as_of} are being prepared (about a minute).")
    return a, info


_preparing: set = set()


def _prepare_async(override: str | None) -> None:
    key = override or "configured"
    if key in _preparing:
        return
    _preparing.add(key)

    def work():
        try:
            R.ensure_isolated(override=override)     # a refit runs in a child process
        finally:
            _preparing.discard(key)
    threading.Thread(target=work, daemon=True).start()


# ── words ─────────────────────────────────────────────────────────────────────

def _noun(cat: str, n: float) -> str:
    base = "FIR" if cat == ALL else f"{LABELS[cat].lower()} FIR"
    return base if round(n) == 1 else base + "s"


def _int(x: float) -> int:
    return int(round(x))


def _calibrated_chance(p: float) -> str:
    """ICD 203 words for a probability."""
    for lo, word in ((0.95, "almost certain"), (0.80, "very likely"), (0.55, "likely"),
                     (0.45, "roughly even chance"), (0.20, "unlikely"), (0.05, "very unlikely")):
        if p >= lo:
            return word
    return "almost no chance"


def _pct(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{abs(100 * x):.0f}%"


def drivers(row: dict, unit_type: str, horizon: int) -> list[dict]:
    """The reasons, in words, largest first — each a multiplier on "a usual week here"."""
    parent = "station" if unit_type == "beat" else "district"
    peers = "beats" if unit_type == "beat" else "stations"
    usual4 = row["usual_level"] / horizon * 28 if horizon else 0
    texts = {
        "recent": lambda x: (f"Recent weeks running {'above' if x > 1 else 'below'} usual — "
                             f"{_int(row['recent4'])} FIRs in the last 4 weeks against a usual "
                             f"{usual4:.1f}" if usual4 < 10 else
                             f"Recent weeks running {'above' if x > 1 else 'below'} usual — "
                             f"{_int(row['recent4'])} FIRs in the last 4 weeks against a usual "
                             f"{usual4:.0f}"),
        "last_year": lambda x: (f"The same weeks last year were {'busier' if x > 1 else 'quieter'} "
                                f"than usual ({row['last_year_h']:.0f})"),
        "neighbours": lambda x: f"Neighbouring {peers} are {'busier' if x > 1 else 'quieter'} than usual",
        "area": lambda x: f"The {parent} as a whole is forecast {'up' if x > 1 else 'down'}",
        "season": lambda x: f"This time of year runs {'above' if x > 1 else 'below'} average",
        "level": lambda x: (f"Pulled toward the {parent}'s level — a short or unusual record "
                            f"here is not taken at face value"),
    }
    out = []
    for key in ("recent", "last_year", "neighbours", "area", "season", "level"):
        x = row.get(f"x_{key}") or 1.0
        if x > 0 and abs(math.log(x)) >= math.log(1 + DRIVER_MIN):
            out.append({"key": key, "factor": round(x, 3), "effect": _pct(x - 1), "text": texts[key](x)})
    # "level" (shrinkage toward the parent) is true of most small units, so it is listed
    # after the reasons that distinguish this one
    out.sort(key=lambda d: (d["key"] == "level", -abs(math.log(d["factor"]))))
    return out


_WHY_KEYS = ("recent", "last_year", "neighbours", "area", "season", "level")


def why(row: dict, unit_type: str, horizon: int) -> dict | None:
    """The forecast taken apart, exactly: a usual period here, times each reason.

    `drivers()` lists the reasons worth a sentence (10% or more). This lists all six, so
    the arithmetic can be shown and checked: usual x every factor = the forecast. For each
    reason it also gives the forecast WITHOUT it (the forecast divided by that factor) -
    "had the last four weeks been usual, this would be 5, not 7". That is the model's own
    counterfactual, not an approximation of one: the model is multiplicative.
    """
    usual, expected = row.get("usual_level") or 0, row.get("expected") or 0
    if usual <= 0 or expected <= 0:
        return None
    parent = "station" if unit_type == "beat" else "district"
    peers = "beats" if unit_type == "beat" else "stations"
    label = {"recent": "The last 4 weeks", "last_year": "The same weeks last year",
             "neighbours": f"Neighbouring {peers}", "area": f"The {parent} as a whole",
             "season": "The time of year", "level": f"Pull toward the {parent}'s level"}
    said = {d["key"]: d["text"] for d in drivers(row, unit_type, horizon)}
    steps, product = [], 1.0
    for key in _WHY_KEYS:
        x = row.get(f"x_{key}") or 1.0
        if x <= 0:
            x = 1.0
        product *= x
        steps.append({"key": key, "label": label[key], "factor": round(x, 3), "effect": _pct(x - 1),
                      "notable": key in said, "text": said.get(key),
                      "without": round(expected / x, 2)})
    steps.sort(key=lambda d: -abs(math.log(d["factor"])))
    return {
        "usual": round(usual, 2), "expected": round(expected, 2), "horizon_days": horizon,
        "steps": steps, "product": round(product, 4),
        # the identity the page relies on; a model change that breaks it should be seen
        "reconciles": abs(usual * product / expected - 1) < 0.01,
        "plain": ("Close to a usual period here: no single reason moves it by 10% or more."
                  if not said else None),
    }


NOT_USED = (
    "Anything about a person: no name, accused id, age, gender, caste, religion or income.",
    "The time of day. The register holds the date of an FIR, not the hour.",
    "Anything outside the FIR register: weather, CCTV, calls for service, social media.",
    "The language model. It words a forecast; it never produces one.",
)


def _fairness(conn: sqlite3.Connection, unit_type: str) -> dict | None:
    try:
        from app.forecast import fairness
        return fairness.measure(conn, unit_type)
    except Exception:
        return None


def global_explanation(conn: sqlite3.Connection, *, unit_type: str = "station", horizon: int = 7,
                       as_of: str | None = None) -> dict:
    """How the engine behaves across the state, as opposed to why one forecast is what it is.

    For every crime category: how much each of the six reasons typically moves a forecast
    (the typical multiplier, and the share of units where it moves the forecast by 10% or
    more), and how the category did in the back-test. Then where the engine is weakest,
    by the back-test's own figures. Everything is read from the stored forecasts and the
    stored back-test; nothing is typed in.

    "Typical" is the geometric mean of each factor's size: exp(mean |ln x|) - 1, so a
    reason that halves some forecasts and doubles others reads as large, not as zero.
    """
    horizon, unit_type = _check_horizon(horizon), _check_unit_type(unit_type)
    a, info = _as_of(conn, as_of)
    wk = a.history_end.isoformat()
    cols = ", ".join(f"x_{k}" for k in _WHY_KEYS)
    cats = []
    for cat in (ALL, *CATEGORIES):
        rows = conn.execute(f"SELECT {cols} FROM forecast_output WHERE as_of_week = ? AND unit_type = ? "
                            f"AND category = ? AND horizon = ? AND usual_level > 0 AND n52 >= ?",
                            (wk, unit_type, cat, horizon, THIN_N52)).fetchall()
        if not rows:
            continue
        reasons = []
        for i, key in enumerate(_WHY_KEYS):
            logs = [abs(math.log(r[i])) for r in rows if r[i] and r[i] > 0]
            if not logs:
                continue
            reasons.append({"key": key, "typical_move": round(math.exp(sum(logs) / len(logs)) - 1, 3),
                            "share_notable": round(sum(1 for v in logs if v >= math.log(1 + DRIVER_MIN)) / len(logs), 3)})
        reasons.sort(key=lambda d: -d["typical_move"])
        acc = accuracy(conn, unit_type, cat, horizon)
        cats.append({
            "category": cat, "label": LABELS[cat], "units": len(rows), "reasons": reasons,
            "main_reason": reasons[0]["key"] if reasons else None,
            "backtest": ({k: acc[k] for k in ("weeks", "top5_share_caught", "top5_share_caught_last4",
                                              "weeks_better_than_last4", "coverage80", "calibration") if k in acc}
                         if acc else None),
        })

    weakest = []
    for c in cats:
        b = c["backtest"]
        if not b:
            continue
        why = []
        if b.get("calibration") is not None and abs(b["calibration"] - 1) >= 0.10:
            why.append(f"forecasts ran {'high' if b['calibration'] > 1 else 'low'}: {b['calibration']:.2f} forecast for every 1 recorded")
        if b.get("weeks") and b.get("weeks_better_than_last4") is not None and b["weeks_better_than_last4"] <= 0.65 * b["weeks"]:
            why.append(f"beat last-4-weeks ranking in only {b['weeks_better_than_last4']} of {b['weeks']} weeks")
        if b.get("coverage80") is not None and not (0.70 <= b["coverage80"] <= 0.995):
            why.append(f"the likely range held {100 * b['coverage80']:.0f}% of the time (it should be near 80%)")
        if why:
            weakest.append({"category": c["category"], "label": c["label"], "why": why})

    labels = {"recent": "The last 4 weeks", "last_year": "The same weeks last year",
              "neighbours": f"Neighbouring {'beats' if unit_type == 'beat' else 'stations'}",
              "area": f"The {'station' if unit_type == 'beat' else 'district'} as a whole",
              "season": "The time of year", "level": f"Pull toward the {'station' if unit_type == 'beat' else 'district'}'s level"}
    return {
        "as_of": _basis(a, info), "unit_type": unit_type, "horizon_days": horizon,
        "reason_labels": labels, "categories": cats, "weakest": weakest, "not_used": list(NOT_USED),
        "fairness": _fairness(conn, unit_type),
        "method": ("Poisson regression on top of a seasonal and recent-weeks baseline; a forecast is a usual "
                   "period times these six reasons. Ranges are split-conformal, calibrated on weeks the model did not see."),
        "evidence_class": "D",
    }


def summary_sentence(row: dict, cat: str, horizon: int) -> str:
    lo8, hi8, lo9, hi9 = (_int(row[k]) for k in ("lo80", "hi80", "lo90", "hi90"))
    rng = (lambda a, b: f"{a}" if a == b else f"{a}–{b}")
    s = (f"Likely {rng(lo8, hi8)} {_noun(cat, hi8)} in the next {horizon} days "
         f"(very likely {rng(lo9, hi9)})")
    if row["usual_level"] > 0:
        s += f"; usually {row['usual_level']:.1f}"
    return s + "."


# ── accuracy ──────────────────────────────────────────────────────────────────

_bt_cache: dict = {"at": 0.0, "value": None}


def backtest(conn: sqlite3.Connection) -> dict | None:
    if _bt_cache["value"] is None or time.monotonic() - _bt_cache["at"] > 300:
        _bt_cache["value"] = BT.load(conn)
        _bt_cache["at"] = time.monotonic()
    return _bt_cache["value"]


def accuracy(conn, unit_type: str, cat: str, horizon: int) -> dict | None:
    bt = backtest(conn)
    m = (bt or {}).get("results", {}).get(unit_type, {}).get(cat, {}).get(str(horizon))
    if not m or "capture" not in m:
        return None
    c5 = m["capture"]["top_5pct"]
    out = {
        "window": f"{bt['window']['first_target_week']} – {bt['window']['last_target_week']}",
        "weeks": c5["weeks"], "top5_share_caught": c5["model"],
        "top5_share_caught_last4": c5["last4"], "weeks_better_than_last4": c5["model_beats_last4_weeks"],
        "coverage80": m["coverage"]["80"]["coverage"], "coverage90": m["coverage"]["90"]["coverage"],
        "calibration": m["calibration"], "measured_at": bt["built_at"],
    }
    if "pai" in m:
        out["pai5"] = m["pai"]["top_5pct"]["model"]["pai"]
    out["text"] = (f"Back-tested on {out['window']} (real record): the top 5% of {unit_type}s "
                   f"caught {100 * c5['model']:.0f}% of the next {horizon} days' "
                   f"{'FIRs' if cat == ALL else LABELS[cat].lower() + ' FIRs'} "
                   f"(last-4-weeks hotspots: {100 * c5['last4']:.0f}%).")
    return out


def track_record(conn, unit_type: str, cat: str, unit: str) -> dict | None:
    bt = backtest(conn)
    m = (bt or {}).get("results", {}).get(unit_type, {}).get(cat, {}).get("7")
    if not m or "units" not in m:
        return None
    weeks = m["capture"]["top_5pct"]["weeks"]
    rec = m["units"].get(unit)
    if rec is None:
        return {"weeks": weeks, "weeks_flagged": 0,
                "text": f"Not in the top 5% in any of the {weeks} back-test weeks."}
    flagged, hit, fc, ac = rec
    return {"weeks": weeks, "weeks_flagged": flagged, "weeks_flagged_with_crime": hit,
            "forecast_total": fc, "actual_total": ac,
            "text": (f"In back-testing it was in the top 5% in {flagged} of {weeks} weeks and "
                     f"recorded at least one FIR in {hit} of those; forecast {fc:.0f} over the "
                     f"window, actual {ac}.")}


def scorecard(conn: sqlite3.Connection, *, unit_type: str = "beat",
              category: str | None = None) -> dict:
    """The forecast graded against what was then recorded, one week at a time.

    Read from the back-test, so it is the real record only and each week was forecast from
    data strictly before it. It is a replay, not a live feed: the real record ends in
    2024-03, and grading a forecast against seeded weeks would measure the seeding.
    Evidence class D - every figure is a count or a ratio of counts.
    """
    ut = _check_unit_type(unit_type)
    cat = resolve_category(category)
    bt = backtest(conn)
    m = (bt or {}).get("results", {}).get(ut, {}).get(cat, {}).get("7")
    if not m or not m.get("weekly"):
        raise NotReady("The forecast has not been graded yet — python -m app.forecast.backtest.")
    rows = []
    for w in m["weekly"]:
        r = {**w, "error": round(w["forecast"] - w["actual"], 1)}
        if "caught" in w:
            r["beat_last4"] = w["caught"] > w["caught_last4"]
        rows.append(r)
    ranked = [r for r in rows if "beat_last4" in r]
    wins = sum(r["beat_last4"] for r in ranked)
    fc, ac = sum(r["forecast"] for r in rows), sum(r["actual"] for r in rows)
    cov80, cov90 = m["coverage"]["80"]["coverage"], m["coverage"]["90"]["coverage"]
    what = "FIRs" if cat == ALL else f"{LABELS[cat].lower()} FIRs"
    # The ranges are a claim about frequency, so the wording follows the measurement:
    # a range that held less often than its label is said to be too narrow, not defended.
    if cov80 >= 0.80:
        ranges = (f"The 80% ranges held {100 * cov80:.1f}% of the time - at least as often "
                  f"as stated.")
    else:
        ranges = (f"The 80% ranges held {100 * cov80:.1f}% of the time. I'd read them as "
                  f"narrower than they should be.")
    w = bt["window"]
    return {
        "unit_type": ut, "category": cat, "category_label": LABELS[cat], "horizon_days": 7,
        "evidence_class": "D",
        "window": {"from": rows[0]["week"], "to": rows[-1]["week"], "weeks": len(rows)},
        "weeks": rows,
        "summary": {"weeks_ranked": len(ranked), "weeks_better_than_last4": wins,
                    "forecast_total": round(fc, 1), "actual_total": ac,
                    "calibration": m["calibration"], "coverage80": cov80, "coverage90": cov90},
        "text": (f"Graded on {len(rows)} weeks of the real record ({rows[0]['week']} to "
                 f"{rows[-1]['week']}): {fc:,.0f} {what} forecast against {ac:,} recorded. "
                 f"The top 5% of {ut}s outranked last-4-weeks hotspots in {wins} of "
                 f"{len(ranked)} weeks."),
        "ranges": ranges,
        "method": (f"Each week is forecast from data strictly before it; the model is "
                   f"refitted every {w['refit_every_weeks']} weeks."),
        "measured_at": bt["built_at"], "model_version": bt.get("model_version"),
    }


# ── Gi* (confirmed clusters), cached per as-of ────────────────────────────────

_gi_cache: dict = {}
_gi_lock = threading.Lock()


def gi_star(as_of: date, days: int = 28) -> dict[str, bool] | None:
    """{district: is_confirmed_hotspot} for all crime over the 4 weeks to the as-of date.
    None while it is being computed (2 s) — the request never waits for it."""
    key = (as_of, days)
    if key in _gi_cache:
        return _gi_cache[key]

    def work():
        from app.services.anomaly import gi_star_surface
        try:
            zones = gi_star_surface(crime_type=None, days=days, end_date=as_of)
            _gi_cache[key] = {z["zone"]: bool(z["is_hotspot"]) for z in zones}
        except Exception:
            _gi_cache[key] = {}
    if _gi_lock.acquire(blocking=False):
        def run():
            try:
                work()
            finally:
                _gi_lock.release()
        threading.Thread(target=run, daemon=True).start()
    return None


def warm(as_of: date) -> None:
    from app.services.anomaly import gi_star_surface
    zones = gi_star_surface(crime_type=None, days=28, end_date=as_of)
    _gi_cache[(as_of, 28)] = {z["zone"]: bool(z["is_hotspot"]) for z in zones}


# ── responses ─────────────────────────────────────────────────────────────────

def _basis(a: asof_mod.AsOf, info: dict) -> dict:
    share = info.get("real_share")
    if share is None:
        text = "No FIRs in the last 13 weeks of history."
    elif share >= 0.99:
        text = "Built on the real record."
    else:
        text = (f"{100 * share:.0f}% of the last 13 weeks of history is real record; the rest "
                f"is seeded demonstration data.")
    return {**a.to_dict(), "real_share": share, "basis": text,
            "computed_at": info.get("built_at"), "model_version": info.get("model_version")}


_COLS = ("unit", "expected", "lo80", "hi80", "lo90", "hi90", "p_any", "baseline", "usual_level",
         "x_level", "x_recent", "x_last_year", "x_neighbours", "x_area", "x_season",
         "recent4", "last_year_h", "n52")


def _item(row: dict, g: dict | None, unit_type: str, cat: str, horizon: int, rank: int | None,
          gi: dict | None) -> dict:
    thin = (row["n52"] or 0) < THIN_N52
    name = display_name(row["unit"], unit_type)
    district = (g or {}).get("district")
    return {
        "rank": rank, "unit": row["unit"], "unit_type": unit_type, "name": name,
        "station": (g or {}).get("station"), "district": district,
        "lat": (g or {}).get("lat"), "lon": (g or {}).get("lon"),
        "area_km2": (g or {}).get("area_km2"),
        "expected": round(row["expected"], 2),
        "band80": {"lo": _int(row["lo80"]), "hi": _int(row["hi80"]), "words": "likely"},
        "band90": {"lo": _int(row["lo90"]), "hi": _int(row["hi90"]), "words": "very likely"},
        "p_any": round(row["p_any"], 3),
        "p_any_words": _calibrated_chance(row["p_any"]),
        "usual": round(row["usual_level"], 2),
        "vs_usual": (round(row["expected"] / row["usual_level"] - 1, 3)
                     if row["usual_level"] > 0 else None),
        "baseline": round(row["baseline"], 2),
        "summary": ("Insufficient history for a reliable forecast — fewer than "
                    f"{THIN_N52} FIRs of this kind here in the last year." if thin
                    else summary_sentence(row, cat, horizon)),
        "history": "thin" if thin else "ok", "fir_last_52w": int(row["n52"] or 0),
        "drivers": drivers(row, unit_type, horizon)[:3],
        "why": why(row, unit_type, horizon),
        "district_cluster": (gi or {}).get(district) if gi is not None else None,
        "evidence_class": "I",
    }


def display_name(unit: str, unit_type: str) -> str:
    """A beat as an officer would say it: "Beat 5", not "5"."""
    if unit_type != "beat":
        return unit
    name = unit.split(" | ", 1)[1] if " | " in unit else unit
    return f"Beat {name}" if re.fullmatch(r"\d+\w?", name.strip()) else name


def _geo(conn, unit_type: str, units: list[str]) -> dict[str, dict]:
    if not units:
        return {}
    out = {}
    for i in range(0, len(units), 500):
        chunk = units[i: i + 500]
        q = ("SELECT unit, station, district, lat, lon, area_km2 FROM geo_units "
             f"WHERE unit_type = ? AND unit IN ({','.join('?' * len(chunk))})")
        for u, st, d, la, lo, ar in conn.execute(q, (unit_type, *chunk)):
            out[u] = {"station": st, "district": d, "lat": la, "lon": lo, "area_km2": ar}
    return out


def _check_horizon(horizon: int) -> int:
    if horizon not in HORIZONS:
        raise Refusal(f"Forecasts are made for the next 7 or 28 days, not {horizon}.",
                      ["7", "28"], "horizon")
    return horizon


def _check_unit_type(unit_type: str) -> str:
    if unit_type not in ("station", "beat"):
        raise Refusal(f"'{unit_type}' is not a forecast unit.", ["station", "beat"], "unit")
    return unit_type


def hotspots(conn: sqlite3.Connection, *, horizon: int = 7, category: str | None = None,
             district: str | None = None, station: str | None = None, unit_type: str = "beat",
             limit: int = 25, as_of: str | None = None) -> dict:
    horizon, unit_type = _check_horizon(horizon), _check_unit_type(unit_type)
    cat = resolve_category(category)
    dists = resolve_districts(conn, district)
    st = resolve_unit(conn, station, "station")[1] if station else None
    a, info = _as_of(conn, as_of)
    wk = a.history_end.isoformat()
    where, params = ["o.as_of_week = ?", "o.unit_type = ?", "o.category = ?", "o.horizon = ?"], \
        [wk, unit_type, cat, horizon]
    join = ""
    if dists or st:
        join = "JOIN geo_units g ON g.unit_type = o.unit_type AND g.unit = o.unit"
        if dists:
            where.append(f"g.district IN ({','.join('?' * len(dists))})"); params += dists
        if st:
            where.append("g.station = ?"); params.append(st)
    limit = max(1, min(int(limit), 500))
    q = (f"SELECT {', '.join('o.' + c for c in _COLS)} FROM forecast_output o {join} "
         f"WHERE {' AND '.join(where)} ORDER BY o.expected DESC, o.unit LIMIT ?")
    rows = [dict(zip(_COLS, r)) for r in conn.execute(q, (*params, limit))]
    total = conn.execute(f"SELECT COUNT(*), COALESCE(SUM(o.expected), 0) FROM forecast_output o "
                         f"{join} WHERE {' AND '.join(where)}", params).fetchone()
    geo = _geo(conn, unit_type, [r["unit"] for r in rows])
    gi = gi_star(a.as_of) if cat == ALL else None
    items = [_item(r, geo.get(r["unit"]), unit_type, cat, horizon, i + 1, gi)
             for i, r in enumerate(rows)]
    scope = st or " + ".join(dists) or "Karnataka"
    return {
        "as_of": _basis(a, info), "horizon_days": horizon,
        "target_weeks": [w.isoformat() for w in a.target_weeks(horizon)],
        "category": cat, "category_label": LABELS[cat], "unit_type": unit_type,
        "scope": scope, "district": " | ".join(dists) or None, "districts": dists, "station": st,
        "units_forecast": int(total[0]), "expected_total": round(float(total[1]), 1),
        "items": items, "evidence_class": "I",
        "bottom_line": (f"{items[0]['name']} ({items[0]['station'] or items[0]['district']}) "
                        f"has the highest forecast in {scope}: {items[0]['summary'][0].lower()}"
                        f"{items[0]['summary'][1:]}" if items else
                        f"No {LABELS[cat].lower()} is forecast in {scope} for the next {horizon} days."),
        "accuracy": accuracy(conn, unit_type, cat, horizon),
        "limits": [
            "Counts reported FIRs, not crime — an under-reporting area looks safe.",
            "The record has dates, not times: no time-of-day pattern is claimed.",
            "Places, never people. The officer decides; the map only proposes.",
        ],
    }


def layer(conn: sqlite3.Connection, *, horizon: int = 7, category: str | None = None,
          district: str | None = None, unit_type: str = "station", as_of: str | None = None) -> dict:
    """Every unit in scope, compact, for shading the map: quantile classes 0–4 over the
    units in view (0 = lowest fifth)."""
    horizon, unit_type = _check_horizon(horizon), _check_unit_type(unit_type)
    cat = resolve_category(category)
    dists = resolve_districts(conn, district)
    a, info = _as_of(conn, as_of)
    q = ("SELECT o.unit, g.lat, g.lon, o.expected, o.lo90, o.hi90, o.p_any, o.n52 "
         "FROM forecast_output o JOIN geo_units g ON g.unit_type = o.unit_type AND g.unit = o.unit "
         "WHERE o.as_of_week = ? AND o.unit_type = ? AND o.category = ? AND o.horizon = ? "
         "AND g.lat IS NOT NULL" + (f" AND g.district IN ({','.join('?' * len(dists))})" if dists else ""))
    params = [a.history_end.isoformat(), unit_type, cat, horizon] + dists
    rows = conn.execute(q, params).fetchall()
    vals = sorted(r[3] for r in rows)
    cuts = [vals[int(len(vals) * k / 5)] for k in range(1, 5)] if vals else []
    cls = lambda v: sum(v > c for c in cuts)
    return {
        "as_of": _basis(a, info), "horizon_days": horizon, "category": cat,
        "category_label": LABELS[cat], "unit_type": unit_type, "districts": dists,
        "fields": ["unit", "lat", "lon", "expected", "lo90", "hi90", "p_any", "class", "thin"],
        "units": [[u, round(la, 5), round(lo, 5), round(e, 2), _int(l9), _int(h9), round(p, 3),
                   cls(e), (n or 0) < THIN_N52] for u, la, lo, e, l9, h9, p, n in rows],
        "class_cuts": [round(c, 2) for c in cuts], "evidence_class": "I",
    }


def _category_groups(conn, cat: str) -> list[str]:
    groups = [g for g in _names(conn, "SELECT DISTINCT CrimeGroup_Name FROM FIRs")]
    return [g for g in groups if categorize(g) == cat]


_groups_cache: dict = {}


def unit_detail(conn: sqlite3.Connection, unit: str, *, unit_type: str | None = None,
                category: str | None = None, as_of: str | None = None,
                history_weeks: int = 26) -> dict:
    cat = resolve_category(category)
    ut, u = resolve_unit(conn, unit, unit_type)
    a, info = _as_of(conn, as_of)
    wk = a.history_end.isoformat()
    g = _geo(conn, ut, [u]).get(u, {})
    forecasts = {}
    for h in HORIZONS:
        row = conn.execute(f"SELECT {', '.join(_COLS)} FROM forecast_output WHERE as_of_week = ? "
                           f"AND unit_type = ? AND category = ? AND horizon = ? AND unit = ?",
                           (wk, ut, cat, h, u)).fetchone()
        forecasts[str(h)] = (_item(dict(zip(_COLS, row)), g, ut, cat, h, None, None) if row else None)
        if forecasts[str(h)]:
            forecasts[str(h)]["drivers"] = drivers(dict(zip(_COLS, row)), ut, h)

    series = info.get("series", "n")
    lo = (a.history_end - timedelta(weeks=history_weeks - 1)).isoformat()
    cat_sql = "" if cat == ALL else "AND category = ?"
    hist = dict(conn.execute(
        f"SELECT week_start, SUM({series}) FROM forecast_cube WHERE unit_type = ? AND unit = ? "
        f"{cat_sql} AND week_start BETWEEN ? AND ? GROUP BY week_start",
        (ut, u, *([cat] if cat != ALL else []), lo, wk)).fetchall())
    weeks = [a.history_end - timedelta(weeks=i) for i in range(history_weeks - 1, -1, -1)]
    history = [{"week_start": w.isoformat(), "firs": int(hist.get(w.isoformat(), 0) or 0)} for w in weeks]

    # the week ahead, as a point on the same chart
    f7 = forecasts.get("7")
    ahead = ([{"week_start": a.target_weeks(7)[0].isoformat(), "expected": f7["expected"],
               "lo80": f7["band80"]["lo"], "hi80": f7["band80"]["hi"],
               "lo90": f7["band90"]["lo"], "hi90": f7["band90"]["hi"]}] if f7 else [])

    # what this unit's FIRs are, over the year to the as-of date
    station = g.get("station") or u
    where = ["TRIM(UPPER(station)) = UPPER(TRIM(?))", "date BETWEEN ? AND ?"]
    params: list = [station, (a.history_end - timedelta(weeks=51)).isoformat(),
                    (a.history_end + timedelta(days=6)).isoformat()]
    if ut == "beat":
        where.append("UPPER(TRIM(Beat_Name)) = ?"); params.append(u.split(" | ", 1)[1])
    if series == "n_real":
        where.append("is_synthetic_row = 0")
    if cat != ALL:
        db = conn.execute("PRAGMA database_list").fetchone()[2]      # '' for :memory:
        grp = _groups_cache.get((db, cat)) if db else None
        if grp is None:
            grp = _category_groups(conn, cat)
            if db:
                _groups_cache[(db, cat)] = grp
        grp = grp or ["\x00"]
        where.append(f"CrimeGroup_Name IN ({','.join('?' * len(grp))})"); params += grp
    heads = [{"crime_head": h or "Not recorded", "firs": n} for h, n in conn.execute(
        f"SELECT CrimeHead_Name, COUNT(*) FROM FIRs WHERE {' AND '.join(where)} "
        f"GROUP BY 1 ORDER BY 2 DESC LIMIT 5", params)]

    by_cat = [{"category": c, "label": LABELS[c], "expected": round(e, 2),
               "lo80": _int(l8), "hi80": _int(h8)} for c, e, l8, h8 in conn.execute(
        "SELECT category, expected, lo80, hi80 FROM forecast_output WHERE as_of_week = ? AND "
        "unit_type = ? AND horizon = 7 AND unit = ? AND category != ? ORDER BY expected DESC LIMIT 6",
        (wk, ut, u, ALL))]

    name = display_name(u, ut)
    f = forecasts.get("7")
    return {
        "unit": u, "unit_type": ut, "name": name, "station": g.get("station"),
        "district": g.get("district"), "lat": g.get("lat"), "lon": g.get("lon"),
        "area_km2": g.get("area_km2"), "category": cat, "category_label": LABELS[cat],
        "as_of": _basis(a, info), "forecast": forecasts, "history": history, "ahead": ahead,
        "top_crime_heads": heads, "by_category_7d": by_cat,
        "track_record": track_record(conn, ut, cat, u),
        "accuracy": accuracy(conn, ut, cat, 7),
        "bottom_line": (f"{name}: {f['summary'][0].lower()}{f['summary'][1:]}" if f else
                        f"No FIRs of this kind at {name} in the last year; the forecast is ~0."),
        "evidence_class": "I",
        "limits": ["Counts reported FIRs, not crime.",
                   "Patrolling here records more FIRs here — rotate some patrols into "
                   "low-forecast beats."],
    }


def status(conn: sqlite3.Connection) -> dict:
    a = asof_mod.resolve(conn)
    runs = []
    try:
        for (wk,) in conn.execute("SELECT DISTINCT as_of_week FROM forecast_models ORDER BY 1"):
            info = R.run_info(conn, wk) or {}
            runs.append({"as_of_week": wk, "as_of": info.get("as_of"), "mode": info.get("mode"),
                         "real_share": info.get("real_share"), "built_at": info.get("built_at"),
                         "models": info.get("models")})
    except sqlite3.OperationalError:
        pass
    bt = backtest(conn)
    return {"as_of": a.to_dict(), "configured": asof_mod.ENV, "runs": runs,
            "backtest": ({"built_at": bt["built_at"], "window": bt["window"],
                          "headline": bt.get("headline")} if bt else None),
            "categories": [{"key": k, "label": v} for k, v in LABELS.items()],
            "districts": _names(conn, "SELECT DISTINCT district FROM geo_units WHERE n_real > 0 "
                                      "ORDER BY district"),
            "horizons_days": list(HORIZONS)}
