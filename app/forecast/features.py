"""Panels and features for the forecast model — Phase 2 of docs/MAP_FORECASTING_PLAN.md.

A *panel* is one crime category's weekly counts for every unit of one type (station or
beat), as a dense [units × weeks] array read from forecast_cube. Everything the model
needs at an origin week t (the last complete week of history) is a window sum over it:

    last1     count in week t
    last4     mean weekly count over t-3 … t
    last13    mean weekly count over t-12 … t
    usual     mean weekly count over t-51 … t          (the unit's own level)
    last_year mean weekly count over the target weeks, one year earlier
    nbr4      neighbouring units' mean of last4 (the spatial lag)
    area      the parent's last13 × this unit's smoothed share of it
              (beat → station, station → district): shrinkage toward the parent, which
              is what keeps a sparse beat's forecast sane
    season    week-of-year Fourier terms of the target week
    base      26:4 blend of the EWMA (half-life 4 weeks) and `area` — the level the model
              multiplies (its Poisson offset); every other count enters as a log-ratio

Coverage. The registry has holes — the real record stops on 2024-03-10 and the seeded
band starts in 2025 — and a hole is *missing data*, not zero crime. A week is "covered"
when the statewide total is at least 30% of the median of its nearby non-empty weeks.
Windows average over covered weeks only, and the model never trains on an origin whose
recent history or target touches a hole.

Recording level. The registry's volume is not stationary for reasons that have nothing to
do with crime: the real extract was sampled unevenly by year (≈1.4k FIRs a week through
2022, ≈7k from January 2023 — a 5× step) and the seeded band runs at ≈350 a week. Left
alone, "the same week last year" would read as a fivefold surge. So every week is
re-expressed at the registry's recording level *as of the forecast*: counts are divided
by that week's level (the median statewide weekly total within ±26 covered weeks — a
median keeps a step sharp) and multiplied by the level at the as-of week. The level is
computed only from weeks up to the as-of date, so a back-test never sees its future.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree

from app.forecast.store import CUBE_FROM

ALL = "ALL"                                 # every category together
NEIGHBOURS = {"station": (6, 25.0), "beat": (6, 3.0)}    # k nearest within km

# ── Near-repeat / self-excitation (final_backend.md §6 P1-1) ──────────────────────────
# Crime is partly self-exciting: an offence raises the short-term risk NEARBY, which is
# the near-repeat effect Mohler et al. (JASA 2011) model with a triggering kernel. Their
# result — flagging 10% of a city, a point process caught 660 of 2,627 crimes against 547
# for a prospective hotspot map — is the best-evidenced gain in this literature.
#
# What this registry supports honestly: the forecast cube is WEEKLY, so a day-resolution
# kernel is not available without a second data path. The part of the effect the weekly
# panel does carry, and that no existing feature encodes, is SHORT-HORIZON SPATIAL
# spillover: `nbr` is the neighbours' four-week mean, which smooths exactly the spike a
# near-repeat is. `nbr1` is the neighbours' LAST week against their usual level.
#
# Off by default. Turn on with ANTAR_FORECAST_NEAR_REPEAT=1 and judge it on the rolling
# back-test (PAI, hit rate, interval coverage) — the plan's commitment is to prove it or
# record the null result, not to ship a plausible-sounding term.
NEAR_REPEAT = os.getenv("ANTAR_FORECAST_NEAR_REPEAT", "0") == "1"

_BASE_FEATURES = ("recent1", "recent4", "recent13", "usual", "last_year", "nbr", "area",
                  "scale", "s1", "c1", "s2", "c2")
FEATURES = _BASE_FEATURES + (("near_repeat",) if NEAR_REPEAT else ())
# The multipliers an officer is shown (see DRIVER_STEPS). "level" is how far the model's
# usual week sits from the unit's raw 52-week average — its pull toward the wider area.
DRIVER_GROUPS = (("level", "recent", "last_year", "neighbours")
                 + (("near_repeat",) if NEAR_REPEAT else ()) + ("area", "season"))


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


@dataclass
class Units:
    """Every unit of one type, its parent and its neighbours (fixed across categories)."""
    unit_type: str
    names: list[str]
    index: dict[str, int]
    parent_names: list[str]              # district for stations, station for beats
    parent_of: np.ndarray                # [U] index into parent_names
    lat: np.ndarray
    lon: np.ndarray
    W: sparse.csr_matrix                 # [U × U] row-normalised neighbour weights
    siblings: np.ndarray                 # [U] number of units sharing the parent


@dataclass
class Calendar:
    """The week axis for one series and as-of: which weeks are covered, and the
    registry's recording level in each (see module docstring)."""
    series: str
    weeks: list[date]
    history_end: int                     # index of the last week the model may see
    totals: np.ndarray                   # [W] statewide weekly FIRs
    covered: np.ndarray                  # [W] bool
    level: np.ndarray                    # [W] recording level, frozen after history_end

    @property
    def scale(self) -> np.ndarray:
        """Multiplier taking week w's counts to the as-of recording level."""
        return self.level[self.history_end] / self.level


@dataclass
class Panel:
    units: Units
    category: str
    cal: Calendar
    Y: np.ndarray                        # [U × W] weekly counts at the as-of recording level
    parent_Y: np.ndarray                 # [P × W] the parent level's, likewise
    Y_raw: np.ndarray                    # [U × W] as recorded (for scoring outcomes)
    parent_raw: np.ndarray | None = None # [P × W] as recorded
    _cum: dict = field(default_factory=dict, repr=False)

    @property
    def weeks(self) -> list[date]:
        return self.cal.weeks

    @property
    def covered(self) -> np.ndarray:
        return self.cal.covered

    def week_index(self, d: date) -> int:
        return (d - self.weeks[0]).days // 7

    # window means over covered weeks, via cumulative sums
    def _cums(self, which: str):
        if which not in self._cum:
            M = self.Y if which == "unit" else self.parent_Y
            cov = self.covered.astype(np.float64)
            C = np.zeros((M.shape[0], M.shape[1] + 1))
            np.cumsum(M * cov, axis=1, out=C[:, 1:])
            K = np.concatenate([[0.0], np.cumsum(cov)])
            self._cum[which] = (C, K)
        return self._cum[which]

    def window_mean(self, a: int, b: int, which: str = "unit") -> tuple[np.ndarray, float]:
        """Mean weekly count over weeks a..b inclusive (covered weeks only), and how many
        covered weeks that was."""
        C, K = self._cums(which)
        a, b = max(a, 0), min(b, len(self.weeks) - 1)
        if b < a:
            return np.zeros(C.shape[0]), 0.0
        k = K[b + 1] - K[a]
        return (C[:, b + 1] - C[:, a]) / max(k, 1.0), float(k)

    def target(self, t: int, h: int) -> np.ndarray:
        return self.Y[:, t + 1: t + 1 + h].sum(axis=1)

    def origin_ok(self, t: int, h: int, need_target: bool = True) -> bool:
        """Usable as a training/evaluation origin: 13 covered weeks of history and, if a
        target is needed, h covered target weeks with no step in the recording level."""
        if t - 12 < 0 or not self.covered[t - 12: t + 1].all():
            return False
        if need_target:
            if t + h >= len(self.weeks) or not self.covered[t + 1: t + 1 + h].all():
                return False
            lv = self.cal.level
            return bool(0.67 <= lv[t + h] / lv[t] <= 1.5)
        return True


def load_units(conn: sqlite3.Connection, unit_type: str) -> Units:
    rows = conn.execute(
        "SELECT unit, station, district, lat, lon FROM geo_units WHERE unit_type = ? ORDER BY unit",
        (unit_type,)).fetchall()
    names = [r[0] for r in rows]
    index = {n: i for i, n in enumerate(names)}
    parent_key = [r[2] if unit_type == "station" else r[1] for r in rows]
    parent_names = sorted({p or "" for p in parent_key})
    pidx = {p: i for i, p in enumerate(parent_names)}
    parent_of = np.array([pidx[p or ""] for p in parent_key], dtype=np.int64)
    lat = np.array([np.nan if r[3] is None else r[3] for r in rows])
    lon = np.array([np.nan if r[4] is None else r[4] for r in rows])
    siblings = np.bincount(parent_of, minlength=len(parent_names))[parent_of]
    W = _neighbour_matrix(unit_type, lat, lon, parent_of)
    return Units(unit_type, names, index, parent_names, parent_of, lat, lon, W, siblings)


def _neighbour_matrix(unit_type: str, lat, lon, parent_of) -> sparse.csr_matrix:
    """k nearest units within a radius; units with no point, or nobody in range, fall
    back to their siblings (same station / same district)."""
    k, radius_km = NEIGHBOURS[unit_type]
    U = len(lat)
    rows, cols = [], []
    has = ~np.isnan(lat)
    idx = np.flatnonzero(has)
    lonely = set(np.flatnonzero(~has).tolist())
    if len(idx) > 1:
        # equirectangular km — accurate to <1% across Karnataka's latitudes
        xy = np.column_stack([lat[idx] * 110.57, lon[idx] * 111.32 * np.cos(np.radians(lat[idx]))])
        tree = cKDTree(xy)
        dist, nn = tree.query(xy, k=min(k + 1, len(idx)), distance_upper_bound=radius_km)
        for a, (ds, ns) in enumerate(zip(dist, nn)):
            got = [idx[n] for d, n in zip(ds, ns) if np.isfinite(d) and n != a and n < len(idx)]
            if got:
                rows += [idx[a]] * len(got)
                cols += got
            else:
                lonely.add(int(idx[a]))
    if lonely:
        by_parent: dict[int, list[int]] = {}
        for u, p in enumerate(parent_of):
            by_parent.setdefault(int(p), []).append(u)
        for u in lonely:
            sib = [s for s in by_parent[int(parent_of[u])] if s != u][:20]
            rows += [u] * len(sib)
            cols += sib
    W = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(U, U))
    deg = np.asarray(W.sum(axis=1)).ravel()
    deg[deg == 0] = 1.0
    return sparse.diags(1.0 / deg) @ W


def _week_axis(through: date) -> list[date]:
    start = _monday(date.fromisoformat(CUBE_FROM))
    n = (through - start).days // 7 + 1
    return [start + timedelta(weeks=i) for i in range(max(n, 0))]


def _dense(conn, unit_type, category, series, units_index, weeks, through) -> np.ndarray:
    Y = np.zeros((len(units_index), len(weeks)), dtype=np.float64)
    cat_sql, params = ("", []) if category == ALL else ("AND category = ?", [category])
    q = (f"SELECT unit, week_start, SUM({series}) FROM forecast_cube "
         f"WHERE unit_type = ? {cat_sql} AND week_start <= ? AND {series} > 0 "
         f"GROUP BY unit, week_start")
    w0 = weeks[0]
    for unit, wk, n in conn.execute(q, [unit_type, *params, through.isoformat()]):
        u = units_index.get(unit)
        if u is None:
            continue
        Y[u, (date.fromisoformat(wk) - w0).days // 7] = n
    return Y


def calendar(conn: sqlite3.Connection, series: str, history_end: date,
             through: date | None = None) -> Calendar:
    """Week axis from CUBE_FROM to `through` (default: history_end). Coverage and level
    use only weeks up to history_end."""
    through = max(through or history_end, history_end)
    weeks = _week_axis(through)
    w0 = weeks[0]
    he = (history_end - w0).days // 7
    tot = np.zeros(len(weeks))
    for wk, n in conn.execute(
            f"SELECT week_start, SUM({series}) FROM forecast_cube WHERE unit_type = 'station' "
            f"AND week_start <= ? GROUP BY week_start", (through.isoformat(),)):
        tot[(date.fromisoformat(wk) - w0).days // 7] = n or 0
    seen = tot.copy()
    seen[he + 1:] = 0                     # coverage of future weeks: judged without them
    cov = np.zeros(len(weeks), dtype=bool)
    for i in range(len(weeks)):
        ref = seen if i <= he else tot
        near = ref[max(0, i - 8): i + 9]
        near = near[near > 0]
        cov[i] = len(near) > 0 and tot[i] >= 0.3 * np.median(near)
    level = np.ones(len(weeks))
    good = cov.copy()
    good[he + 1:] = False
    for i in range(he + 1):
        lo, hi = max(0, i - 26), min(he, i + 26)
        vals = tot[lo: hi + 1][good[lo: hi + 1]]
        level[i] = np.median(vals) if len(vals) else np.nan
    # fill uncovered stretches from the nearest covered level; freeze after history_end
    valid = np.flatnonzero(~np.isnan(level[: he + 1]))
    if len(valid):
        for i in range(he + 1):
            if np.isnan(level[i]):
                level[i] = level[valid[np.argmin(np.abs(valid - i))]]
        level[he + 1:] = level[he]
    else:
        level[:] = 1.0
    return Calendar(series, weeks, he, tot, cov, np.maximum(level, 1e-9))


def load_panel(conn, units: Units, parent_units: Units | None, category: str,
               cal: Calendar) -> Panel:
    weeks = cal.weeks
    through = weeks[-1]
    Y = _dense(conn, units.unit_type, category, cal.series, units.index, weeks, through)
    if units.unit_type == "beat" and parent_units is not None:
        # a station's count includes FIRs with no beat, so read stations directly
        PS = _dense(conn, "station", category, cal.series, parent_units.index, weeks, through)
        parent_Y = np.zeros((len(units.parent_names), len(weeks)))
        pmap = {n: i for i, n in enumerate(units.parent_names)}
        for sname, si in parent_units.index.items():
            if sname in pmap:
                parent_Y[pmap[sname]] = PS[si]
    else:
        # stations → district: sum the stations
        A = sparse.csr_matrix((np.ones(len(units.names)), (units.parent_of, np.arange(len(units.names)))),
                              shape=(len(units.parent_names), len(units.names)))
        parent_Y = A @ Y
    k = cal.scale
    return Panel(units, category, cal, Y * k, parent_Y * k, Y, parent_Y)


def with_calendar(p: Panel, cal: Calendar) -> Panel:
    """The same counts seen from another as-of (same week axis): re-levelled, caches
    dropped. Lets a back-test load a category once and refit at many origins."""
    assert len(cal.weeks) == len(p.weeks) and cal.weeks[0] == p.weeks[0]
    k = cal.scale
    return Panel(p.units, p.category, cal, p.Y_raw * k, p.parent_raw * k, p.Y_raw, p.parent_raw)


EPS = 0.05                  # weekly-rate floor inside the log-ratios
EWMA_HALFLIFE = 4.0
SHRINK_WEEKS = (26.0, 4.0)  # base rate = (26·EWMA + 4·area share) / 30


def ewma(p: Panel) -> np.ndarray:
    """[U × W] EWMA (half-life 4 weeks) of weekly counts through each week; uncovered
    weeks carry the last value."""
    if "ewma" not in p._cum:
        lam = 1 - 0.5 ** (1 / EWMA_HALFLIFE)
        E = np.zeros_like(p.Y)
        cur = None
        for w in range(p.Y.shape[1]):
            if p.covered[w]:
                cur = p.Y[:, w].copy() if cur is None else lam * p.Y[:, w] + (1 - lam) * cur
            if cur is not None:
                E[:, w] = cur
        p._cum["ewma"] = E
    return p._cum["ewma"]


def features(p: Panel, t: int, h: int) -> dict[str, np.ndarray]:
    """Weekly rates for every unit at origin t (horizon h weeks), plus the base rate the
    model multiplies. All at the as-of recording level."""
    last4, _ = p.window_mean(t - 3, t)
    last13, _ = p.window_mean(t - 12, t)
    usual, _ = p.window_mean(t - 51, t)
    last1 = p.Y[:, t] if p.covered[t] else last4
    ly, k = p.window_mean(t + 1 - 52, t + h - 52)
    last_year = ly if k > 0 else usual
    nbr4 = p.units.W @ last4
    nbr_usual = p.units.W @ usual
    # Neighbours' LAST week — the near-repeat signal nbr4 smooths away. Computed always
    # (one sparse mat-vec); it only enters the design when NEAR_REPEAT is on.
    nbr1 = p.units.W @ last1
    p13, _ = p.window_mean(t - 12, t, "parent")
    p52, _ = p.window_mean(t - 51, t, "parent")
    par = p.units.parent_of
    # smoothed share of the parent's FIRs: a unit with no history gets 1/siblings of it
    share = (usual * 52 + 1.0 / p.units.siblings) / (p52[par] * 52 + 1.0)
    area = p13[par] * share
    area_usual = p52[par] * share
    ew = ewma(p)[:, t]
    wk = p.weeks[0] + timedelta(weeks=t + 1)
    doy = (wk + timedelta(days=7 * h / 2)).timetuple().tm_yday
    ang = 2 * np.pi * doy / 365.25
    one = np.ones(p.Y.shape[0])
    return {
        "last1": last1, "last4": last4, "last13": last13, "usual": usual,
        "last_year": last_year, "nbr4": nbr4, "nbr1": nbr1, "nbr_usual": nbr_usual,
        "area": area, "area_usual": area_usual, "ewma": ew,
        "ang": ang * one, "season_on": one,
    }


def base_rate(f: dict[str, np.ndarray]) -> np.ndarray:
    """The weekly level the model multiplies: EWMA shrunk toward the unit's area share."""
    a, b = SHRINK_WEEKS
    return (a * f["ewma"] + b * f["area"]) / (a + b)


SEASON = ("s1", "c1", "s2", "c2")


def _lr(x, y):
    return np.log((x + EPS) / (y + EPS))


def design(f: dict[str, np.ndarray]) -> np.ndarray:
    """Model matrix. Every count enters as a log-ratio — level-free, so a busy station and
    a quiet beat share one set of coefficients — except `scale`, which lets the response
    differ with volume."""
    b = base_rate(f)
    on = f["season_on"]
    cols = {
        "recent1": _lr(f["last1"], b), "recent4": _lr(f["last4"], b),
        "recent13": _lr(f["last13"], b), "usual": _lr(f["usual"], b),
        "last_year": _lr(f["last_year"], f["usual"]),
        "nbr": _lr(f["nbr4"], f["nbr_usual"]), "area": _lr(f["area"], f["area_usual"]),
        # Near-repeat: neighbours' last week against their usual level.
        "near_repeat": _lr(f["nbr1"], f["nbr_usual"]),
        "scale": np.log(b + EPS),
        "s1": on * np.sin(f["ang"]), "c1": on * np.cos(f["ang"]),
        "s2": on * np.sin(2 * f["ang"]), "c2": on * np.cos(2 * f["ang"]),
    }
    return np.column_stack([cols[k] for k in FEATURES])


# The reasons, in the order the forecast is built up from "a usual week here". Each step
# moves some inputs from their usual value to their actual one; the change in the forecast
# at that step is that reason's multiplier. The product of all of them is exact.
DRIVER_STEPS = (
    ("recent", ("last1", "last4", "last13", "ewma")),
    ("last_year", ("last_year",)),
    ("neighbours", ("nbr4",)),
    *((("near_repeat", ("nbr1",)),) if NEAR_REPEAT else ()),
    ("area", ("area",)),
    ("season", ("season_on",)),
)


def usual_state(f: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """The same units in an unremarkable week: recent weeks and last year at the unit's
    own 52-week level, neighbours and area at theirs, no seasonal effect."""
    u = dict(f)
    for k in ("last1", "last4", "last13", "ewma", "last_year"):
        u[k] = f["usual"]
    u["nbr4"] = f["nbr_usual"]
    u["nbr1"] = f["nbr_usual"]
    u["area"] = f["area_usual"]
    u["season_on"] = np.zeros_like(f["season_on"])
    return u


def exposure(f: dict[str, np.ndarray], h: int) -> np.ndarray:
    """The Poisson offset: expected FIRs over the horizon at the base rate."""
    return h * (base_rate(f) + 0.01)
