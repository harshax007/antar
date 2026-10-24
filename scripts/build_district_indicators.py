"""
Build data/district_indicators.csv: social indicators for Karnataka's 30 revenue districts.

    python -I scripts/build_district_indicators.py

Reads the public downloads in data/external/ (not committed) and writes one CSV that is:

  Census of India 2011    population, decadal growth 2001-11, density, sex ratio, literacy,
                          urban share. Via census2011.co.in's district pages
                          (data/external/census2011/).
  NFHS-5 (2019-21)        district factsheets, IIPS / Ministry of Health and Family Welfare.
                          Via Pratap Vardhan's CSV of the factsheets (CC BY 4.0,
                          github.com/pratapvardhan/NFHS-5), data/external/nfhs5/.

Vijayanagara was carved out of Ballari in 2020-21; both sources predate it, so Ballari's
figures cover both. Every column's label, unit, year and source go into the second file,
data/district_indicators_meta.csv, which the app shows beside each number.
"""
from __future__ import annotations

import csv
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "data", "external")
OUT = os.path.join(ROOT, "data", "district_indicators.csv")
META = os.path.join(ROOT, "data", "district_indicators_meta.csv")

# census2011.co.in / NFHS spelling -> the name used here (Karnataka's current official names)
NAMES = {
    "bangalore": "Bengaluru Urban", "bangalore rural": "Bengaluru Rural", "belgaum": "Belagavi",
    "bellary": "Ballari", "bijapur": "Vijayapura", "chamarajanagar": "Chamarajanagara",
    "chikkaballapura": "Chikkaballapura", "chikkaballapur": "Chikkaballapura", "chikmagalur": "Chikkamagaluru",
    "gulbarga": "Kalaburagi", "mysore": "Mysuru", "shimoga": "Shivamogga", "tumkur": "Tumakuru",
    "dharwad": "Dharwad", "davanagere": "Davanagere", "davangere": "Davanagere", "yadgir": "Yadgir",
    "bagalkot": "Bagalkot", "bidar": "Bidar", "chitradurga": "Chitradurga", "dakshina kannada": "Dakshina Kannada",
    "gadag": "Gadag", "hassan": "Hassan", "haveri": "Haveri", "kodagu": "Kodagu", "kolar": "Kolar",
    "koppal": "Koppal", "mandya": "Mandya", "raichur": "Raichur", "ramanagara": "Ramanagara",
    "udupi": "Udupi", "uttara kannada": "Uttara Kannada",
}

# NFHS-5 indicators kept: the ones criminology links to crime, and that the factsheets give
# for every district. key: (indicator number in the factsheet, label, direction note)
NFHS = {
    "women_literate": (14, "Women who are literate", "%"),
    "women_10y_school": (15, "Women with 10 or more years of schooling", "%"),
    "child_marriage": (16, "Women 20-24 married before 18", "%"),
    "teen_pregnancy": (18, "Women 15-19 already mothers or pregnant", "%"),
    "electricity": (7, "Population in households with electricity", "%"),
    "clean_fuel": (10, "Households using clean cooking fuel", "%"),
    "sanitation": (9, "Population with improved sanitation", "%"),
    "health_insurance": (12, "Households with health insurance", "%"),
    "child_stunting": (73, "Children under 5 who are stunted", "%"),
    "men_alcohol": (104, "Men 15+ who drink alcohol", "%"),
    "men_tobacco": (102, "Men 15+ who use tobacco", "%"),
}

CENSUS_META = {
    "population_2011": ("Population", "people", "Census of India 2011"),
    "decadal_growth": ("Population growth 2001-11", "%", "Census of India 2011"),
    "density": ("Population density", "per km2", "Census of India 2011"),
    "sex_ratio_2011": ("Sex ratio", "women per 1,000 men", "Census of India 2011"),
    "literacy_2011": ("Literacy", "%", "Census of India 2011"),
    "urban_pct": ("Living in urban areas", "%", "Census of India 2011"),
}


def _num(s: str) -> float | None:
    s = str(s or "").replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _name(raw: str) -> str | None:
    return NAMES.get(" ".join(str(raw).lower().replace("district", "").split()))


def census() -> dict[str, dict]:
    d = os.path.join(EXT, "census2011")
    page = open(os.path.join(d, "karnataka_districts.html"), encoding="utf-8", errors="replace").read()
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [html.unescape(re.sub("<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        name = _name(cells[1])
        if not name:
            raise SystemExit(f"unmapped census district: {cells[1]!r}")
        out[name] = {"population_2011": _num(cells[3]), "decadal_growth": _num(cells[4]),
                     "sex_ratio_2011": _num(cells[5]), "literacy_2011": _num(cells[6]), "density": _num(cells[7])}
    for f in glob.glob(os.path.join(d, "*-*.html")):
        t = html.unescape(re.sub(r"<[^>]+>", " ", open(f, encoding="utf-8", errors="replace").read()))
        t = re.sub(r"\s+", " ", t)
        m = re.search(r"Out of the total (.+?) population for 2011 census, ([\d.]+) percent lives in urban", t)
        if not m:
            raise SystemExit(f"no urban share in {f}")
        name = _name(m.group(1))
        if name not in out:
            raise SystemExit(f"district page {f} ({m.group(1)!r}) not in the list")
        out[name]["urban_pct"] = float(m.group(2))
    return out


def nfhs() -> dict[str, dict]:
    path = os.path.join(EXT, "nfhs5", "NFHS-5-Districts.csv")
    out: dict[str, dict] = {}
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        if "karnataka" not in r["State"].lower():
            continue
        name = _name(r["District"])
        if not name:
            raise SystemExit(f"unmapped NFHS district: {r['District']!r}")
        m = re.match(r"\s*(\d+)\.", r["Indicator"])
        if not m:
            continue
        no = int(m.group(1))
        for key, (num, _, _) in NFHS.items():
            if num == no:
                out.setdefault(name, {})[key] = _num(r["NFHS-5"])
    return out


def main() -> None:
    c, n = census(), nfhs()
    names = sorted(set(c) | set(n))
    missing = [x for x in names if x not in c or x not in n]
    if missing:
        raise SystemExit(f"districts missing from one source: {missing}")
    cols = ["district"] + list(CENSUS_META) + list(NFHS)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for name in names:
            w.writerow([name] + [c[name].get(k) for k in CENSUS_META] + [n[name].get(k) for k in NFHS])
    with open(META, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["key", "label", "unit", "source", "year"])
        for k, (label, unit, src) in CENSUS_META.items():
            w.writerow([k, label, unit, src, "2011"])
        for k, (_, label, unit) in NFHS.items():
            w.writerow([k, label, unit, "NFHS-5 district factsheets (IIPS, MoHFW)", "2019-21"])
    print(f"{len(names)} districts, {len(cols) - 1} indicators -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
