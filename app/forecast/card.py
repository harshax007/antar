"""The model card — generated, never typed.

Every claim here is read from something that ran: the model configuration in code, the
fitted models in forecast_models, the latest forecast run and the latest back-test in
forecast_meta. If the back-test has not been run, the card says accuracy is not yet
measured; it never fills the gap.

Replaces the hand-written card that described a model which did not run ("DBSCAN + 30-day
velocity") and claimed a provenance that was not true ("CCTNS live replica, updated
nightly") — plan items A5 and A6.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from app.forecast import asof as asof_mod
from app.forecast import backtest as BT
from app.forecast import features as F
from app.forecast import model as M
from app.forecast import run as R
from app.forecast.categories import CATEGORIES

NAME = "Antar Map Forecast"


def _pct(x: float | None) -> str:
    return "not measured" if x is None else f"{100 * x:.1f}%"


def _fallbacks(conn: sqlite3.Connection, as_of_week: str) -> list[str]:
    try:
        rows = conn.execute("SELECT DISTINCT category, fit FROM forecast_models WHERE as_of_week = ?",
                            (as_of_week,)).fetchall()
    except sqlite3.OperationalError:
        return []
    out = set()
    for cat, fit in rows:
        if json.loads(fit)["method"] != "glm":
            out.add(CATEGORIES.get(cat, cat))
    return sorted(out)


def build(conn: sqlite3.Connection, today: date | None = None) -> dict:
    a = asof_mod.resolve(conn, today=today)
    run_info = R.run_info(conn, a.history_end.isoformat()) or {}
    bt = BT.load(conn)
    head = (bt or {}).get("headline", {})
    beat, station = head.get("beat.ALL", {}), head.get("station.ALL", {})
    theft = head.get("beat.PROPERTY", {})
    real_end = a.real_end.isoformat() if a.real_end else "unknown"

    accuracy = None
    evaluation: list[str] = []
    if bt:
        w = bt["window"]
        accuracy = {
            "window": f"{w['first_target_week']} to {w['last_target_week']}",
            "origins": w["origins"], "refits": w["refits"], "measured_at": bt["built_at"],
            "model_version": bt["model_version"],
            "beat_all_7d": beat, "station_all_7d": station, "beat_property_7d": theft,
        }
        if beat:
            evaluation.append(
                f"Top 5% of beats (~{beat['top5_units']:,}) caught {_pct(beat['top5_caught'])} of "
                f"the next week's FIRs, against {_pct(beat['top5_caught_last4'])} for last-4-weeks "
                f"hotspots (ceiling {_pct(beat['top5_oracle'])}); better in "
                f"{beat['weeks_model_beats_last4']} of {beat['weeks']} weeks.")
            if "pai5" in beat:
                evaluation.append(
                    f"Predictive Accuracy Index at 5% of land: {beat['pai5']:.1f} "
                    f"({_pct(beat['pai5_hit'])} of crime on {_pct(beat['pai5_area'])} of land); "
                    f"last-4-weeks hotspots: {beat['pai5_last4']:.1f}.")
            evaluation.append(f"90% ranges contained the outcome {_pct(beat['coverage90'])} of the "
                              f"time; 80% ranges {_pct(beat['coverage80'])}.")
        if station:
            evaluation.append(
                f"Stations: top 5% caught {_pct(station['top5_caught'])} of next-week FIRs; "
                f"Poisson deviance {100 * station['deviance_gain']:.0f}% below the baseline.")
        evaluation.append(
            f"Rolling origin, {w['origins']} weeks ({w['first_target_week']} – "
            f"{w['last_target_week']}), refitted every {w['refit_every_weeks']} weeks on "
            f"past data only; real record only.")
    else:
        evaluation.append("Accuracy not yet measured — run `python -m app.forecast.backtest`.")

    basis = run_info.get("real_share")
    if basis is None:
        provenance_run = "No forecast has been computed for the current as-of week yet."
    elif basis >= 0.99:
        provenance_run = (f"Current forecasts: as of {run_info['as_of']}, built on the real record.")
    else:
        provenance_run = (f"Current forecasts: as of {run_info['as_of']}; "
                          f"{100 * basis:.0f}% of the last 13 weeks of history is real record, "
                          f"the rest is seeded demonstration data.")

    fallbacks = _fallbacks(conn, a.history_end.isoformat())
    bias = [
        "Forecasts count reported FIRs, not crime. An area that under-reports will look "
        "safe; Antar's reporting-silence check flags some of these, not all.",
        "Feedback loop: patrolling flagged beats records more FIRs there, which the next "
        "forecast reads as more crime. Rotate some patrols into low-forecast beats.",
        "Places and times only — never people. No individual is scored.",
        "The record has dates, not times: no hour-of-day patterns are claimed.",
        "Beat areas are estimated (Voronoi from beat centroids); the data carries no beat "
        "boundaries, so PAI is approximate.",
        "The registry's recording volume changes for reasons unrelated to crime (a 5× step "
        "in January 2023); counts are re-levelled to the as-of recording level.",
    ]
    if fallbacks:
        bias.append(f"Too few FIRs to fit a model for: {', '.join(fallbacks)} — these use the "
                    f"seasonal-naive + EWMA baseline.")
    if basis is not None and basis < 0.99:
        bias.append("The current forecast's recent history is largely seeded demonstration "
                    "data; its accuracy is measured on the real record.")

    return {
        "model_name": f"{NAME} v{R.MODEL_VERSION}",
        "type": "Poisson GLM with split-conformal ranges — police station and beat, 7 and 28 days",
        "architecture": (
            "Per crime category and unit (station, beat): a Poisson GLM whose offset is the "
            "unit's recent level (EWMA, half-life 4 weeks, shrunk toward its area), adjusted "
            "by recent weeks, the same weeks last year, neighbouring units, the wider area "
            "and season. Beats are reconciled to their station's forecast. 80% and 90% "
            "ranges are split-conformal on held-out weeks, per volume band. Inputs are "
            "clamped to their training range. Baseline for comparison: seasonal-naive + EWMA."),
        "intended_use": ("Where to look next week, and how sure: ranking police stations and "
                         "beats by expected FIRs to inform patrol proposals, which a "
                         "supervising officer approves. Not for decisions about individuals."),
        "evidence_class": "I",
        "bias_disclosure": bias,
        "false_positive_mitigation": (
            "No automatic action: a forecast can only propose a patrol, which goes to a named "
            "officer for approval. Every forecast carries a range, not just a number, and "
            "units with thin history are marked as such. Hotspots are also compared with "
            "Getis-Ord Gi* clusters so 'busy' is not confused with 'statistically clustered'."),
        "data_provenance": (
            f"Karnataka State Police FIR registry extract loaded into Antar's database — "
            f"the real record ends {real_end}; later rows are seeded demonstration data. "
            f"Not a live CCTNS feed. {provenance_run}"),
        "evaluation": evaluation,
        "accuracy": accuracy,
        "horizons_days": list(M.HORIZONS),
        "categories": len(CATEGORIES),
        "features": list(F.FEATURES),
        "as_of": a.to_dict(),
        "components": [
            {"name": "Map forecast", "status": "back-tested" if bt else "not yet back-tested",
             "what": "Expected FIRs per station and beat, next 7 and 28 days."},
            {"name": "Anomaly alerts",
             "status": "flags unusual weeks; not a forecast, so not in the back-test",
             "what": "MAD z-score and seasonal residual per zone and crime, Getis-Ord Gi* "
                     "hotspot significance, Bayesian reporting-silence check."},
        ],
        "generated": True,
    }
