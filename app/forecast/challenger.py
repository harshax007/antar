"""
Antar — Challenger Forecast Model (LightGBM Global Model)
Phase L3 of LabBuild_plan.md.

Implements LightGBM Poisson global model with log exposure offset,
Mondrian split-conformal prediction intervals, and exact TreeSHAP attributions.
Mirrors the interface of app.forecast.model for seamless drop-in scoring in backtest.py.
"""
from __future__ import annotations

import sys
# Ensure onnxruntime is loaded before lightgbm / scikit-learn on Windows to prevent OpenMP clash
try:
    import onnxruntime  # noqa: F401
except Exception:
    pass

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.forecast.features import (
    FEATURES,
    Panel,
    exposure,
    features,
)
from app.forecast import model

HORIZONS = {7: 1, 28: 4}
LEVELS = (0.8, 0.9)

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    lgb = None
    LIGHTGBM_AVAILABLE = False


class ChallengerUnavailable(RuntimeError):
    """Raised when lightgbm is not installed or available."""
    pass


FEATURE_NAMES = [
    "last1",
    "last4",
    "last13",
    "usual",
    "last_year",
    "nbr4",
    "nbr1",
    "nbr_usual",
    "area",
    "area_usual",
    "ewma",
    "sin_ang",
    "cos_ang",
    "sin2_ang",
    "cos2_ang",
    "log1p_usual",
    "parent_idx",
    "unit_type",
]

DRIVER_FEATURE_GROUPS = {
    "level": ["usual", "log1p_usual"],
    "recent": ["last1", "last4", "last13", "ewma"],
    "last_year": ["last_year"],
    "neighbours": ["nbr4", "nbr_usual"],
    "near_repeat": ["nbr1"],
    "area": ["area", "area_usual", "parent_idx"],
    "season": ["sin_ang", "cos_ang", "sin2_ang", "cos2_ang"],
}


@dataclass
class LgbFit:
    horizon_days: int
    booster: Any                         # lightgbm.Booster
    feature_names: List[str]
    alpha: float                         # NB2 dispersion from training residuals
    conformal: Dict[str, Dict[str, float]] # Mondrian conformal quantiles per bin
    trained_rows: int
    seconds: float
    unit_type: str = "station"
    category: str = "ALL"
    best_iteration: int = 0
    heldout: Dict[str, float] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__ if k != "booster"}
        d["method"] = "lgbm"
        return d


def _lgb_unit_rows(p: Panel, f: Dict[str, np.ndarray], h: int) -> np.ndarray:
    """Builds (U, n_features) matrix for panel at a single origin."""
    U = p.Y.shape[0]
    ang = f["ang"]
    sin_ang = np.sin(ang)
    cos_ang = np.cos(ang)
    sin2_ang = np.sin(2.0 * ang)
    cos2_ang = np.cos(2.0 * ang)
    log1p_usual = np.log1p(np.maximum(f["usual"], 0.0))
    parent_idx = p.units.parent_of.astype(np.float64)
    unit_type_val = 0.0 if getattr(p, "unit_type", "station") == "station" else 1.0
    u_type = np.full(U, unit_type_val, dtype=np.float64)

    cols = [
        f["last1"],
        f["last4"],
        f["last13"],
        f["usual"],
        f["last_year"],
        f["nbr4"],
        f["nbr1"],
        f["nbr_usual"],
        f["area"],
        f["area_usual"],
        f["ewma"],
        sin_ang,
        cos_ang,
        sin2_ang,
        cos2_ang,
        log1p_usual,
        parent_idx,
        u_type,
    ]
    return np.column_stack(cols)


def _lgb_rows(p: Panel, origins: List[int], h: int, rng: Optional[np.random.RandomState] = None, cap: Optional[int] = None):
    """Stacked (X, y, exposure, baselines) over origins for active units."""
    Xs, ys, es, bs = [], [], [], []
    for t in origins:
        f = features(p, t, h)
        idx = np.flatnonzero((f["usual"] > 0) | (f["nbr4"] > 0) | (f["area"] > 0))
        if len(idx) == 0:
            continue
        X_t = _lgb_unit_rows(p, f, h)
        Xs.append(X_t[idx])
        ys.append(p.target(t, h)[idx])
        es.append(exposure(f, h)[idx])
        bs.append({k: v[idx] for k, v in model.baselines(p, t, h, f).items()})

    if not Xs:
        return None

    X = np.vstack(Xs)
    y = np.concatenate(ys)
    e = np.concatenate(es)
    base = {k: np.concatenate([b[k] for b in bs]) for k in bs[0]}

    if cap and len(y) > cap:
        if rng is None:
            rng = np.random.RandomState(0)
        sel = rng.choice(len(y), cap, replace=False)
        X, y, e = X[sel], y[sel], e[sel]
        base = {k: v[sel] for k, v in base.items()}

    return X, y, e, base


def fit(
    p: Panel,
    last_origin: int,
    horizon_days: int,
    *,
    parent: Optional[model.Parent] = None,
    n_cal_origins: int = 8,
    max_train_origins: int = 60,
    max_rows: int = 400_000,
    seed: int = 0,
) -> LgbFit:
    """Fit LightGBM Poisson model over valid origins with log-exposure offset.

    Evaluates on held-out calibration origins for early stopping and split-conformal bands.
    """
    if not LIGHTGBM_AVAILABLE:
        raise ChallengerUnavailable("lightgbm is not installed. Run: pip install lightgbm")

    t0 = time.perf_counter()
    h = HORIZONS.get(horizon_days, 1)
    valid = model._valid_origins(p, h, last_origin)

    if not valid:
        raise ValueError(f"No valid origins for horizon={horizon_days}, last_origin={last_origin}")

    if len(valid) > n_cal_origins:
        train_origins = valid[:-n_cal_origins][-max_train_origins:]
        cal_origins = valid[-n_cal_origins:]
    else:
        train_origins = valid
        cal_origins = []

    rng = np.random.RandomState(seed)
    train_data = _lgb_rows(p, train_origins, h, rng=rng, cap=max_rows)
    if train_data is None:
        raise ValueError("Insufficient training rows with active signal.")

    X_train, y_train, e_train, base_train = train_data
    log_e_train = np.log(np.maximum(e_train, 1e-12))

    train_ds = lgb.Dataset(
        X_train,
        label=y_train,
        init_score=log_e_train,
        feature_name=FEATURE_NAMES,
        categorical_feature=["parent_idx"],
        free_raw_data=False,
    )

    valid_sets = [train_ds]
    valid_names = ["train"]

    X_cal, y_cal, e_cal, base_cal = None, None, None, None
    if cal_origins:
        cal_data = _lgb_rows(p, cal_origins, h, rng=rng, cap=100_000)
        if cal_data is not None:
            X_cal, y_cal, e_cal, base_cal = cal_data
            log_e_cal = np.log(np.maximum(e_cal, 1e-12))
            cal_ds = lgb.Dataset(
                X_cal,
                label=y_cal,
                init_score=log_e_cal,
                feature_name=FEATURE_NAMES,
                categorical_feature=["parent_idx"],
                reference=train_ds,
                free_raw_data=False,
            )
            valid_sets.append(cal_ds)
            valid_names.append("cal")

    params = {
        "objective": "poisson",
        "learning_rate": 0.05,
        "num_leaves": 63,
        "min_data_in_leaf": 200,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "lambda_l2": 1.0,
        "verbose": -1,
        "num_threads": 4,
        "seed": seed,
        "deterministic": True,
    }

    callbacks = []
    if len(valid_sets) > 1:
        callbacks.append(lgb.early_stopping(stopping_rounds=50, verbose=False))

    booster = lgb.train(
        params,
        train_ds,
        num_boost_round=600,
        valid_sets=valid_sets,
        valid_names=valid_names,
        callbacks=callbacks,
    )

    best_iter = booster.best_iteration or 600

    # Calibrate conformal bands and dispersion
    heldout = {}
    if X_cal is not None and len(y_cal) > 0:
        raw_cal = booster.predict(X_cal, raw_score=True)
        mu_cal = e_cal * np.exp(np.clip(raw_cal, -20.0, 12.0))
        alpha = model._dispersion(y_cal, mu_cal)
        conformal = model._calibrate(y_cal, mu_cal, alpha)
        heldout = {
            "mae_model": float(np.mean(np.abs(y_cal - mu_cal))),
            "dev_model": model.poisson_deviance(y_cal, mu_cal),
            "events": float(y_cal.sum()),
            "rows": float(len(y_cal)),
        }
    else:
        # Fallback calibration from training residuals
        raw_tr = booster.predict(X_train, raw_score=True)
        mu_tr = e_train * np.exp(np.clip(raw_tr, -20.0, 12.0))
        alpha = model._dispersion(y_train, mu_tr)
        conformal = model._calibrate(y_train, mu_tr, alpha)

    elapsed = round(time.perf_counter() - t0, 2)
    return LgbFit(
        horizon_days=horizon_days,
        booster=booster,
        feature_names=FEATURE_NAMES,
        alpha=alpha,
        conformal=conformal,
        trained_rows=len(y_train),
        seconds=elapsed,
        unit_type=getattr(p, "unit_type", "station"),
        category=getattr(p, "category", "ALL"),
        best_iteration=best_iter,
        heldout=heldout,
    )


def predict(
    p: Panel,
    f: LgbFit,
    t: int,
    parent: Optional[model.Parent] = None,
    *,
    explain: bool = False,
) -> Dict[str, np.ndarray]:
    """Forecast for every unit from origin t using fitted LightGBM challenger."""
    h = HORIZONS.get(f.horizon_days, 1)
    feat = features(p, t, h)
    base = model.baselines(p, t, h, feat)
    e = exposure(feat, h)

    X = _lgb_unit_rows(p, feat, h)
    raw_margin = f.booster.predict(X, raw_score=True)
    mu = e * np.exp(np.clip(raw_margin, -20.0, 12.0))

    # Reconcile beat forecasts to station parent if beat model
    rec = model.reconcile(p, mu, feat, parent, t, h)
    mu = mu * rec
    usual = feat["usual"] * h

    out: Dict[str, np.ndarray] = {
        "expected": mu,
        "p_any": model.p_any(mu, f.alpha),
        **base,
        "usual_level": usual,
        "recent4": feat["last4"] * 4,
        "usual_week": feat["usual"],
        "last_year_h": feat["last_year"] * h,
    }

    for level in LEVELS:
        lo, hi = model.bands(mu, f.alpha, f.conformal, level)
        out[f"lo{int(level * 100)}"] = lo
        out[f"hi{int(level * 100)}"] = hi

    if not explain:
        return out

    # Exact TreeSHAP feature contributions
    # booster.predict(X, pred_contrib=True) returns [U, n_features + 1] where last column is bias
    contrib = f.booster.predict(X, pred_contrib=True)
    f_contrib: Dict[str, np.ndarray] = {}
    for idx, name in enumerate(FEATURE_NAMES):
        f_contrib[name] = contrib[:, idx]

    # Map TreeSHAP log contributions into multiplicative driver groups
    for group, group_features in DRIVER_FEATURE_GROUPS.items():
        log_sum = np.zeros(p.Y.shape[0], dtype=np.float64)
        for gf in group_features:
            if gf in f_contrib:
                log_sum += f_contrib[gf]
        out[f"x_{group}"] = np.exp(np.clip(log_sum, -5.0, 5.0))

    out["x_area"] = out.get("x_area", np.ones_like(mu)) * rec
    return out
