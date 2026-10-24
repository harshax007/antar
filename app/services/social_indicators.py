"""
Antar - district social indicators against crime
================================================
How crime rates across Karnataka's 30 districts line up with social indicators: urbanisation,
population growth (a proxy for migration), literacy and schooling, child marriage, household
amenities (an economic proxy), alcohol use. Indicators come from data/district_indicators.csv
(Census 2011, NFHS-5 2019-21; scripts/build_district_indicators.py). Crime is the register's
real FIRs, 2016-2022, as a yearly rate per lakh people.

What it can and cannot say, stated with every result:
  - 30 districts: a correlation is about districts, never about the people in them
    (the ecological fallacy). It is never a basis to target any group.
  - Recorded crime depends on reporting. Cities report more, so many indicators that rise
    with urbanisation look linked to crime for that reason alone; each link is also given
    with urbanisation held constant.
  - Correlation is not cause.

Spearman's rank correlation is the headline (30 points, one of them Bengaluru: a rank method
does not let one district decide the answer); Pearson is given beside it.
"""
from __future__ import annotations

import csv
import os
import threading
import time
from functools import lru_cache

import numpy as np
from scipy import stats

from app.core.db_path import DB_PATH, registry_connect

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "district_indicators.csv")
META = os.path.join(ROOT, "data", "district_indicators_meta.csv")
YEARS = (2016, 2022)            # the real record's consistent years (2023 is an outlier extract)

# police district (FIRs.district_norm) -> revenue district (Census, NFHS)
POLICE_TO_REVENUE = {
    "Bagalkot": "Bagalkot", "Ballari": "Ballari", "Vijayanagara": "Ballari",
    "Belagavi City": "Belagavi", "Belagavi Dist": "Belagavi",
    "Bengaluru City": "Bengaluru Urban", "Bengaluru Dist": "Bengaluru Rural",
    "Bidar": "Bidar", "Chamarajanagar": "Chamarajanagara", "Chickballapura": "Chikkaballapura",
    "Chikkamagaluru": "Chikkamagaluru", "Chitradurga": "Chitradurga",
    "Dakshina Kannada": "Dakshina Kannada", "Mangaluru City": "Dakshina Kannada",
    "Davanagere": "Davanagere", "Dharwad": "Dharwad", "Hubballi Dharwad City": "Dharwad",
    "Gadag": "Gadag", "Hassan": "Hassan", "Haveri": "Haveri",
    "Kalaburagi": "Kalaburagi", "Kalaburagi City": "Kalaburagi", "Kodagu": "Kodagu",
    "Kolar": "Kolar", "K.G.F": "Kolar", "Koppal": "Koppal", "Mandya": "Mandya",
    "Mysuru City": "Mysuru", "Mysuru Dist": "Mysuru", "Raichur": "Raichur", "Ramanagara": "Ramanagara",
    "Shivamogga": "Shivamogga", "Tumakuru": "Tumakuru", "Udupi": "Udupi", "Uttara Kannada": "Uttara Kannada",
    "Vijayapur": "Vijayapura", "Yadgir": "Yadgir",
}
STATEWIDE_UNITS = ("CID", "Coastal Security Police", "ISD Bengaluru", "Karnataka Railways")

CATEGORIES = {
    "all": ("All crime", None),
    "property": ("Property crime", ("THEFT", "BURGLARY", "ROBBERY", "DACOITY", "HOUSE BREAK", "SNATCH")),
    "violent": ("Violent crime", ("MURDER", "HURT", "ASSAULT", "CULPABLE", "KIDNAP", "ABDUCT", "RIOT", "AFFRAY")),
    "women": ("Crimes against women", ("WOMEN", "CRUELTY BY HUSBAND", "DOWRY", "RAPE", "POCSO", "MOLEST", "DISROBE", "OUTRAG")),
    "fraud": ("Fraud and cyber crime", ("CYBER", "CHEATING", "BREACH OF TRUST", "FORGERY", "COUNTERFEIT")),
    "road": ("Road accidents", ("ACCIDENT", "RASHNESS", "MOTOR VEHICLE")),
}

CAVEATS = [
    "These are 30 districts. A link between a district's figures says nothing about any person in it, and is never a basis to target a group.",
    "Recorded crime depends on reporting: cities report more. Each link is also shown with urbanisation held constant.",
    "Correlation is not cause.",
    "Indicators are from Census 2011 and NFHS-5 (2019-21); crime is the register's FIRs for 2016-2022, a yearly rate per lakh people on 2011 population.",
]

_lock = threading.Lock()
_cache: dict | None = None
_cache_at = 0.0
_TTL_S = 3600


def _category(group: str) -> list[str]:
    g = (group or "").upper()
    return ["all"] + [k for k, (_, keys) in CATEGORIES.items() if keys and any(x in g for x in keys)]


@lru_cache(maxsize=1)
def indicators() -> tuple[list[dict], dict]:
    rows = list(csv.DictReader(open(DATA, encoding="utf-8")))
    meta = {r["key"]: r for r in csv.DictReader(open(META, encoding="utf-8"))}
    for r in rows:
        for k in meta:
            r[k] = float(r[k]) if r.get(k) not in (None, "") else None
    return rows, meta


def _rates() -> dict[str, dict[str, float]]:
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        q = con.execute(
            "SELECT district_norm, CrimeGroup_Name, COUNT(*) FROM FIRs WHERE is_synthetic_row = 0 "
            "AND date >= ? AND date < ? GROUP BY 1, 2", (f"{YEARS[0]}-01-01", f"{YEARS[1] + 1}-01-01")).fetchall()
    finally:
        con.close()
    counts: dict[str, dict[str, int]] = {}
    for pd_, group, n in q:
        rev = POLICE_TO_REVENUE.get(pd_ or "")
        if not rev:
            continue
        for cat in _category(group):
            counts.setdefault(rev, {}).setdefault(cat, 0)
            counts[rev][cat] += n
    years = YEARS[1] - YEARS[0] + 1
    pop = {r["district"]: r["population_2011"] for r in indicators()[0]}
    return {d: {c: round(n / years / pop[d] * 1e5, 2) for c, n in cs.items()} | {"firs": cs.get("all", 0)}
            for d, cs in counts.items() if pop.get(d)}


def _strength(rho: float) -> str:
    a = abs(rho)
    return "strong" if a >= 0.6 else "moderate" if a >= 0.4 else "weak" if a >= 0.2 else "no"


def _partial_spearman(x, y, z) -> tuple[float, float]:
    """Spearman correlation of x and y with z held constant (on ranks), and its p-value."""
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))
    A = np.column_stack([np.ones_like(rz), rz])
    ex = rx - A @ np.linalg.lstsq(A, rx, rcond=None)[0]
    ey = ry - A @ np.linalg.lstsq(A, ry, rcond=None)[0]
    r = float(np.corrcoef(ex, ey)[0, 1])
    n = len(x)
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r * r))
    p = float(2 * stats.t.sf(abs(t), n - 3))
    return r, p


# Indicators of development and of deprivation. When better-off districts record MORE crime
# (or deprived ones less), the usual reading in criminology is reporting and registration -
# education, access to a police station, trust - not that development causes crime.
DEVELOPMENT = {"urban_pct", "literacy_2011", "women_literate", "women_10y_school", "electricity",
               "clean_fuel", "sanitation", "health_insurance", "density"}
DEPRIVATION = {"child_marriage", "teen_pregnancy", "child_stunting"}
CRIME_WORDS = {"all": "crime", "property": "property crime", "violent": "violent crime",
               "women": "crime against women", "fraud": "fraud and cyber crime", "road": "road accidents"}


def _sentence(label: str, unit: str, cat: str, rho: float, p: float) -> str:
    crime = CRIME_WORDS.get(cat, cat)
    what = label[0].lower() + label[1:]
    if p >= 0.05 or abs(rho) < 0.2:
        return f"No clear link between {what} and recorded {crime} across districts."
    more = "more" if rho > 0 else "less"
    lead = {"Population growth 2001-11": "faster population growth (2001-11)",
            "Living in urban areas": "more people living in urban areas"}.get(label)         or (f"a higher share of {what}" if unit == "%" else f"higher {what}")
    return f"Districts with {lead} record {more} {crime} ({_strength(rho)} link)."


def _reading(key: str, rho: float, significant: bool) -> str | None:
    if not significant:
        return None
    if (key in DEVELOPMENT and rho > 0) or (key in DEPRIVATION and rho < 0):
        return ("Better-off districts recording more crime usually reflects reporting and registration "
                "(education, access to a police station), not more offending.")
    if key in ("men_alcohol", "men_tobacco") and rho > 0:
        return "Consistent with research linking alcohol to violence and crimes against women; still a district-level link, not a cause."
    if key == "decadal_growth" and rho > 0:
        return "Fast-growing districts draw migrants; a link here is about places changing quickly, not about migrants."
    return None


def analysis() -> dict:
    global _cache, _cache_at
    with _lock:
        if _cache is not None and time.time() - _cache_at < _TTL_S:
            return _cache
        rows, meta = indicators()
        rates = _rates()
        districts = [r for r in rows if r["district"] in rates]
        urban = np.array([r["urban_pct"] for r in districts], dtype=float)
        out = {}
        for cat, (crime_label, _) in CATEGORIES.items():
            y = np.array([rates[r["district"]].get(cat, 0.0) for r in districts], dtype=float)
            links = []
            for key, m in meta.items():
                if key == "population_2011":
                    continue
                x = np.array([r[key] for r in districts], dtype=float)
                if np.isnan(x).any():
                    continue
                rho, p = stats.spearmanr(x, y)
                pr, pp = stats.pearsonr(x, y)
                item = {"key": key, "label": m["label"], "unit": m["unit"], "source": m["source"], "year": m["year"],
                        "spearman": round(float(rho), 3), "p": round(float(p), 4),
                        "pearson": round(float(pr), 3), "pearson_p": round(float(pp), 4),
                        "strength": _strength(rho), "significant": bool(p < 0.05 and abs(rho) >= 0.2),
                        "sentence": _sentence(m["label"], m["unit"], cat, float(rho), float(p))}
                item["reading"] = _reading(key, float(rho), item["significant"])
                if key != "urban_pct":
                    prho, pp2 = _partial_spearman(x, y, urban)
                    item.update({"partial_urban": round(prho, 3), "partial_p": round(pp2, 4),
                                 "holds_without_urban": bool(pp2 < 0.05 and abs(prho) >= 0.2 and np.sign(prho) == np.sign(rho))})
                links.append(item)
            links.sort(key=lambda l: (not l["significant"], -abs(l["spearman"])))
            out[cat] = {"label": crime_label, "links": links}
        table = []
        for r in districts:
            table.append({"district": r["district"], **{k: r[k] for k in meta},
                          "rates": {c: rates[r["district"]].get(c, 0.0) for c in CATEGORIES},
                          "firs": rates[r["district"]]["firs"]})
        _cache = {"years": list(YEARS), "districts": len(districts), "categories": {k: v[0] for k, v in CATEGORIES.items()},
                  "indicators": list(meta.values()), "table": table, "correlations": out, "caveats": CAVEATS,
                  "excluded_units": list(STATEWIDE_UNITS),
                  "sources": [
                      {"name": "Census of India 2011", "via": "census2011.co.in district pages"},
                      {"name": "NFHS-5 (2019-21) district factsheets, IIPS and MoHFW",
                       "via": "github.com/pratapvardhan/NFHS-5 (CC BY 4.0)"}]}
        _cache_at = time.time()
        return _cache
