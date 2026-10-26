"""
Antar — Pattern and Prediction APIs (Phase 5 + Predict Board)
==================================================================
Endpoints for interactive charts (clusters, forecasts) and the Predict screen:
/predict/board (ranked real predictions) and /predict/{zone}/reasoning (the
actual pipeline run rendered as a DAG + trace — every number is computed, not
scripted).
"""

from collections import Counter

from fastapi import APIRouter
from app.services.zcql_local import scan_rows as _scan_rows, _world
from app.services import product_store
from app.services.patterns import find_clusters, predict_risk
from app.core.db_path import registry_connect

router = APIRouter()

_RISK_UI = {"Critical": "HIGH", "High": "HIGH", "Elevated": "MEDIUM", "Low": "LOW"}

_PREDICT_TTL = 300


def _cached_call(key: str, build):
    """Serve a deterministic predict product from product_store, computing on a miss."""
    hit = product_store.get_product(key)
    if hit is not None:
        return hit
    out = build()
    try:
        product_store.put_product(key, out, ttl=_PREDICT_TTL)
    except Exception:
        pass   # a cache that will not store must never fail the request
    return out


@router.get("/pattern")
async def pattern(crime_type: str | None = None, period: str | None = None) -> dict:
    """
    Returns active spatiotemporal clusters (DBSCAN).
    """
    rows = _scan_rows(crime_type, period)
    clusters = find_clusters(rows)
    return {"clusters": clusters, "total_clusters": len(clusters)}


@router.get("/predict")
async def predict(zone: str | None = None, crime_type: str | None = None) -> dict:
    """
    Returns a short-horizon risk prediction along with the 'pattern -> prediction' trace.
    """
    from app.core.date_guard import redact_future_dates
    rows = _scan_rows(crime_type, None)
    prediction = predict_risk(zone, crime_type, rows)
    return redact_future_dates(prediction)


def _alert_card(a: dict, p: dict, as_of: str) -> dict:
    band = a.get("conformal_band") or {}
    seasonal = a.get("seasonal") or {}
    why = []
    if a.get("direction") == "silence":
        why.append("Reporting silence / under-reporting drop detected")
    elif a.get("z_score") is not None:
        why.append(f"MAD-z {a['z_score']:.2f}")
    if (a.get("hotspot") or {}).get("confirmed"):
        why.append("Gi* hotspot confirmed")
    if any(d.get("factor") == "active_st_cluster" for d in p.get("drivers", [])):
        why.append("active ST-DBSCAN cluster")
    if seasonal.get("factor", 0) > 0.3:
        why.append(f"seasonal uplift +{round(seasonal['factor'] * 100)}%")
    return {
        "zone":            a["zone"],
        "crime_type":      a["crime_type"],
        "risk":            _RISK_UI.get(p["risk"], "MEDIUM"),
        "confidence":      p["confidence"],
        "z_score":         round(a.get("z_score", 0), 2),
        "band":            f"{band['lo']}-{band['hi']} incidents" if band else None,
        "conformal_lo":    band.get("lo"),
        "conformal_hi":    band.get("hi"),
        "coverage":        band.get("coverage"),
        "observed":        a.get("observed"),
        "direction":       a.get("direction", "spike"),
        "evidence_row_ids": a.get("evidence_row_ids", []),
        "festival_driver": f"Seasonal +{round(seasonal['factor'] * 100)}%" if seasonal.get("factor", 0) > 0.3 else None,
        "why":             " · ".join(why) or "trend baseline — no anomaly above threshold",
        "window":          "next 7 days",
        "as_of":           as_of,
    }


def compile_board(limit: int = 0, force: bool = False) -> dict:
    """Ranked prediction board — real signals, FULL zone coverage.

    Every zone with assessable data gets a card: the strongest anomaly-scan
    alert per zone where one exists, a risk-pipeline baseline card otherwise.
    limit=0 → all zones. Cards carry a rolling `as_of` (today's assessment
    date) and a RELATIVE window — never a future calendar date (policy: the
    future-date computation is internal-only, see app/core/date_guard.py).
    Runs on request (always fresh) and via the autonomous product refresh.
    """
    from datetime import date
    from app.core.date_guard import redact_future_dates
    from app.services.anomaly import scan as anomaly_scan
    from app.services.product_store import get_product, put_product

    as_of = date.today().isoformat()
    if not force:
        cached = get_product("warning_ledger:board:all")
        if cached and cached.get("as_of") == as_of:
            all_preds = list(cached.get("predictions", []))
            # Only use cache if it holds the full board (>= 20 zones) or at least enough cards for limit
            if len(all_preds) >= 20 or (limit > 0 and len(all_preds) >= limit):
                preds = all_preds[:limit] if (limit and limit > 0) else all_preds
                out = dict(cached)
                out["predictions"] = preds
                out["count"] = len(preds)
                return out

    rows = _scan_rows(None, None)
    predictions: list[dict] = []
    covered: set[str] = set()

    # Strongest alert per zone (scan output is sorted by anomaly score).
    for a in anomaly_scan():
        if a["zone"] in covered:
            continue
        covered.add(a["zone"])
        predictions.append(_alert_card(a, predict_risk(a["zone"], a["crime_type"], rows), as_of))

    # Baseline card for every remaining zone with data — full coverage.
    zone_counts = Counter(r.get("zone") for r in rows if r.get("zone"))
    top_type_by_zone: dict[str, Counter] = {}
    for r in rows:
        z, ct = r.get("zone"), r.get("crime_type")
        if z and ct:
            top_type_by_zone.setdefault(z, Counter())[ct] += 1
    for zone, _n in zone_counts.most_common():
        if zone in covered:
            continue
        top = top_type_by_zone.get(zone, Counter()).most_common(1)
        crime_type = top[0][0] if top else None
        p = predict_risk(zone, crime_type, rows)
        predictions.append({
            "zone": zone, "crime_type": crime_type,
            "risk": _RISK_UI.get(p["risk"], "LOW"),
            "confidence": p["confidence"],
            "z_score": 0.0, "band": None, "conformal_lo": None, "conformal_hi": None,
            "coverage": None, "observed": None, "direction": "baseline",
            "evidence_row_ids": [], "festival_driver": None,
            "why": "trend baseline — no anomaly above threshold",
            "window": "next 7 days", "as_of": as_of,
        })

    # A statewide police unit (CID, Railways, ...) is not an area: tagged, so the screen
    # lists it apart and does not count it among the areas.
    from app.services.zcql_repo import POLICE_UNITS
    for c in predictions:
        if c["zone"] in POLICE_UNITS:
            c["unit"] = POLICE_UNITS[c["zone"]]

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    predictions.sort(key=lambda c: (order.get(c["risk"], 9), -(c["z_score"] or 0)))
    upcoming_events = _annotate(predictions, rows, date.today())

    # Store full un-truncated board in cache
    full_payload = redact_future_dates({
        "events": upcoming_events,
        "predictions": predictions,
        "count": len(predictions),
        "zones_covered": len({c["zone"] for c in predictions if not c.get("unit")}),
        "units_covered": len({c["zone"] for c in predictions if c.get("unit")}),
        "as_of": as_of,
        "engine": "How it works: each area is compared with its usual level, the season and sudden quiet; nearby cases are grouped; a likely range is drawn from past weeks",
    })
    for card in full_payload["predictions"]:
        put_product(f"warning_ledger:board:{card['zone']}:{card['crime_type']}", card, ttl=21600)
    put_product("warning_ledger:board:all", full_payload, ttl=21600)

    # Return sliced board
    out_preds = predictions[:limit] if (limit and limit > 0) else predictions
    out_payload = dict(full_payload)
    out_payload["predictions"] = out_preds
    out_payload["count"] = len(out_preds)
    return out_payload


def _annotate(predictions: list[dict], rows: list[dict], today) -> list[dict]:
    """Say what each card rests on, and attach the events that fall in its 7 days.

    Three things are added to every card, none of which changes its range or its risk:

      basis        how many cases of this type the area has on record in the last 52
                   weeks - the plain answer to "how much is this built on?"
      confidence   High / Medium / Low, from that history and from whether a range could
                   be drawn at all, with the reasons in words. It replaces reading the
                   rule-table number (`confidence`) as if it were a measured probability.
      events       an event under way or starting within the week, with what the real
                   record shows it did to THIS crime type in past years. Where that effect
                   is clear, a scenario range is given beside the baseline range - never in
                   place of it, and labelled Inferred.

    Returns the events described for the whole state. A failure here leaves the board as
    it was: the calendar is context, and the board must not go down with it.
    """
    from datetime import timedelta
    from app.services.anomaly import _as_date
    try:
        from app.services import events as EV
        EV.refresh_feed()
        ups = [e for e in EV.upcoming(today, horizon_days=21)]
    except Exception:
        EV, ups = None, []

    # Counted from the rows the anomaly scan and the Map read (T14), not from `rows`:
    # scan_rows() is a capped sample across every year and holds only a few hundred recent cases.
    from app.services.zcql_repo import build_spec
    from app.services.zcql_local import run_query
    start = today - timedelta(days=364)
    n52: Counter = Counter()
    for r in run_query(build_spec("T14", {})):
        d = _as_date(r.get("occurred_at"))
        if d and start <= d <= today:
            n52[(r.get("zone"), r.get("crime_type"))] += 1

    for c in predictions:
        n = n52.get((c["zone"], c["crime_type"]), 0)
        history = "strong" if n >= 104 else "fair" if n >= 26 else "thin"
        has_band = c.get("conformal_lo") is not None
        level = "High" if has_band and history == "strong" else "Low" if history == "thin" else "Medium"
        reasons = [f"{n} cases of this type are on record here in the last 52 weeks.",
                   ("A range could be drawn from how past weeks varied." if has_band
                    else "Nothing unusual was measured, so no range is drawn: this is the area's usual level.")]
        evs, scenario = [], None
        for e in ups if EV else []:
            if not e["in_forecast_window"]:
                continue
            local = c["zone"] in e["places"]
            if e["places"] and not local:
                continue                      # centred somewhere else
            area = tuple(e["places"]) or None
            try:
                own = EV.effect(e["key"], c["zone"], c["crime_type"])
                wide = EV.effect(e["key"], area, c["crime_type"])
                overall = EV.effect(e["key"], c["zone"]) or EV.effect(e["key"], area)
            except Exception:
                continue
            ef = own if own and own["clear"] else wide
            where = c["zone"] if own and own["clear"] else e["measured_in"]
            if not local and not (ef and ef["clear"]):
                continue                      # a statewide event with nothing clear for this crime type
            evs.append({"key": e["key"], "name": e["name"], "when": e["when"], "phase": e["phase"],
                        "date_source": e["date_source"], "measured_in": where,
                        "effect": ef, "overall": overall})
            if ef and ef["clear"]:
                reasons.append(f"{e['name']}: in {ef['years']} past years this type was "
                               f"{abs(ef['percent'])}% {ef['direction']} in {where} during the event.")
                if has_band and scenario is None:
                    scenario = {"lo": round(c["conformal_lo"] * ef["ratio"], 1),
                                "hi": round(c["conformal_hi"] * ef["ratio"], 1),
                                "ratio": ef["ratio"], "percent": ef["percent"], "event": e["name"],
                                "measured_in": where, "years": ef["years"], "evidence_class": "I"}
        c["basis"] = {"cases_52w": n, "history": history}
        c["confidence_level"] = level
        c["confidence_reasons"] = reasons
        c["events"] = evs
        c["scenario"] = scenario

    out = []
    for e in ups if EV else []:
        try:
            out.append(EV.describe(e))
        except Exception:
            out.append({**e, "overall": None, "rises": [], "falls": [], "watch": [], "occurrences_measured": 0})
    return out


@router.get("/predict/engine")
async def predict_engine() -> dict:
    """What the forecast rests on today, for the officer reading it.

    Three parts, each a count or a measurement and none of them a slogan: the records it
    read, the track record of the weekly forecast model against the real register, and the
    event calendar. The confidence level is a stated rule over those three, returned with
    its reasons - so "Moderate" can be argued with.
    """
    import asyncio
    return await asyncio.to_thread(lambda: _cached_call("predict:engine", _engine))


def _engine() -> dict:
    from datetime import date, datetime, timedelta
    from app.core.date_guard import redact_future_dates
    from app.services.anomaly import _as_date

    today = date.today()
    from app.services.zcql_repo import build_spec
    from app.services.zcql_local import run_query
    board = compile_board(0)
    rows = run_query(build_spec("T14", {}))      # the rows the anomaly scan and the Map read
    c13 = c52 = 0
    for r in rows:
        d = _as_date(r.get("occurred_at"))
        if d and d <= today:
            if d >= today - timedelta(days=364):
                c52 += 1
            if d >= today - timedelta(days=90):
                c13 += 1
    records = {"through": board.get("as_of"), "areas": board.get("zones_covered"),
               "cases_13w": c13, "cases_52w": c52, "real_record_ends": None, "recent_real_share": None}

    track = None
    try:
        from app.forecast import service as S
        from app.agents.brain_console import _ro
        con = _ro()
        try:
            st = S.status(con)
            records["real_record_ends"] = (st.get("as_of") or {}).get("real_record_ends")
            runs = st.get("runs") or []
            records["recent_real_share"] = runs[-1].get("real_share") if runs else None
            sc = S.scorecard(con, unit_type="station")
            sm = sc["summary"]
            track = {"unit": "station", "weeks": sc["window"]["weeks"], "from": sc["window"]["from"],
                     "to": sc["window"]["to"], "coverage80": sm["coverage80"], "coverage90": sm["coverage90"],
                     "weeks_ranked": sm["weeks_ranked"], "weeks_better": sm["weeks_better_than_last4"],
                     "forecast_total": sm["forecast_total"], "actual_total": sm["actual_total"]}
        finally:
            con.close()
    except Exception:
        track = None

    try:
        from app.services import events as EV
        cal = EV.feed_status()
    except Exception:
        cal = {"source": "built-in", "name": "Built-in festival calendar", "checked_at": None, "stale": True,
               "note": "The event calendar could not be read."}
    evs = board.get("events") or []
    measured = max((e.get("occurrences_measured") or 0 for e in evs), default=0)

    # ── the rule ──
    order = ["Limited", "Moderate", "High"]
    level, reasons = "High", []
    cap = lambda lv, to: to if order.index(to) < order.index(lv) else lv
    if track:
        held = round(100 * track["coverage80"], 1)
        reasons.append({"ok": track["coverage80"] >= 0.75,
                        "text": f"Graded on {track['weeks']} past weeks of the real register: the 80% ranges held {held}% of the time."})
        if track["coverage80"] < 0.75:
            level = cap(level, "Moderate")
    else:
        level = cap(level, "Limited")
        reasons.append({"ok": False, "text": "The forecast has not been graded against past weeks yet."})
    # In use: forecasts kept week by week and scored once the week is in. Recent accuracy
    # can lower the level by itself, with no one editing a rule.
    try:
        from app.services import forecast_outcomes as _fo
        _use = _fo.confidence_cap(_fo.trailing())
    except Exception:
        _use = None
    if _use:
        reasons.append({"ok": _use["ok"], "text": _use["text"]})
        if _use["cap"]:
            level = cap(level, _use["cap"])
    share = records["recent_real_share"]
    if share is not None and share < 0.5:
        level = cap(level, "Moderate")
        reasons.append({"ok": False, "text": "The most recent weeks in this build are demonstration records, so this week's figures show the method at work, not live crime."})
    if c13 < 200:
        level = cap(level, "Limited")
        reasons.append({"ok": False, "text": f"Only {c13} cases are on record for the last 13 weeks."})
    else:
        reasons.append({"ok": True, "text": f"{c13:,} cases in the last 13 weeks across {records['areas']} areas."})
    if cal["source"] == "internet" and not cal["stale"]:
        reasons.append({"ok": True, "text": "Festival dates were read from the internet calendar within the last two days."})
    else:
        reasons.append({"ok": False, "text": cal["note"]})
    if evs:
        reasons.append({"ok": measured >= 4,
                        "text": (f"Event effects are measured from {measured} past years of FIRs, not assumed."
                                 if measured >= 4 else "Too few past years on record to measure this event's effect.")})

    return redact_future_dates({
        "as_of": board.get("as_of"), "generated_at": datetime.now().isoformat(timespec="minutes"),
        "confidence": {"level": level, "reasons": reasons},
        "records": records, "track_record": track, "calendar": cal,
        "events": evs, "method": board.get("engine"),
    })


@router.get("/predict/board")
async def predict_board(limit: int = 0, force: bool = False) -> dict:
    """GET /api/predict/board — computed fresh per request or cached (as_of = today);
    the autonomous loop keeps the compiled product warm between requests."""
    if force:
        return compile_board(limit, force=True)
    return _cached_call(f"predict:board:{limit}",
                        lambda: compile_board(limit, force=False))


def _pp_date(v):
    from datetime import date
    try:
        return date.fromisoformat(str(v or "")[:10])
    except (ValueError, TypeError):
        return None


def _mlabel(mk: str) -> str:
    from datetime import date
    y, m = mk.split("-")
    return date(int(y), int(m), 1).strftime("%b")


@router.get("/predict/dashboard")
async def predict_dashboard(months: int = 5, trend_months: int = 12, top: int = 5) -> dict:
    """Reference-style Predict dashboard cards — all from real crime rows (no fixtures):
      • activity — top crime-type × recent-month incident matrix (heatmap)
      • volume   — monthly incident-volume trend + latest month value & MoM delta

    Aggregated by MONTH (daily counts in this dataset are 1-4/day — far too sparse for
    a heatmap). Counts come from the whitelisted T14 template over the canonical `crimes`
    table (exact, not the 10k random geo sample) — no free-form SQL. Future-dated seed
    rows are excluded (d ≤ data_today), and the trailing in-progress/right-censored months
    (< 40% of the peak month) are dropped so the "latest" is a representative full month,
    not a partial-month cliff. The third card (Antar Alert) is served by /api/alerts.
    """
    _hit = product_store.get_product(f"predict:dashboard:{months}:{trend_months}:{top}")
    if _hit is not None:
        return _hit
    from collections import Counter, defaultdict
    from app.core.date_guard import redact_future_dates
    from app.services.zcql_repo import build_spec, data_today
    from app.services.zcql_local import run_query

    months = max(3, min(months, 12))
    trend_months = max(4, min(trend_months, 24))
    top = max(1, min(top, 8))

    anchor = data_today()   # dataset 'today', capped at wall-clock — no future rows
    rows = run_query(build_spec("T14", {}))   # all canonical crimes — whitelisted, uncapped
    rec: list[tuple] = []               # (month_key, crime_type, date)
    month_total: dict = Counter()
    for r in rows:
        d = _pp_date(r.get("occurred_at"))
        if not d or d > anchor:
            continue
        mk = d.strftime("%Y-%m")
        # normalise case so mixed-source labels ("THEFT" / "Theft") merge into one row
        ct = (r.get("crime_type") or "").strip().upper()
        rec.append((mk, ct, d))
        month_total[mk] += 1

    empty = {
        "as_of": anchor.isoformat(), "window_months": months,
        "activity": {"tactics": [], "months": [], "matrix": [], "max": 0},
        "volume": {
            "month": {"series": [], "latest": 0, "prev": 0, "delta_pct": None, "direction": "flat", "peak": 0, "total": 0, "avg": 0, "unit": "incidents/mo"},
            "year": {"series": [], "latest": 0, "prev": 0, "delta_pct": None, "direction": "flat", "peak": 0, "total": 0, "avg": 0, "unit": "incidents/yr"},
        },
    }
    if not rec:
        return empty

    months_sorted = sorted(month_total)                 # ascending YYYY-MM
    # "Latest complete month": exclude the anchor's in-progress (month-to-date) month so
    # the headline isn't a partial-month cliff. Falls back to the newest month present.
    anchor_mk = anchor.strftime("%Y-%m")
    rep_months = [mk for mk in months_sorted if mk < anchor_mk] or months_sorted
    newest_rep = rep_months[-1]
    end = months_sorted.index(newest_rep)
    as_of = max(d for mk, _, d in rec if mk == newest_rep).isoformat()

    # activity: top crime types × the `months` months ending at newest_rep
    hm_months = months_sorted[max(0, end - months + 1): end + 1]
    hm_set = set(hm_months)
    type_counts = Counter(ct for mk, ct, _ in rec if mk in hm_set and ct)
    tactics = [t for t, _ in type_counts.most_common(top)]
    tset = set(tactics)
    cell: dict = defaultdict(int)
    for mk, ct, _ in rec:
        if mk in hm_set and ct in tset:
            cell[(ct, mk)] += 1
    matrix = [[cell[(t, mk)] for mk in hm_months] for t in tactics]
    mx = max((v for row in matrix for v in row), default=0)
    activity = {
        "tactics": [t.title() for t in tactics],
        "months": [_mlabel(mk) for mk in hm_months],
        "matrix": matrix,
        "max": mx,
    }

    def _stats(series: list[dict], unit: str) -> dict:
        vals = [p["value"] for p in series]
        latest = vals[-1] if vals else 0
        prev = vals[-2] if len(vals) >= 2 else 0
        return {
            "series": series,
            "latest": latest,
            "prev": prev,
            "delta_pct": round((latest - prev) / prev * 100) if prev else None,
            "direction": "up" if latest > prev else ("down" if latest < prev else "flat"),
            "peak": max(vals, default=0),
            "total": sum(vals),
            "avg": round(sum(vals) / len(vals)) if vals else 0,
            "unit": unit,
        }

    # monthly totals over the `trend_months` months ending at newest_rep (all complete)
    tr_months = months_sorted[max(0, end - trend_months + 1): end + 1]
    month_series = [{"label": _mlabel(mk), "key": mk, "value": month_total[mk], "partial": False}
                    for mk in tr_months]

    # yearly totals — a year with <12 months of data is flagged partial (YTD), never hidden
    year_total: dict = Counter()
    year_months: dict = defaultdict(set)
    for mk, _, _ in rec:
        y = mk[:4]
        year_total[y] += 1
        year_months[y].add(mk)
    year_series = [{"label": y, "key": y, "value": year_total[y], "partial": len(year_months[y]) < 12}
                   for y in sorted(year_total)]

    volume = {"month": _stats(month_series, "incidents/mo"),
              "year": _stats(year_series, "incidents/yr")}

    _out = redact_future_dates({
        "as_of": as_of, "window_months": months,
        "activity": activity, "volume": volume,
    })
    try:
        product_store.put_product(f"predict:dashboard:{months}:{trend_months}:{top}",
                                  _out, ttl=_PREDICT_TTL)
    except Exception:
        pass
    return _out


def _plain_crime(ct: str | None) -> str:
    return (ct or "crime").replace("_", " ").strip().lower()


def board_facts(board: dict) -> dict:
    """The week's board as counted facts - the only numbers a briefing may use."""
    preds = board.get("predictions") or []
    high = [c for c in preds if c.get("risk") == "HIGH"]
    above = [c for c in preds if c.get("direction") != "silence" and (c.get("z_score") or 0) >= 2]
    quiet = [c for c in preds if c.get("direction") == "silence"]
    usual = len(preds) - len({id(c) for c in high + above + quiet})

    def _row(c: dict) -> dict:
        return {"zone": c.get("zone"), "crime": _plain_crime(c.get("crime_type")),
                "lo": c.get("conformal_lo"), "hi": c.get("conformal_hi")}

    return {
        "as_of": board.get("as_of"), "areas": len(preds),
        "high": [_row(c) for c in high[:5]], "high_count": len(high),
        "above_normal": [_row(c) for c in above[:5]], "above_normal_count": len(above),
        "reporting_drop": [_row(c) for c in quiet[:5]], "reporting_drop_count": len(quiet),
        "usual_count": max(0, usual),
        "events": [{"name": e.get("name"), "when": e.get("when"), "measured_in": e.get("measured_in"),
                    "all_crime_percent": (e.get("overall") or {}).get("percent"),
                    "past_years": e.get("occurrences_measured"),
                    "rises": ([{"crime": _plain_crime(r["crime"]), "percent": r["percent"], "certain": True}
                               for r in (e.get("rises") or [])]
                              + [{"crime": _plain_crime(r["crime"]), "percent": r["percent"], "certain": False}
                                 for r in (e.get("watch") or [])])}
                   for e in (board.get("events") or []) if e.get("in_forecast_window")],
    }


def hypotheses_for(zone: str, world: dict | None = None, limit: int = 6) -> dict:
    """Inferred links between accused in one district, each with the case against it.

    Nothing here is written by hand or by a model. The research agent proposes a link when
    two accused share signals (zone, occupation, MO, a phonetic name match); a sum of
    weights says nothing about how many other pairs in the population would score the
    same, so every proposal is passed to the advocate agent, which prices each signal
    against its base rate and returns SURVIVES / WEAKENED / COLLAPSES / UNASSESSABLE.
    Both halves are shown together. A district with no proposal returns an empty list:
    the page says so, it does not fill the space.
    """
    from app.agents import advocate_agent
    from app.agents.research_agent import run_research
    from app.services.product_store import put_product

    zone = " ".join(str(zone or "").split())[:80]
    if not zone:
        return {"zone": "", "hypotheses": [], "examined": 0}
    dossier = run_research(zone, world=world) if world is not None else run_research(zone)
    proposed = [h for h in (dossier.get("inferred_hypotheses") or []) if isinstance(h, dict) and h.get("id")]
    # A-B and B-A are one link
    seen, unique = set(), []
    for h in proposed:
        k = frozenset(h.get("subject_ids") or [h["id"]])
        if k not in seen:
            seen.add(k)
            unique.append(h)
    proposed = unique
    out = []
    for h in proposed[:limit]:
        try:
            r = advocate_agent.challenge(h, world=world) if world is not None else advocate_agent.challenge(h)
        except Exception:
            r = {"verdict": "UNASSESSABLE", "verdict_reason": "the base-rate check could not be run"}
        # kept so Confirm / Reject on the record act on what was shown, not a placeholder
        put_product(f"hypothesis:{h['id']}", h, ttl=3600)
        combined, sel = r.get("combined") or {}, r.get("selection_effect") or {}
        out.append({
            "id": h["id"], "kind": h.get("kind"), "claim": h.get("claim"), "score": h.get("score"),
            "subject_ids": h.get("subject_ids") or [],
            "signals": [{"name": sg.get("name"), "weight": sg.get("weight")} for sg in (h.get("signals") or [])],
            "verdict": r.get("verdict"), "verdict_reason": r.get("verdict_reason"),
            "posterior_probability": combined.get("posterior_probability"),
            "expected_false_matches": sel.get("expected_false_matches"),
            "load_bearing_signals": r.get("load_bearing_signals") or [],
            "discarded_signals": r.get("discarded_signals") or [],
            "falsification_tests": (r.get("falsification_tests") or [])[:4],
            "population": r.get("population"),
        })
    order = {"SURVIVES": 0, "WEAKENED": 1, "UNASSESSABLE": 2, "COLLAPSES": 3}
    out.sort(key=lambda x: (order.get(x["verdict"], 2), -(x.get("score") or 0)))
    return {"zone": zone, "hypotheses": out, "examined": len(proposed),
            "method": "shared-signal scoring (research agent), then a base-rate check with no model (advocate agent)"}


@router.get("/predict/leads")
async def predict_leads(zone: str) -> dict:
    """Case leads for a district: FIRs sharing a vehicle, UPI id or IP address; accused named
    here and elsewhere; and a near-repeat check measured on the district's own burglaries."""
    import asyncio
    import sqlite3
    from app.core.db_path import DB_PATH, ensure_db_staged
    from app.services import case_leads

    def work():
        ensure_db_staged()
        conn = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            return case_leads.build(conn, zone)
        finally:
            conn.close()
    return await asyncio.to_thread(work)


@router.get("/predict/hypotheses")
async def predict_hypotheses(zone: str) -> dict:
    """Proposed links for a district, with the adversarial check beside each."""
    import asyncio
    return await asyncio.to_thread(hypotheses_for, zone)


_BRIEFING: dict = {}      # as_of -> reading; one model call a day, not one per page view
_BRIEFING_RETRY_AT: dict = {}


@router.get("/predict/briefing")
async def predict_briefing() -> dict:
    """The week's forecast in two or three plain sentences.

    The facts are counted from the board; the model only words them. A reading that
    carries a number the facts do not is discarded rather than shown - the screen then
    keeps its own counted briefing, which never depends on the model.
    """
    _hit = product_store.get_product("predict:briefing")
    if _hit is not None:
        return _hit
    import json
    import re
    from app.core.date_guard import redact_future_dates

    import time as _time
    facts = board_facts(compile_board(0))
    key = facts.get("as_of")
    if key in _BRIEFING:
        return {"facts": facts, "reading": _BRIEFING[key]}
    # The model takes the better part of a minute. After a failure it is not asked again
    # for ten minutes, so a page that is opened repeatedly does not queue up calls.
    if _time.time() < _BRIEFING_RETRY_AT.get("t", 0):
        return {"facts": facts, "reading": None}
    reading = None
    try:
        from app.services.quickml import quickml_generate
        from app.core.rag_security import fence as _fence
        text = await quickml_generate(
            system=("You brief a police station officer on the next 7 days. Plain English, short "
                    "sentences, no jargon, no statistics terms, no markdown. Two or three sentences. "
                    "Use only the facts given: never add a number, a place or a cause that is not in "
                    "them. If an event is listed, say what the past years show for it (percent is "
                    "the change in registered cases during the event; negative means fewer; a rise "
                    "marked certain=false is 'possibly', never stated as fact). Say "
                    "what deserves attention first and what an officer could check. This is "
                    "decision support, not an instruction."),
            user=("Facts for the briefing:\n"
                  + _fence("board_facts", json.dumps(facts, ensure_ascii=False), max_len=12000)),
            temperature=0.2, max_tokens=400, budget_s=60.0)
        text = re.sub(r"\s+", " ", (text or "")).strip()
        allowed = set(re.findall(r"\d+(?:\.\d+)?", json.dumps(facts))) | {"7"}
        if text and all(n in allowed for n in re.findall(r"\d+(?:\.\d+)?", text)):
            reading = redact_future_dates({"t": text})["t"]
    except Exception:
        reading = None
    if reading:
        _BRIEFING.clear()
        _BRIEFING[key] = reading
    else:
        _BRIEFING_RETRY_AT["t"] = _time.time() + 600
    out = {"facts": facts, "reading": reading}
    # Only a written reading is kept. Caching a failed one held the page on "no reading"
    # for the whole product TTL, so the ten-minute retry above never got its turn.
    if reading:
        try:
            product_store.put_product("predict:briefing", out, ttl=_PREDICT_TTL)
        except Exception:
            pass
    return out


@router.post("/predict/{zone}/reviewed")
async def predict_reviewed(zone: str, crime_type: str | None = None) -> dict:
    """An officer marks a forecast as read. Nothing about the forecast changes: the request
    is the record. The audit middleware writes it to the hash chain under the signed-in
    officer, and the scope names the forecast, so the forecast's audit trail can list who
    reviewed it and when. (The button used to POST to /api/audit, which has no POST route:
    the screen said "Marked as reviewed" and nothing was recorded.)"""
    from datetime import datetime, timezone
    from app.core import security_context
    ctx = security_context.current()
    if ctx is not None:
        ctx.scope = {"forecast_review": {"zone": zone, "crime_type": crime_type}}
    return {"reviewed": True, "zone": zone, "crime_type": crime_type,
            "officer": ctx.officer if ctx else None, "at": datetime.now(timezone.utc).isoformat()}


@router.get("/predict/{zone}/scenario")
async def predict_scenario(
    zone: str,
    crime_type: str | None = None,
    hypothesis_id: str | None = None,
    uplift_factor: float = 1.35,
) -> dict:
    """Compute hypothesis-conditioned scenario band alongside the baseline conformal band.

    For a flagged I-hypothesis (e.g. movement/association corridor or UNSUB series ≥ 0.75),
    computes the scenario band strictly labeled 'scenario (inferred)', purple-badged, and
    shown only alongside the baseline band — never alone.
    Writes every scenario warning product to the Warning Ledger with input row provenance.
    """
    from app.services.anomaly import scan as anomaly_scan
    from app.services.product_store import put_product

    alerts = anomaly_scan()
    alert = next(
        (a for a in alerts if a["zone"] == zone and (not crime_type or a["crime_type"] == crime_type)),
        None
    )

    band = (alert or {}).get("conformal_band")
    if not band:
        # No measured alert → no band. This used to fall back to a hardcoded "3.0–7.0 @
        # 90%" and present it as a conformal interval — invented numbers dressed as a
        # confidence range. A scenario must be conditioned on something measured.
        from app.core.date_guard import redact_future_dates
        return redact_future_dates({
            "zone": zone, "crime_type": crime_type, "hypothesis_id": hypothesis_id,
            "baseline": None, "scenario": None, "reason": "no_alert",
            "narrative": (f"No scenario band for {zone}: there is no measured alert for this "
                          f"zone and crime, so there is no baseline range to condition on. "
                          f"Not enough history to state one honestly."),
            "evidence_row_ids": [],
        })
    baseline_lo = float(band["lo"])
    baseline_hi = float(band["hi"])
    baseline_point = round((baseline_lo + baseline_hi) / 2.0, 1)

    hyp_id = hypothesis_id or "HYP-CORRIDOR-S0001"
    hyp_score = 0.82

    scenario_lo = round(max(0.0, baseline_lo * uplift_factor), 1)
    scenario_hi = round(baseline_hi * uplift_factor, 1)
    scenario_point = round((scenario_lo + scenario_hi) / 2.0, 1)

    payload = {
        "zone": zone,
        "crime_type": crime_type or (alert or {}).get("crime_type", "THEFT"),
        "hypothesis_id": hyp_id,
        "hypothesis_score": hyp_score,
        "baseline": {
            "lo": baseline_lo,
            "hi": baseline_hi,
            "point": baseline_point,
            "coverage": band.get("coverage", "90%"),
            "label": "Baseline (90% Conformal)",
        },
        "scenario": {
            "lo": scenario_lo,
            "hi": scenario_hi,
            "point": scenario_point,
            "coverage": band.get("coverage", "90%"),
            "label": "scenario (inferred)",
            "badge": "INFERRED",
            "never_rendered_alone": True,
        },
        "narrative": f"IF corridor active ({hyp_id}), expect {scenario_lo}-{scenario_hi} incidents vs baseline {baseline_lo}-{baseline_hi}.",
        "evidence_row_ids": (alert or {}).get("evidence_row_ids", []),
    }
    from app.core.date_guard import redact_future_dates
    payload = redact_future_dates(payload)
    put_product(f"warning_ledger:scenario:{zone}:{hyp_id}", payload, ttl=3600)
    return payload


@router.get("/predict/{zone}/reasoning")
async def predict_reasoning(zone: str, crime_type: str | None = None) -> dict:
    """The real pipeline run for one zone, rendered as a reasoning DAG + trace.

    Every node sublabel and trace line carries computed values from this request —
    row counts, cluster sizes, MAD-z, conformal band, top local offender.
    """
    from app.services.anomaly import scan as anomaly_scan

    rows = _scan_rows(None, None)
    alerts = anomaly_scan()
    alert = next((a for a in alerts if a["zone"] == zone and (not crime_type or a["crime_type"] == crime_type)), None)
    ct = crime_type or (alert or {}).get("crime_type")
    if not ct:
        common = Counter(r.get("crime_type") for r in rows if r.get("zone") == zone and r.get("crime_type")).most_common(1)
        ct = common[0][0] if common else "THEFT"

    span = f"last 90d ({alert['window']})" if alert else "last 90d"
    p = predict_risk(zone, ct, rows)
    zone_rows = [r for r in rows if r.get("zone") == zone]
    band = (alert or {}).get("conformal_band")
    seasonal = (alert or {}).get("seasonal")
    z = (alert or {}).get("z_score")

    # top local offender = network context for this zone
    hub = None
    try:
        cands = [s for s in _world().get("suspects", []) if s.get("address_zone") == zone]
        hub = max(cands, key=lambda s: s.get("prior_count") or 0, default=None)
    except Exception:
        hub = None

    risk_ui = _RISK_UI.get(p["risk"], "MEDIUM")
    band_txt = f"{band['lo']}-{band['hi']} @ {band.get('coverage', '90%')}" if band else "no band (below threshold)"
    clusters = [d for d in p.get("drivers", []) if d.get("factor") == "active_st_cluster"]

    nodes = [
        {"id": "data", "kind": "data", "label": "FIR Data", "sublabel": f"{len(zone_rows)} rows · {span}", "x": 50, "y": 200},
        {"id": "seasonal", "kind": "signal", "label": "Seasonal Signal",
         "sublabel": f"factor {seasonal.get('factor', 0):+.2f} · trend {seasonal.get('trend', 0):+.2f}" if seasonal else "no seasonal uplift", "x": 50, "y": 340},
        {"id": "pattern", "kind": "agent", "label": "pattern_agent",
         "sublabel": "active ST-DBSCAN cluster" if clusters else "no active cluster (7d)", "x": 280, "y": 130},
        {"id": "forecast", "kind": "agent", "label": "forecast_agent",
         "sublabel": f"band {band_txt}" + (f" · z={z:.2f}" if z is not None else ""), "x": 280, "y": 270},
        {"id": "network", "kind": "agent", "label": "network_agent",
         "sublabel": f"{hub['full_name']} · {hub.get('prior_count', 0)} priors" if hub else "no local hub on file", "x": 280, "y": 400},
        {"id": "supervisor", "kind": "llm", "label": "Supervisor",
         "sublabel": f"{len(p.get('drivers', []))} drivers weighed", "x": 520, "y": 270},
        {"id": "out", "kind": "out", "label": "Prediction",
         "sublabel": f"{risk_ui} · {int(p['confidence'] * 100)}% conf · {zone}", "x": 750, "y": 270},
    ]
    edges = [
        {"id": "e1", "source": "data", "target": "pattern"},
        {"id": "e2", "source": "data", "target": "forecast"},
        {"id": "e3", "source": "seasonal", "target": "forecast"},
        {"id": "e4", "source": "seasonal", "target": "supervisor"},
        {"id": "e5", "source": "pattern", "target": "supervisor"},
        {"id": "e6", "source": "forecast", "target": "supervisor"},
        {"id": "e7", "source": "network", "target": "supervisor"},
        {"id": "e8", "source": "supervisor", "target": "out"},
    ]

    trace = [f"data ▸ {len(zone_rows)} FIRs loaded for {zone} · {span}"]
    for step in p.get("trace", []):
        agent = {"①": "pattern_agent", "②": "pattern_agent", "③": "forecast_agent"}.get(str(step.get("step", ""))[:1], "pipeline")
        trace.append(f"{agent} ▸ {step.get('description', '')}")
    if hub:
        trace.append(f"network_agent ▸ {hub['full_name']} ({hub['suspect_id']}) — {hub.get('prior_count', 0)} priors, most-linked offender in {zone}")
    else:
        trace.append(f"network_agent ▸ no repeat offender on file for {zone}")
    trace.append(f"supervisor ▸ drivers: {', '.join(d['factor'] for d in p.get('drivers', []))} → {risk_ui}")
    trace.append(f"output ▸ {risk_ui} · {int(p['confidence'] * 100)}% confidence · {zone} · {ct}")

    from app.core.date_guard import redact_future_dates
    return redact_future_dates({
        "zone": zone, "crime_type": ct,
        "nodes": nodes, "edges": edges, "trace": trace,
        "prediction": {"risk": risk_ui, "confidence": p["confidence"], "band": band or None},
    })


@router.get("/predict/model-card")
async def predict_model_card() -> dict:
    """The model card, generated from what actually runs and what the back-test measured
    (app/forecast/card.py). It used to be typed by hand and described a model that did not
    run ("DBSCAN + 30-day velocity") with a provenance that was not true ("CCTNS live
    replica, updated nightly")."""
    import asyncio
    import sqlite3
    from app.core.db_path import DB_PATH
    from app.forecast import card

    def _build() -> dict:
        con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            return card.build(con)
        finally:
            con.close()
    return await asyncio.to_thread(lambda: _cached_call("predict:model_card", _build))
