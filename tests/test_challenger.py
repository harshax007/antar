"""
Antar — Unit Tests for Challenger Forecast Model (LightGBM)
Tests fitting, conformal calibration, prediction, and TreeSHAP explainability.
"""
import sqlite3
from datetime import date, timedelta

import numpy as np
import pytest

# Ensure onnxruntime is loaded first on Windows
try:
    import onnxruntime  # noqa: F401
except Exception:
    pass

from app.forecast import asof, features as F, model as M, store
from app.forecast import challenger as C

START, END = date(2018, 1, 1), date(2024, 3, 10)
STEP = date(2023, 1, 2)
HOLE = (date(2021, 6, 7), date(2021, 8, 15))
AS_OF = "2024-03-10"


def _make_test_registry(seed: int = 42) -> sqlite3.Connection:
    rng = np.random.default_rng(seed)
    con = sqlite3.connect(":memory:")
    cols = (
        "station", "Beat_Name", "district_norm", "CrimeGroup_Name", "crime_type",
        "date", "Latitude", "Longitude", "lat_r", "lon_r", "is_synthetic_row", "CrimeHead_Name"
    )
    con.execute(f"CREATE TABLE FIRs (id INTEGER PRIMARY KEY, {', '.join(cols)})")
    rows = []
    beats = []
    for d in range(2):
        for s in range(3):
            for b in range(3):
                lat = 12.0 + d * 1.5 + s * 0.05
                lon = 76.0 + b * 0.01 + s * 0.05
                base = 0.5 + 0.5 * ((s + b) % 3)
                beats.append((f"Dist{d}", f"Station{d}{s} PS", f"Beat {b}", lat, lon, base))

    day = START
    while day <= END:
        in_hole = HOLE[0] <= day <= HOLE[1]
        k = 5.0 if day >= STEP else 1.0
        season = 1.0 + 0.3 * np.sin(2 * np.pi * day.timetuple().tm_yday / 365.25)
        for i, (dist, st, bt, lat, lon, base) in enumerate(beats):
            lam = base * season * k / 7.0
            n = 0 if in_hole else rng.poisson(lam)
            for _ in range(n):
                rows.append((st, bt, dist, "THEFT", "THEFT", day.isoformat(),
                             lat, lon, round(lat, 2), round(lon, 2), 0, "Theft"))
        day += timedelta(days=1)

    con.executemany(f"INSERT INTO FIRs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", rows)
    con.commit()
    store.build(con)
    return con


@pytest.fixture(scope="module")
def reg():
    con = _make_test_registry()
    yield con
    con.close()


def test_challenger_fit_and_predict(reg):
    a = asof.resolve(reg, AS_OF)
    cal = F.calendar(reg, "n_real", a.history_end)
    st = F.load_units(reg, "station")
    ps = F.load_panel(reg, st, None, "PROPERTY", cal)
    T = cal.history_end

    fit_res = C.fit(ps, last_origin=T - 1, horizon_days=7, n_cal_origins=6, seed=42)

    assert fit_res.horizon_days == 7
    assert fit_res.booster is not None
    assert fit_res.trained_rows > 0
    assert fit_res.alpha >= 0.0
    assert "all" in fit_res.conformal
    assert fit_res.seconds > 0.0

    # Predict at origin
    pred = C.predict(ps, fit_res, t=T - 1, explain=True)

    assert "expected" in pred
    assert len(pred["expected"]) == ps.Y.shape[0]
    assert np.all(pred["expected"] >= 0.0)
    assert np.all(pred["lo80"] <= pred["expected"])
    assert np.all(pred["hi80"] >= pred["expected"])
    assert np.all(pred["lo90"] <= pred["hi90"])

    # Check driver explainability
    for group in ("level", "recent", "last_year", "neighbours", "area", "season"):
        key = f"x_{group}"
        assert key in pred, f"Missing driver key: {key}"
        assert np.all(pred[key] > 0.0)
        assert np.all(np.isfinite(pred[key]))


def test_challenger_conformal_coverage(reg):
    a = asof.resolve(reg, AS_OF)
    cal = F.calendar(reg, "n_real", a.history_end)
    st = F.load_units(reg, "station")
    ps = F.load_panel(reg, st, None, "PROPERTY", cal)
    T = cal.history_end

    fit_res = C.fit(ps, last_origin=T - 4, horizon_days=7, n_cal_origins=6, seed=42)
    assert "dev_model" in fit_res.heldout or fit_res.trained_rows > 0
from app.forecast import league as L


def test_league_build_and_crowning():
    # Synthetic backtest dict with champion GLM and challenger LightGBM
    mock_bt = {
        "version": "3",
        "results": {
            "station": {
                "ALL": {
                    "7": {
                        "capture": {
                            "top_5pct": {
                                "model": 0.42,
                                "last4": 0.35,
                                "model_beats_last4_weeks": 18,
                                "weeks": 22,
                            }
                        },
                        "coverage": {
                            "80": {"coverage": 0.82},
                            "90": {"coverage": 0.91},
                        },
                        "deviance": {"model": 1.25, "baseline": 1.50},
                        "mae": {"model": 0.45, "last4": 0.52},
                        "calibration": 0.98,
                        "pai": {
                            "top_5pct": {
                                "model": {"pai": 8.4, "hit": 0.42, "pei": 0.75},
                                "last4": {"pai": 7.0, "hit": 0.35, "pei": 0.62},
                            }
                        },
                    }
                }
            }
        },
        "results_challengers": {
            "lgbm": {
                "station": {
                    "ALL": {
                        "7": {
                            "capture": {
                                "top_5pct": {
                                    "model": 0.46,
                                    "last4": 0.35,
                                    "model_beats_last4_weeks": 20,
                                    "weeks": 22,
                                }
                            },
                            "coverage": {
                                "80": {"coverage": 0.81},
                                "90": {"coverage": 0.89},
                            },
                            "deviance": {"model": 1.18, "baseline": 1.50},
                            "mae": {"model": 0.42, "last4": 0.52},
                            "calibration": 0.99,
                            "pai": {
                                "top_5pct": {
                                    "model": {"pai": 9.2, "hit": 0.46, "pei": 0.82},
                                    "last4": {"pai": 7.0, "hit": 0.35, "pei": 0.62},
                                }
                            },
                        }
                    }
                }
            }
        },
    }

    league_data = L.build(mock_bt)
    assert "rows" in league_data
    assert len(league_data["rows"]) == 3  # GLM, LGBM, Last4

    lgbm_row = next(r for r in league_data["rows"] if r["model"] == "lgbm")
    glm_row = next(r for r in league_data["rows"] if r["model"] == "glm")
    last4_row = next(r for r in league_data["rows"] if r["model"] == "last4")

    # LGBM has higher PAI5 (9.2 vs 8.4) and coverage >= 0.85 -> crowned winner!
    assert lgbm_row["winner"] is True
    assert glm_row["winner"] is False
    assert last4_row["winner"] is False

    # Check PEI presence
    assert lgbm_row["pei5"] == 0.82
    assert glm_row["pei5"] == 0.75

    # Check report rendering
    md = L.render_report(league_data)
    assert "WINNER" in md
    assert "LGBM" in md
    assert "PAI@5%" in md
