"""
Fairness and feedback: what the back-test shows about WHERE the forecast points
==============================================================================
A forecast of registered FIRs can become a loop: it points at the places with the most
registrations, more policing there registers more, and the next forecast points there
again. This module measures how far the back-test's own flags behave like that, from the
stored back-test (no refit), and says what it cannot measure yet.

    python -m app.forecast.fairness        writes docs/FORECAST_FAIRNESS.md

Measured, for "the top 5% of units by forecast, next 7 days, all crime":

  persistence     how many distinct units were ever flagged, how many were flagged in every
                  week, and what share of all flags the always-flagged units took
  where           the share of flags that fell in city commissionerates against districts,
                  beside the share of registered cases there - is a group flagged more than
                  its cases would explain?
  level           forecast total over recorded total for the flagged units of each group:
                  does the engine over-forecast one group?
  ranges          how often the likely range held for quiet units against busy ones

Not measured, and said so: forecast error for units that were never flagged (the stored
back-test keeps per-unit totals for flagged units only), and any effect of policing on
registration - that needs deployment data this system does not hold.

The engine uses no feature about a person or a community (app/forecast/features.py). That
is a property of the code and is tested; it is not a measurement and is not presented as one.
"""
from __future__ import annotations

import sqlite3

from app.forecast import service as S
from app.forecast.features import ALL
from app.core.db_path import registry_connect


def _group(district: str | None) -> str:
    """City commissionerates against the rest. From the district's own name in the register."""
    return "city" if str(district or "").strip().lower().endswith("city") else "district"


def measure(conn: sqlite3.Connection, unit_type: str = "station") -> dict | None:
    bt = S.backtest(conn)
    m = ((bt or {}).get("results", {}).get(unit_type, {}).get(ALL, {}) or {}).get("7")
    if not m or "units" not in m:
        return None
    weeks = m["capture"]["top_5pct"]["weeks"]
    per_week = m["capture"]["top_5pct"]["units"]
    pool = m["rows"] // max(1, m["origins"])
    units = m["units"]                                  # unit -> [weeks flagged, weeks with crime, forecast, actual]
    slots = sum(v[0] for v in units.values())
    always = [u for u, v in units.items() if v[0] == weeks]
    geo = S._geo(conn, unit_type, list(units))

    groups: dict[str, dict] = {g: {"units": 0, "flags": 0, "forecast": 0.0, "actual": 0.0} for g in ("city", "district")}
    for u, v in units.items():
        g = groups[_group((geo.get(u) or {}).get("district"))]
        g["units"] += 1
        g["flags"] += v[0]
        g["forecast"] += v[2]
        g["actual"] += v[3]
    total_actual = sum(g["actual"] for g in groups.values()) or 1.0
    by_group = []
    for name, g in groups.items():
        by_group.append({
            "group": "City commissionerates" if name == "city" else "Districts",
            "flagged_units": g["units"],
            "share_of_flags": round(g["flags"] / slots, 3) if slots else None,
            "share_of_cases_among_flagged": round(g["actual"] / total_actual, 3),
            "forecast_over_recorded": round(g["forecast"] / g["actual"], 3) if g["actual"] else None,
        })

    cov = m["coverage"]["80"].get("by_volume") or {}
    ranges = [{"usual_weekly_cases": k, "held": v["coverage"], "forecasts": v["n"]} for k, v in cov.items()]

    always_share = round(len(always) * weeks / slots, 3) if slots else None
    findings = []
    findings.append(
        f"{len(units)} of about {pool:,} {unit_type}s were ever in the top 5% over {weeks} weeks, and {len(always)} of the "
        f"{per_week} flagged each week were the same ones every week ({100 * always_share:.0f}% of all flags). "
        "The forecast keeps pointing at the same places. That is what a stable pattern looks like, and it is also what a "
        "feedback loop looks like; this record cannot tell them apart.")
    city = next(g for g in by_group if g["group"].startswith("City"))
    if city["share_of_flags"] is not None:
        findings.append(
            f"{100 * city['share_of_flags']:.0f}% of flags fell in city commissionerates ({city['flagged_units']} of the "
            f"{len(units)} flagged {unit_type}s), which hold {100 * city['share_of_cases_among_flagged']:.0f}% of those units' "
            f"registered cases. A top-5% list by count will always favour the busiest {unit_type}s; a rural {unit_type} "
            "with a sharp rise from a low level does not reach it.")
    worst = max((g for g in by_group if g["forecast_over_recorded"]), key=lambda g: abs(g["forecast_over_recorded"] - 1), default=None)
    if worst:
        off = worst["forecast_over_recorded"] - 1
        findings.append(
            f"Among flagged units the engine's level is within {abs(100 * off):.0f}% of what was recorded for "
            f"{worst['group'].lower()} ({worst['forecast_over_recorded']:.2f} forecast for every 1 recorded), the group it is furthest off for."
            if abs(off) < 0.10 else
            f"The engine {'over' if off > 0 else 'under'}-forecasts flagged {worst['group'].lower()}: "
            f"{worst['forecast_over_recorded']:.2f} forecast for every 1 recorded, on {worst['flagged_units']} flagged {unit_type}s.")
    if ranges:
        lo, hi = min(r["held"] for r in ranges), max(r["held"] for r in ranges)
        findings.append(f"The likely range held between {100 * lo:.0f}% and {100 * hi:.0f}% of the time across quiet and busy "
                        f"{unit_type}s (it should be near 80% for all of them).")

    return {
        "unit_type": unit_type, "weeks": weeks, "flagged_per_week": per_week, "units_in_pool": pool,
        "window": f"{bt['window']['first_target_week']} to {bt['window']['last_target_week']}",
        "persistence": {"ever_flagged": len(units), "flagged_every_week": len(always),
                        "share_of_flags_from_always_flagged": always_share,
                        "share_of_units_ever_flagged": round(len(units) / pool, 3) if pool else None},
        "by_group": by_group, "ranges_by_volume": ranges, "findings": findings,
        "not_measured": [
            "Forecast error for units that were never flagged: the stored back-test keeps per-unit totals for flagged units only.",
            "Whether policing a place changes how much is registered there. That needs deployment records this system does not hold.",
            "Any comparison by community. The register used here carries no such field, and the engine uses none.",
        ],
        "what_to_do": [
            "Read a flag as 'the record is densest here', not 'crime is highest here'.",
            "Rotate attention: the units just below the cut are forecast almost as high and are flagged far less often.",
            "When a deployment follows a forecast, record it, so the effect on registration can be measured.",
        ],
        "evidence_class": "D",
    }


def report(conn: sqlite3.Connection) -> str:
    from datetime import date
    lines = ["# Forecast: fairness and feedback", "",
             f"Generated by `python -m app.forecast.fairness` on {date.today().isoformat()} from the stored back-test. "
             "Do not edit by hand; rerun the script.", ""]
    for ut in ("station", "beat"):
        f = measure(conn, ut)
        if not f:
            lines += [f"## {ut.capitalize()}s", "", "No back-test is stored for this unit type.", ""]
            continue
        p = f["persistence"]
        lines += [f"## {ut.capitalize()}s", "",
                  f"Top 5% by forecast, all crime, next 7 days; {f['weeks']} weeks, {f['window']}; {f['flagged_per_week']:,} flagged a week out of about {f['units_in_pool']:,}.", "",
                  *[f"- {x}" for x in f["findings"]], "",
                  "| Persistence | |", "|---|---:|",
                  f"| Distinct units ever flagged | {p['ever_flagged']:,} |",
                  f"| Flagged in every week | {p['flagged_every_week']:,} |",
                  f"| Share of all flags taken by those | {100 * p['share_of_flags_from_always_flagged']:.0f}% |",
                  f"| Share of units ever flagged | {100 * p['share_of_units_ever_flagged']:.1f}% |", "",
                  "| Group | Flagged units | Share of flags | Share of cases (flagged units) | Forecast per 1 recorded |", "|---|---:|---:|---:|---:|",
                  *[f"| {g['group']} | {g['flagged_units']:,} | {100 * g['share_of_flags']:.0f}% | {100 * g['share_of_cases_among_flagged']:.0f}% | {g['forecast_over_recorded']} |"
                    for g in f["by_group"]], "",
                  "| Usual weekly cases | Likely range held | Forecasts |", "|---|---:|---:|",
                  *[f"| {r['usual_weekly_cases']} | {100 * r['held']:.1f}% | {r['forecasts']:,} |" for r in f["ranges_by_volume"]], ""]
    f = measure(conn, "station") or {}
    lines += ["## Not measured", "", *[f"- {x}" for x in f.get("not_measured", [])], "",
              "## How to use a flag", "", *[f"- {x}" for x in f.get("what_to_do", [])], ""]
    return "\n".join(lines)


if __name__ == "__main__":
    import pathlib
    from app.core.db_path import DB_PATH
    conn = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    out = pathlib.Path(__file__).resolve().parents[2] / "docs" / "FORECAST_FAIRNESS.md"
    out.write_text(report(conn), encoding="utf-8")
    print("wrote", out)
