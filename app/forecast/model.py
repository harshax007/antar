"""The forecast model — Phase 2 of docs/MAP_FORECASTING_PLAN.md.

Defensible over clever. For each unit type × crime category × horizon:

  Baselines   seasonal-naive (the same weeks last year), EWMA (half-life 4 weeks) and
              their average — "the baseline", the bar the model has to clear
  Model       Poisson GLM, log link, with an offset: mu = base * exp(b0 + x.b). `base` is
              the unit's EWMA shrunk toward its share of the parent area, so the model
              only has to learn *adjustments* - recent weeks vs base, last year vs usual,
              neighbours and area vs theirs, season (features.py). Fitted as a rate
              (y / base, weighted by base), which is exactly a Poisson offset.
              Over-dispersion is estimated from residuals (NB2, method of moments) and
              drives the per-unit spread.
  Bands       split-conformal on held-out origins the model never saw. Scores are
              Pearson-normalised residuals |y − μ| / √(μ + αμ²), so a band widens with a
              unit's own volatility, and they are calibrated separately per volume bin
              (Mondrian), so sparse beats and busy stations each get honest coverage.
  Coherence   beat forecasts are reconciled top-down to their station's: a station's
              beats are scaled to sum to the station forecast × the share of its FIRs
              that name a beat. The station model sees every FIR in the station, so it is
              the better-estimated level; the beat model decides how it splits. Applied
              before calibration, so the bands are calibrated on what is shown.
  Level       a station model's forecasts are rescaled by Σ actual ÷ Σ forecast on its
              held-out block (shrunk toward 1 by LEVEL_PRIOR events, capped to ×0.5–2).
              The statewide recording-level fix is right for the total but not for every
              category — the 2023 sampling step was not uniform, and narcotics came out
              ~1.6–2.2× high in the first back-test. Beats inherit it through
              reconciliation. The block precedes the origin, so nothing leaks.
  Guard       every input is clamped to the range it took in training (0.5–99.5th
              percentile), so an unusual unit is never an extrapolation of a log-linear
              curve — the failure that let a seeded beat out-forecast its own station.
  Drivers     the forecast is built up from the unit's usual week one reason at a time
              (recent weeks → last year → neighbours → wider area → season); each step's
              change is that reason's multiplier, and their product is exactly the
              forecast. That is the "why".

No statsmodels, no deep learning: scikit-learn's PoissonRegressor plus numpy/scipy.
"""
from __future__ import annotations

import math
import time
import warnings
from dataclasses import dataclass, field

import numpy as np

from app.forecast.features import (DRIVER_STEPS, FEATURES, Panel, design, exposure,
                                   features, usual_state)

HORIZONS = {7: 1, 28: 4}                 # horizon in days → weeks
LEVELS = (0.8, 0.9)
BIN_EDGES = (0.5, 2.0, 8.0)              # Mondrian bins on the expected count
MIN_BIN = 40                             # smaller bins borrow the pooled quantile
MIN_TRAIN_EVENTS = 300                   # below this a category falls back to the baseline
LEVEL_PRIOR = 20.0                       # events of shrinkage toward "no level correction"
LEVEL_RANGE = (0.5, 2.0)


@dataclass
class Fit:
    unit_type: str
    category: str
    horizon_days: int
    method: str                          # glm | baseline
    intercept: float = 0.0
    coef: dict[str, float] = field(default_factory=dict)
    clip: dict[str, tuple[float, float]] = field(default_factory=dict)  # training range
    alpha: float = 0.0                   # NB2 dispersion
    level_adj: float = 1.0               # held-out level correction (stations only)
    conformal: dict[str, dict[str, float]] = field(default_factory=dict)   # bin → {q80,q90}
    n_train: int = 0
    n_cal: int = 0
    train_origins: tuple[str, str] | None = None
    cal_origins: tuple[str, str] | None = None
    heldout: dict[str, float] = field(default_factory=dict)
    seconds: float = 0.0
    note: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


# ── baselines ────────────────────────────────────────────────────────────────

def baselines(p: Panel, t: int, h: int, f: dict | None = None) -> dict[str, np.ndarray]:
    f = f or features(p, t, h)
    seasonal = f["last_year"] * h
    ew = f["ewma"] * h
    return {"seasonal_naive": seasonal, "ewma": ew, "last4": f["last4"] * h,
            "baseline": 0.5 * (seasonal + ew)}


# ── fitting ──────────────────────────────────────────────────────────────────

def _valid_origins(p: Panel, h: int, last: int) -> list[int]:
    first = p.week_index(p.weeks[0]) + 52           # a full year of history first
    return [t for t in range(first, last + 1) if p.origin_ok(t, h)]


def _rows(p: Panel, origins: list[int], h: int, rng, cap: int | None):
    """Stacked (X, y, exposure, baselines) over origins, for units with any signal."""
    Xs, ys, es, bs = [], [], [], []
    for t in origins:
        f = features(p, t, h)
        idx = np.flatnonzero((f["usual"] > 0) | (f["nbr4"] > 0) | (f["area"] > 0))
        if not len(idx):
            continue
        Xs.append(design(f)[idx]); ys.append(p.target(t, h)[idx])
        es.append(exposure(f, h)[idx])
        bs.append({k: v[idx] for k, v in baselines(p, t, h, f).items()})
    if not Xs:
        return None
    X, y, e = np.vstack(Xs), np.concatenate(ys), np.concatenate(es)
    base = {k: np.concatenate([b[k] for b in bs]) for k in bs[0]}
    if cap and len(y) > cap:
        sel = rng.choice(len(y), cap, replace=False)
        X, y, e = X[sel], y[sel], e[sel]
        base = {k: v[sel] for k, v in base.items()}
    return X, y, e, base


def _dispersion(y: np.ndarray, mu: np.ndarray) -> float:
    """NB2 α by method of moments: E[(y − μ)² − y] = α μ²."""
    den = float(np.sum(mu ** 2))
    if den <= 0:
        return 0.0
    return float(np.clip(np.sum((y - mu) ** 2 - y) / den, 0.0, 5.0))


def _sd(mu: np.ndarray, alpha: float) -> np.ndarray:
    return np.sqrt(mu + alpha * mu ** 2 + 1e-9)


def _bin(mu: np.ndarray) -> np.ndarray:
    return np.searchsorted(np.array(BIN_EDGES), mu, side="right")


def _conformal_q(scores: np.ndarray, level: float) -> float:
    n = len(scores)
    if n == 0:
        return float("inf")
    k = min(n, math.ceil((n + 1) * level))
    return float(np.sort(scores)[k - 1])


def _calibrate(y, mu, alpha) -> dict[str, dict[str, float]]:
    s = np.abs(y - mu) / _sd(mu, alpha)
    b = _bin(mu)
    out = {"all": {f"q{int(l * 100)}": _conformal_q(s, l) for l in LEVELS}}
    for i in range(len(BIN_EDGES) + 1):
        m = b == i
        if m.sum() >= MIN_BIN:
            out[str(i)] = {f"q{int(l * 100)}": _conformal_q(s[m], l) for l in LEVELS}
    return out


def bands(mu: np.ndarray, alpha: float, conformal: dict, level: float) -> tuple[np.ndarray, np.ndarray]:
    """Integer [lo, hi] with lo ≤ μ ≤ hi. The conformal interval is continuous; an integer
    outcome lies inside it exactly when it lies in [ceil(lo), floor(hi)], so rounding
    inward keeps the calibrated coverage. Widening to contain μ can only add coverage."""
    key = f"q{int(level * 100)}"
    q = np.array([conformal.get(str(b), conformal["all"])[key] for b in _bin(mu)])
    sd = _sd(mu, alpha)
    lo = np.minimum(np.ceil(np.maximum(mu - q * sd, 0.0) - 1e-9), np.floor(mu))
    hi = np.maximum(np.floor(mu + q * sd + 1e-9), np.ceil(mu))
    return lo, hi


def p_any(mu: np.ndarray, alpha: float) -> np.ndarray:
    """P(at least one FIR) under NB2 — the useful number for a quiet beat."""
    if alpha < 1e-6:
        return 1 - np.exp(-mu)
    return 1 - (1 + alpha * mu) ** (-1 / alpha)


@dataclass
class Parent:
    """The station level a beat forecast is reconciled to."""
    panel: Panel
    fit: Fit


def _full_mu(p: Panel, f: Fit, t: int, h: int):
    feat = features(p, t, h)
    base = baselines(p, t, h, feat)
    return _mu(f, design(feat), exposure(feat, h), base["baseline"]), feat, base


def reconcile(p: Panel, mu: np.ndarray, feat: dict, parent: Parent | None,
              t: int, h: int) -> np.ndarray:
    """Per-unit factor that makes beats sum to their station's forecast (see module doc).
    1.0 for stations, and for beats whose station has no forecast."""
    if parent is None:
        return np.ones_like(mu)
    pmu, pfeat, _ = _full_mu(parent.panel, parent.fit, t, h)
    names = p.units.parent_names
    pidx = np.array([parent.panel.units.index.get(n, -1) for n in names])
    grp = p.units.parent_of
    P = len(names)
    beat_sum = np.bincount(grp, weights=mu, minlength=P)
    beat_usual = np.bincount(grp, weights=feat["usual"], minlength=P)
    st_mu = np.where(pidx >= 0, pmu[np.maximum(pidx, 0)], np.nan)
    st_usual = np.where(pidx >= 0, pfeat["usual"][np.maximum(pidx, 0)], 0.0)
    share = np.where(st_usual > 0, np.clip(beat_usual / np.maximum(st_usual, 1e-12), 0, 1), 1.0)
    ok = (pidx >= 0) & (beat_sum > 1e-9)
    factor = np.where(ok, st_mu * share / np.where(ok, beat_sum, 1.0), 1.0)
    return factor[grp]


def fit(p: Panel, last_origin: int, horizon_days: int, *, parent: Parent | None = None,
        n_cal_origins: int = 8, max_train_origins: int = 60, max_rows: int = 150_000,
        seed: int = 0) -> Fit:
    """Train on origins before a held-out calibration block, calibrate on that block.

    `last_origin` is the latest origin whose target weeks are fully observed. `parent`
    (beats only) is the fitted station level to reconcile to.
    """
    from sklearn.linear_model import PoissonRegressor

    t0 = time.perf_counter()
    h = HORIZONS[horizon_days]
    rng = np.random.default_rng(seed)
    out = Fit(p.units.unit_type, p.category, horizon_days, "glm")
    origins = _valid_origins(p, h, last_origin)
    if len(origins) < n_cal_origins + 8:
        out.method, out.note = "baseline", f"only {len(origins)} usable weeks of history"
        cal = origins[-n_cal_origins:]
    else:
        cal = origins[-n_cal_origins:]
        # training targets must end before the first calibration origin — no leakage
        train = [t for t in origins if t + h <= cal[0]]
        if len(train) > max_train_origins:           # keep the most recent, thin the rest
            recent = train[-max_train_origins // 2:]
            older = train[:-max_train_origins // 2]
            step = max(1, len(older) // (max_train_origins - len(recent)))
            train = older[::step] + recent
        rows = _rows(p, train, h, rng, max_rows)
        # judged on FIRs as recorded: the level-adjusted counts can be a twentieth of them
        events = int(sum(p.Y_raw[:, t + 1: t + 1 + h].sum() for t in train))
        if rows is None or events < MIN_TRAIN_EVENTS:
            out.method = "baseline"
            out.note = f"too few FIRs to fit ({events} in the training weeks)"
        else:
            X, y, e, _ = rows
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m = PoissonRegressor(alpha=1e-4, solver="newton-cholesky", max_iter=200)
                    m.fit(X, y / e, sample_weight=e)          # = Poisson with a log(e) offset
                out.intercept = float(m.intercept_)
                out.coef = {k: float(c) for k, c in zip(FEATURES, m.coef_)}
                lo, hi = np.quantile(X, 0.005, axis=0), np.quantile(X, 0.995, axis=0)
                out.clip = {k: (float(a), float(b)) for k, a, b in zip(FEATURES, lo, hi)}
                out.alpha = _dispersion(y, _mu(out, X, e, None))
                out.n_train = int(len(y))
                out.train_origins = (p.weeks[train[0]].isoformat(), p.weeks[train[-1]].isoformat())
            except Exception as exc:                    # pragma: no cover — logged in the card
                out.method, out.note = "baseline", f"GLM did not converge: {exc}"

    cal_rows = _cal_rows(p, out, cal, h, parent) if cal else None
    if cal_rows is not None:
        yc, mu, basec = cal_rows
        if parent is None:
            adj = (yc.sum() + LEVEL_PRIOR) / (mu.sum() + LEVEL_PRIOR)
            out.level_adj = float(np.clip(adj, *LEVEL_RANGE))
            mu = mu * out.level_adj
        if out.method == "baseline":
            out.alpha = _dispersion(yc, mu)
        out.conformal = _calibrate(yc, mu, out.alpha)
        out.n_cal = int(len(yc))
        out.cal_origins = (p.weeks[cal[0]].isoformat(), p.weeks[cal[-1]].isoformat())
        out.heldout = {"mae_model": float(np.mean(np.abs(yc - mu))),
                       **{f"mae_{k}": float(np.mean(np.abs(yc - v))) for k, v in basec.items()},
                       "dev_model": poisson_deviance(yc, mu),
                       **{f"dev_{k}": poisson_deviance(yc, v) for k, v in basec.items()},
                       "events": float(yc.sum()), "rows": float(len(yc))}
    else:
        out.conformal = {"all": {"q80": 1.28, "q90": 1.65}}
        out.note = (out.note + "; " if out.note else "") + "no held-out weeks: normal-theory band"
    out.seconds = round(time.perf_counter() - t0, 2)
    return out


def _cal_rows(p: Panel, f: Fit, origins: list[int], h: int, parent: Parent | None):
    """Held-out (y, reconciled μ, baselines) for units with any signal."""
    ys, mus, bs = [], [], []
    for t in origins:
        mu, feat, base = _full_mu(p, f, t, h)
        mu = mu * reconcile(p, mu, feat, parent, t, h)
        idx = np.flatnonzero((feat["usual"] > 0) | (feat["nbr4"] > 0) | (feat["area"] > 0))
        if not len(idx):
            continue
        ys.append(p.target(t, h)[idx]); mus.append(mu[idx])
        bs.append({k: v[idx] for k, v in base.items()})
    if not ys:
        return None
    return (np.concatenate(ys), np.concatenate(mus),
            {k: np.concatenate([b[k] for b in bs]) for k in bs[0]})


def poisson_deviance(y: np.ndarray, mu: np.ndarray) -> float:
    """Mean Poisson deviance - the proper score for a count forecast. (MAE rewards
    predicting the median, which for a quiet beat is always zero.)"""
    mu = np.maximum(mu, 1e-3)
    t = np.where(y > 0, y * np.log(np.maximum(y, 1e-12) / mu), 0.0)
    return float(np.mean(2 * (t - (y - mu))))


def _mu(f: Fit, X: np.ndarray, e: np.ndarray, baseline: np.ndarray | None) -> np.ndarray:
    return _mu_raw(f, X, e, baseline) * f.level_adj


def _mu_raw(f: Fit, X: np.ndarray, e: np.ndarray, baseline: np.ndarray | None) -> np.ndarray:
    if f.method == "baseline":
        return np.maximum(baseline, 0.0)
    beta = np.array([f.coef[k] for k in FEATURES])
    if f.clip:
        X = np.clip(X, [f.clip[k][0] for k in FEATURES], [f.clip[k][1] for k in FEATURES])
    return e * np.exp(np.clip(f.intercept + X @ beta, -20, 12))


# ── prediction ───────────────────────────────────────────────────────────────

def predict(p: Panel, f: Fit, t: int, parent: Parent | None = None, *,
            explain: bool = True) -> dict[str, np.ndarray]:
    """Forecast for every unit from origin t (the last complete week of history).

    Besides the forecast and its bands, returns the driver multipliers:
        expected = usual × x_level × x_recent × x_last_year × x_neighbours × x_area × x_season
    where `usual` is the unit's own 52-week average over the horizon. A beat's
    reconciliation to its station is part of x_area — it *is* the wider area's forecast.
    """
    h = HORIZONS[f.horizon_days]
    mu, feat, base = _full_mu(p, f, t, h)
    rec = reconcile(p, mu, feat, parent, t, h)
    mu = mu * rec
    usual = feat["usual"] * h
    out: dict[str, np.ndarray] = {"expected": mu, "p_any": p_any(mu, f.alpha), **base,
                                  "usual_level": usual, "recent4": feat["last4"] * 4,
                                  "usual_week": feat["usual"],
                                  "last_year_h": feat["last_year"] * h}
    for level in LEVELS:
        lo, hi = bands(mu, f.alpha, f.conformal, level)
        out[f"lo{int(level * 100)}"], out[f"hi{int(level * 100)}"] = lo, hi

    if not explain:
        return out
    ones = np.ones_like(mu)
    if f.method != "glm":
        for g in ("level", *(g for g, _ in DRIVER_STEPS)):
            out[f"x_{g}"] = ones
        out["x_area"] = rec
        return out
    state = usual_state(feat)
    prev = _mu(f, design(state), exposure(state, h), None)
    has = usual > 0
    out["x_level"] = np.where(has, prev / np.where(has, usual, 1.0), 1.0)
    for g, keys in DRIVER_STEPS:
        state = {**state, **{k: feat[k] for k in keys}}
        cur = _mu(f, design(state), exposure(state, h), None)
        out[f"x_{g}"] = cur / np.maximum(prev, 1e-12)
        prev = cur
    out["x_area"] = out["x_area"] * rec
    return out
