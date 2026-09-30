"""Map forecasting, Phase 2 — the model, its bands and its reasons.

Runs on a synthetic registry whose truth is known by construction: 2 districts × 4
stations × 3 beats, weekly Poisson counts with a seasonal cycle, one beat on a rising
trend, a 5× recording step on 2023-01-02 (as in the real extract) and a 10-week hole.
Everything goes through the real pipeline: FIRs → forecast_cube → panels → model.
"""
import sqlite3
from datetime import date, timedelta

import numpy as np
import pytest

from app.forecast import asof, features as F, model as M, run, store

START, END = date(2018, 1, 1), date(2024, 3, 10)
STEP = date(2023, 1, 2)                        # recording level ×5 from here
HOLE = (date(2021, 6, 7), date(2021, 8, 15))   # nothing recorded (missing, not zero)
AS_OF = "2024-03-10"


def _registry(seed=7) -> sqlite3.Connection:
    rng = np.random.default_rng(seed)
    con = sqlite3.connect(":memory:")
    cols = ("station", "Beat_Name", "district_norm", "CrimeGroup_Name", "crime_type", "date",
            "Latitude", "Longitude", "lat_r", "lon_r", "is_synthetic_row", "CrimeHead_Name")
    con.execute(f"CREATE TABLE FIRs (id INTEGER PRIMARY KEY, {', '.join(cols)})")
    rows = []
    beats = []
    for d in range(2):
        for s in range(4):
            for b in range(3):
                lat, lon = 12.0 + d * 1.5 + s * 0.05, 76.0 + b * 0.01 + s * 0.05
                base = 0.4 + 0.6 * ((s + b) % 4)                   # 0.4 … 2.2 thefts a week
                beats.append((f"D{d}", f"S{d}{s} PS", f"Beat {b}", lat, lon, base))
    day = START
    while day <= END:
        in_hole = HOLE[0] <= day <= HOLE[1]
        k = 5.0 if day >= STEP else 1.0
        season = 1 + 0.3 * np.sin(2 * np.pi * day.timetuple().tm_yday / 365.25)
        for i, (dist, st, bt, lat, lon, base) in enumerate(beats):
            trend = 1 + (0.6 * (day - START).days / (END - START).days if i == 0 else 0)
            lam = base * season * trend * k / 7
            n = 0 if in_hole else rng.poisson(lam)
            for _ in range(n):
                rows.append((st, bt, dist, "THEFT", "THEFT", day.isoformat(),
                             lat, lon, round(lat, 2), round(lon, 2), 0,
                             "Theft of vehicle" if n > 1 else "House theft"))
            if not in_hole and rng.random() < 0.002 * k:           # a rare category
                rows.append((st, bt, dist, "MURDER", "MURDER", day.isoformat(),
                             lat, lon, round(lat, 2), round(lon, 2), 0, "Murder"))
        day += timedelta(days=1)
    con.executemany(f"INSERT INTO FIRs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", rows)
    con.commit()
    store.build(con)
    return con


@pytest.fixture(scope="module")
def reg():
    con = _registry()
    yield con
    con.close()


@pytest.fixture(scope="module")
def world(reg):
    a = asof.resolve(reg, AS_OF)
    cal = F.calendar(reg, "n_real", a.history_end)
    st, bt = F.load_units(reg, "station"), F.load_units(reg, "beat")
    ps = F.load_panel(reg, st, None, "PROPERTY", cal)
    pb = F.load_panel(reg, bt, st, "PROPERTY", cal)
    T = cal.history_end
    fits = {}
    for hd, h in M.HORIZONS.items():
        fs = M.fit(ps, T - h, hd)
        fb = M.fit(pb, T - h, hd, parent=M.Parent(ps, fs))
        fits[hd] = (fs, fb)
    return {"cal": cal, "ps": ps, "pb": pb, "T": T, "fits": fits}


# ── data handling ────────────────────────────────────────────────────────────

def test_a_hole_is_missing_data_not_zero(world):
    cal = world["cal"]
    hole = [i for i, w in enumerate(cal.weeks) if HOLE[0] <= w <= HOLE[1] - timedelta(days=6)]
    assert hole and not cal.covered[hole].any()
    assert cal.covered[: hole[0]].all()
    p = world["pb"]
    assert not any(p.origin_ok(t, 1) for t in range(hole[0] - 1, hole[-1] + 13))


def test_recording_step_is_normalised_away(world):
    """The 5× step in 2023 is how the registry was sampled, not a crime wave."""
    cal = world["cal"]
    i_before = cal.weeks.index(STEP) - 30
    i_after = cal.weeks.index(STEP) + 30
    assert cal.level[i_after] / cal.level[i_before] == pytest.approx(5, rel=0.15)
    # a year-ago feature straddling the step reads as ~1×, not ~5×
    p, T = world["ps"], world["T"]
    f = F.features(p, T, 1)
    ratio = f["last_year"].sum() / f["usual"].sum()
    assert 0.6 < ratio < 1.6
    # origins whose target crosses the step are never trained on
    s = cal.weeks.index(STEP)
    assert not p.origin_ok(s - 1, 1)


# ── the model ────────────────────────────────────────────────────────────────

def test_fit_is_deterministic(world):
    p, T = world["pb"], world["T"]
    parent = M.Parent(world["ps"], world["fits"][7][0])
    a = M.fit(p, T - 1, 7, parent=parent)
    b = M.fit(p, T - 1, 7, parent=parent)
    assert a.coef == b.coef and a.alpha == b.alpha and a.conformal == b.conformal


@pytest.mark.parametrize("hd", [7, 28])
def test_model_beats_the_baseline_on_held_out_weeks(world, hd):
    for f in world["fits"][hd]:
        assert f.method == "glm", f.note
        ho = f.heldout
        assert ho["dev_model"] < ho["dev_baseline"], (f.unit_type, ho)
        assert ho["dev_model"] < ho["dev_seasonal_naive"], (f.unit_type, ho)


def test_it_learns_a_rising_beat(world):
    """Beat 0 of S00 rises 60% over the record; the forecast follows it, not the average."""
    p, T = world["pb"], world["T"]
    fs, fb = world["fits"][28]
    pr = M.predict(p, fb, T, M.Parent(world["ps"], fs))
    i = p.units.index["S00 PS | BEAT 0"]
    assert pr["expected"][i] > pr["usual_level"][i]


@pytest.mark.parametrize("hd", [7, 28])
def test_bands_contain_the_forecast_and_nest(world, hd):
    p, T = world["pb"], world["T"]
    fs, fb = world["fits"][hd]
    pr = M.predict(p, fb, T, M.Parent(world["ps"], fs))
    mu = pr["expected"]
    assert (pr["lo90"] <= pr["lo80"]).all() and (pr["hi80"] <= pr["hi90"]).all()
    assert (pr["lo90"] <= mu).all() and (mu <= pr["hi90"]).all()
    assert (pr["lo80"] <= mu).all() and (mu <= pr["hi80"]).all()
    assert (pr["lo90"] >= 0).all()
    assert ((0 <= pr["p_any"]) & (pr["p_any"] <= 1)).all()


def test_bands_hold_their_coverage_on_unseen_weeks(reg, world):
    """Calibrate as of six months earlier, then score the 90% band on the 26 weeks after."""
    cal0 = world["cal"]
    t_as_of = cal0.weeks.index(date(2023, 9, 4))
    cal = F.calendar(reg, "n_real", cal0.weeks[t_as_of], through=cal0.weeks[-1])
    st, bt = F.load_units(reg, "station"), F.load_units(reg, "beat")
    ps = F.load_panel(reg, st, None, "PROPERTY", cal)
    f = M.fit(ps, t_as_of - 1, 7)
    hit = n = 0
    for t in range(t_as_of, t_as_of + 26):
        pr = M.predict(ps, f, t)
        y = ps.target(t, 1)                  # after the as-of week: as recorded
        hit += int(((pr["lo90"] <= y) & (y <= pr["hi90"])).sum())
        n += len(y)
    assert hit / n >= 0.8, hit / n


def test_reasons_multiply_to_the_forecast(world):
    p, T = world["pb"], world["T"]
    fs, fb = world["fits"][7]
    pr = M.predict(p, fb, T, M.Parent(world["ps"], fs))
    prod = pr["usual_level"].copy()
    for g in F.DRIVER_GROUPS:
        prod *= pr[f"x_{g}"]
    has = pr["usual_level"] > 0
    np.testing.assert_allclose(prod[has], pr["expected"][has], rtol=1e-6)


def test_beats_never_add_up_to_more_than_their_station(world):
    ps, pb, T = world["ps"], world["pb"], world["T"]
    for hd in (7, 28):
        fs, fb = world["fits"][hd]
        s = M.predict(ps, fs, T)["expected"]
        b = M.predict(pb, fb, T, M.Parent(ps, fs))["expected"]
        sums = np.bincount(pb.units.parent_of, weights=b, minlength=len(pb.units.parent_names))
        for name, total in zip(pb.units.parent_names, sums):
            assert total <= s[ps.units.index[name]] * (1 + 1e-6)


def test_inputs_are_clamped_to_the_training_range(world):
    fs = world["fits"][7][0]
    x = np.array([[1e6] * len(F.FEATURES)])
    mu = M._mu(fs, x, np.array([1.0]), None)
    x_hi = np.array([[fs.clip[k][1] for k in F.FEATURES]])
    assert mu[0] == pytest.approx(M._mu(fs, x_hi, np.array([1.0]), None)[0])


def test_a_rare_category_falls_back_to_the_baseline_and_says_so(reg, world):
    st = F.load_units(reg, "station")
    p = F.load_panel(reg, st, None, "MURDER", world["cal"])
    f = M.fit(p, world["T"] - 1, 7)
    assert f.method == "baseline" and "too few" in f.note


# ── persistence ──────────────────────────────────────────────────────────────

def test_compute_persists_forecasts_and_is_idempotent(reg):
    a = asof.resolve(reg, AS_OF)
    first = run.compute(reg, a, cats=["PROPERTY"])
    assert first["as_of_week"] == "2024-03-04" and first["series"] == "n_real"
    assert first["real_share"] == 1.0
    rows = reg.execute("SELECT unit_type, horizon, expected, lo90, hi90 FROM forecast_output "
                       "WHERE as_of_week = '2024-03-04' AND category = 'PROPERTY'").fetchall()
    assert {r[0] for r in rows} == {"station", "beat"} and {r[1] for r in rows} == {7, 28}
    assert all(lo <= e <= hi for _, _, e, lo, hi in rows)
    info = run.run_info(reg, "2024-03-04")
    assert info["model_version"] == run.MODEL_VERSION and info["models"] == 4
    # current → ensure returns the stored run instead of refitting
    again = run.ensure(reg, AS_OF)
    assert again["built_at"] == info["built_at"]


def test_wall_clock_forecasts_say_how_real_their_history_is(reg):
    a = asof.resolve(reg, "2024-03-10")
    assert run.series_for(a) == "n_real"
    later = asof.resolve(reg, "2026-09-18")
    assert run.series_for(later) == "n"
