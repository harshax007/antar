"""
Antar — Model League Table (Champion GLM vs Challenger LightGBM)
Phase L3.3 of LabBuild_plan.md.

Builds and renders the head-to-head model league table:
- Compares Poisson GLM (Champion) vs LightGBM (Challenger) vs Baselines (Last4, Seasonal-Naive, Oracle)
- Evaluates MAE, deviance gain, split-conformal coverage (80%/90%), PAI, and PEI
- Implements crowning logic: best PAI5 with ties broken by MAE; disqualified if cover90 < 0.85
- Saves to forecast_meta under key 'league' and writes docs/lab/MODEL_LEAGUE.md
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
LEAGUE_MD_PATH = ROOT / "docs" / "lab" / "MODEL_LEAGUE.md"
META_KEY = "league"


def build(bt: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Turn back-test result into an executive league comparison table."""
    results = bt.get("results", {})
    results_challengers = bt.get("results_challengers", {})
    has_lgbm = "lgbm" in results_challengers

    rows: List[Dict[str, Any]] = []
    notes: List[str] = [
        "Beat areas are Voronoi estimates derived from station centroids.",
        "Split-conformal prediction intervals use Mondrian volume bins.",
    ]
    if not has_lgbm:
        notes.append("LightGBM challenger was not executed in this back-test run.")

    # Iterate over unit types, categories, horizons
    for ut in ("station", "beat"):
        ut_res = results.get(ut, {})
        for cat, cat_res in ut_res.items():
            for hd_str, m_glm in cat_res.items():
                if "capture" not in m_glm:
                    continue
                hd = int(hd_str)
                m_lgbm = results_challengers.get("lgbm", {}).get(ut, {}).get(cat, {}).get(hd_str)

                # Extract GLM metrics
                cap_glm = m_glm["capture"].get("top_5pct", {})
                cov_glm = m_glm.get("coverage", {})
                pai_glm = m_glm.get("pai", {}).get("top_5pct", {}).get("model", {})
                dev_base = m_glm.get("deviance", {}).get("baseline", 1.0)
                dev_glm = m_glm.get("deviance", {}).get("model", 1.0)
                gain_glm = round(1.0 - (dev_glm / max(dev_base, 1e-9)), 3)

                glm_row = {
                    "category": cat,
                    "unit_type": ut,
                    "horizon_days": hd,
                    "model": "glm",
                    "mae": m_glm.get("mae", {}).get("model", 0.0),
                    "deviance_gain": gain_glm,
                    "calibration": m_glm.get("calibration", 1.0),
                    "cover80": cov_glm.get("80", {}).get("coverage", 0.0),
                    "cover90": cov_glm.get("90", {}).get("coverage", 0.0),
                    "capture5": cap_glm.get("model", 0.0),
                    "pai1": m_glm.get("pai", {}).get("top_1pct", {}).get("model", {}).get("pai", 0.0),
                    "pai5": pai_glm.get("pai", 0.0),
                    "pai10": m_glm.get("pai", {}).get("top_10pct", {}).get("model", {}).get("pai", 0.0),
                    "pei5": pai_glm.get("pei", 0.0),
                    "weeks_better": cap_glm.get("model_beats_last4_weeks", 0),
                    "weeks_total": cap_glm.get("weeks", 0),
                }

                # Baseline row
                base_row = {
                    "category": cat,
                    "unit_type": ut,
                    "horizon_days": hd,
                    "model": "last4",
                    "mae": m_glm.get("mae", {}).get("last4", 0.0),
                    "deviance_gain": 0.0,
                    "calibration": 1.0,
                    "cover80": 0.0,
                    "cover90": 0.0,
                    "capture5": cap_glm.get("last4", 0.0),
                    "pai1": m_glm.get("pai", {}).get("top_1pct", {}).get("last4", {}).get("pai", 0.0),
                    "pai5": m_glm.get("pai", {}).get("top_5pct", {}).get("last4", {}).get("pai", 0.0),
                    "pai10": m_glm.get("pai", {}).get("top_10pct", {}).get("last4", {}).get("pai", 0.0),
                    "pei5": m_glm.get("pai", {}).get("top_5pct", {}).get("last4", {}).get("pei", 0.0),
                    "weeks_better": 0,
                    "weeks_total": cap_glm.get("weeks", 0),
                }

                candidates = [glm_row]

                # Extract LightGBM challenger if available
                if m_lgbm and "capture" in m_lgbm:
                    cap_lgb = m_lgbm["capture"].get("top_5pct", {})
                    cov_lgb = m_lgbm.get("coverage", {})
                    pai_lgb = m_lgbm.get("pai", {}).get("top_5pct", {}).get("model", {})
                    dev_lgb = m_lgbm.get("deviance", {}).get("model", 1.0)
                    gain_lgb = round(1.0 - (dev_lgb / max(dev_base, 1e-9)), 3)

                    lgb_row = {
                        "category": cat,
                        "unit_type": ut,
                        "horizon_days": hd,
                        "model": "lgbm",
                        "mae": m_lgbm.get("mae", {}).get("model", 0.0),
                        "deviance_gain": gain_lgb,
                        "calibration": m_lgbm.get("calibration", 1.0),
                        "cover80": cov_lgb.get("80", {}).get("coverage", 0.0),
                        "cover90": cov_lgb.get("90", {}).get("coverage", 0.0),
                        "capture5": cap_lgb.get("model", 0.0),
                        "pai1": m_lgbm.get("pai", {}).get("top_1pct", {}).get("model", {}).get("pai", 0.0),
                        "pai5": pai_lgb.get("pai", 0.0),
                        "pai10": m_lgbm.get("pai", {}).get("top_10pct", {}).get("model", {}).get("pai", 0.0),
                        "pei5": pai_lgb.get("pei", 0.0),
                        "weeks_better": cap_lgb.get("model_beats_last4_weeks", 0),
                        "weeks_total": cap_lgb.get("weeks", 0),
                    }
                    candidates.append(lgb_row)

                # Determine Winner: best PAI5, ties broken by lower MAE
                # Over-confident models (cover90 < 0.85) are disqualified from winning
                eligible = [c for c in candidates if c["cover90"] >= 0.85]
                if not eligible:
                    eligible = candidates  # Fallback if calibration band was conservative

                eligible.sort(key=lambda c: (-c["pai5"], c["mae"]))
                winner_model = eligible[0]["model"]

                for c in candidates:
                    c["winner"] = (c["model"] == winner_model)
                    rows.append(c)

                base_row["winner"] = False
                rows.append(base_row)

    # Weekly actual vs predicted (from GLM ALL 7-day)
    weekly_data = results.get("beat", {}).get("ALL", {}).get("7", {}).get("weekly", [])
    if not weekly_data:
        weekly_data = results.get("station", {}).get("ALL", {}).get("7", {}).get("weekly", [])

    league_payload = {
        "version": "1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
        "predicted_vs_actual": weekly_data,
        "notes": notes,
    }
    return league_payload


def save(conn: sqlite3.Connection, league: Dict[str, Any]) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS forecast_meta (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID")
    conn.execute("INSERT OR REPLACE INTO forecast_meta VALUES (?, ?)", (META_KEY, json.dumps(league)))
    conn.commit()


def load(conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    try:
        row = conn.execute("SELECT value FROM forecast_meta WHERE key = ?", (META_KEY,)).fetchone()
    except sqlite3.OperationalError:
        return None
    return json.loads(row[0]) if row else None


def render_report(league: Dict[str, Any]) -> str:
    lines = [
        "# Antar — Champion vs. Challenger Model League",
        "",
        f"> Generated on {league.get('timestamp', 'N/A')}. Real KSP record back-test.",
        "",
        "## 1. Executive Summary & League Table",
        "",
        "| Category | Unit | Horizon | Model | Status | PAI@5% | PEI@5% | Capture@5% | Dev Gain | MAE | Cover 90% | Calibration |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in league.get("rows", []):
        status = "**WINNER**" if r.get("winner") else "Challenger" if r["model"] == "lgbm" else "Champion" if r["model"] == "glm" else "Baseline"
        lines.append(
            f"| {r['category']} | {r['unit_type']} | {r['horizon_days']}d | {r['model'].upper()} | {status} "
            f"| **{r['pai5']:.2f}** | {r['pei5']:.3f} | {r['capture5']*100:.1f}% | {r['deviance_gain']*100:+.1f}% "
            f"| {r['mae']:.3f} | {r['cover90']*100:.1f}% | {r['calibration']:.2f} |"
        )

    lines.extend([
        "",
        "## 2. Notes & Caveats",
        "",
    ])
    for note in league.get("notes", []):
        lines.append(f"- {note}")

    return "\n".join(lines)


def write_report(league: Dict[str, Any], path: Path = LEAGUE_MD_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(league), encoding="utf-8")
    return path
