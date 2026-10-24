"""
Antar/Antar — Evidence Ledger (P0, build03_improveX)
=========================================================
The engineered synthetic FIR set (`fir_synthetic.csv`, copied to app/seeds/data/) exposed
as a backend-queryable *evidence layer*. This is ADDITIVE — the official `FIRs` register
(1,000,000 rows in main.db) stays untouched and continues to power Map/Predict/trends. This layer is the ONLY source
carrying per-accused / vehicle / UPI / IP linkage, so it backs Brain's evidence graph,
corridors, dossiers, and the movement/linkage agents.

Loaded once into memory (the graph_cache pattern — O(1) reads, no DB mutation, fully
deterministic and offline). Names come from `alias_for()`, a FAITHFUL port of the frontend
`lib/crimeGraph.js` aliasFor() so one entity renders the SAME name on Brain (client) and
Search/Chat (server). Aliases are SYNTHETIC — every surface must show them WITH the raw
ACC id and a "synthetic alias" label (honest-data contract).

[VERIFY / production boundary] In a Catalyst deployment this CSV would be ingested into the
Data Store and read via whitelisted ZCQL; here it is an in-memory local layer consistent
with zcql_local's role as the local bridge. Swap `_load()` for a Data Store read on Catalyst.
"""

from __future__ import annotations

import csv
import os
import re
import threading
from datetime import date

# ── alias_for: exact port of frontend lib/crimeGraph.js aliasFor() ──────────────
# Same lists, same modular arithmetic → identical name for a given id on both sides.
_ALIAS_FIRST = ["Ravi", "Suresh", "Manju", "Kiran", "Prakash", "Santosh", "Ramesh", "Vijay",
                "Anil", "Mahesh", "Nagesh", "Girish", "Harish", "Lokesh", "Umesh", "Dinesh",
                "Shankar", "Basava", "Mallika", "Deepa", "Rekha", "Savita", "Lakshmi", "Geetha"]
_ALIAS_LAST = ["Kumar", "Gowda", "Shetty", "Naik", "Rao", "Reddy", "Hegde", "Patil",
               "Swamy", "Murthy", "Acharya", "Poojari", "Kulkarni", "Desai", "Angadi", "Byadgi"]


def alias_for(accused_id: str | None) -> str:
    """Deterministic synthetic display name for an accused id. Mirrors the JS byte-for-byte:
    strip non-digits → int → FIRST[d % 24] + ' ' + LAST[(d // 24) % 16]. '' if no digits."""
    digits = re.sub(r"\D", "", str(accused_id or ""))
    if not digits:
        return ""
    d = int(digits)
    return f"{_ALIAS_FIRST[d % len(_ALIAS_FIRST)]} {_ALIAS_LAST[(d // len(_ALIAS_FIRST)) % len(_ALIAS_LAST)]}"


# ── in-memory store (lazy singleton, graph_cache pattern) ───────────────────────
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "seeds", "data", "fir_synthetic.csv")
_rows: list[dict] | None = None
_by_accused: dict[str, list[dict]] | None = None
_kidx: dict | None = None          # hard-key indexes for linkage (built lazily)
_lock = threading.Lock()
_loaded_on = ""             # the day _rows was loaded for


def _load() -> tuple[list[dict], dict[str, list[dict]]]:
    rows: list[dict] = []
    by: dict[str, list[dict]] = {}
    if not os.path.exists(_CSV_PATH):
        return rows, by
    # A row dated after today is a seeded demo row that has not "happened" yet. Counting it
    # gave corridors a last FIR in December and a recency measured back from it.
    today = date.today().isoformat()
    with open(_CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f)):
            r["_i"] = i
            if _fir_date(r) > today:
                continue
            rows.append(r)
            aid = (r.get("Accused_ID") or "").strip()
            if aid:
                by.setdefault(aid, []).append(r)
    return rows, by


def _ensure() -> None:
    # Reloaded when the day changes: _load() leaves out rows dated after today, and those
    # rows become part of the record at midnight.
    global _rows, _by_accused, _loaded_on, _kidx
    today = date.today().isoformat()
    if _rows is None or _loaded_on != today:
        with _lock:
            if _rows is None or _loaded_on != today:
                _rows, _by_accused = _load()
                _loaded_on, _kidx = today, None


def refresh() -> dict:
    """Force a reload (startup warm / after re-ingest). Returns a small summary."""
    global _rows, _by_accused, _kidx
    with _lock:
        _rows, _by_accused = _load()
        _kidx, _loaded_on = None, date.today().isoformat()
    return {"rows": len(_rows), "accused": len(_by_accused)}


# ── read API ────────────────────────────────────────────────────────────────────
def _distinct(rows: list[dict], col: str) -> list[str]:
    return sorted({(r.get(col) or "").strip() for r in rows if (r.get(col) or "").strip()})


def _top_counts(rows: list[dict], col: str, alt: str | None = None, n: int = 3) -> list[dict]:
    counts: dict[str, int] = {}
    for r in rows:
        v = (r.get(col) or "").strip() or (alt and (r.get(alt) or "").strip()) or ""
        if v:
            counts[v] = counts.get(v, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
    return [{"label": k, "count": v} for k, v in ranked]


def stats() -> dict:
    _ensure()
    return {
        "rows": len(_rows),
        "accused": len(_by_accused),
        "districts": len(_distinct(_rows, "District_Name")),
        "years": _distinct(_rows, "FIR_YEAR"),
        "with_vehicle": sum(1 for r in _rows if (r.get("Vehicle_Reg_No") or "").strip()),
        "with_upi": sum(1 for r in _rows if (r.get("UPI_ID") or "").strip()),
        "with_ip": sum(1 for r in _rows if (r.get("IP_Address") or "").strip()),
        "source": "fir_synthetic.csv (evidence layer, additive to official FIRs)",
    }


def entity(accused_id: str) -> dict | None:
    """Full evidence dossier for one accused id, or None. Every field traces to CSV rows."""
    _ensure()
    rows = _by_accused.get(accused_id)
    if not rows:
        return None
    districts = _distinct(rows, "District_Name")
    return {
        "accused_id": accused_id,
        "alias": alias_for(accused_id),
        "name_note": "synthetic alias",
        "fir_count": len(rows),
        "districts": districts,
        "cross_district": len(districts) > 1,
        "top_crimes": _top_counts(rows, "CrimeHead_Name", alt="CrimeGroup_Name"),
        "vehicles": _distinct(rows, "Vehicle_Reg_No"),
        "upis": _distinct(rows, "UPI_ID"),
        "ips": _distinct(rows, "IP_Address"),
        "years": _distinct(rows, "FIR_YEAR"),
        "firs": [{
            "ref": f"EV-{r['_i']}",
            "district": (r.get("District_Name") or "").strip(),
            "crime": (r.get("CrimeHead_Name") or r.get("CrimeGroup_Name") or "").strip(),
            "year": (r.get("FIR_YEAR") or "").strip(),
            "place": (r.get("Place_of_Offence") or "").strip(),
        } for r in rows[:25]],
    }


_LINK_FIELDS = (("Vehicle_Reg_No", "vehicle"), ("UPI_ID", "upi"), ("IP_Address", "ip"))


def search(q: str, limit: int = 20) -> list[dict]:
    """Resolve a query to evidence entities — by accused id, alias name, or a shared
    vehicle/UPI/IP key. Deterministic: results sorted by (fir_count desc, accused_id)."""
    _ensure()
    ql = (q or "").strip().lower()
    if not ql:
        return []
    hits: list[dict] = []
    for aid, rows in _by_accused.items():
        name = alias_for(aid)
        matched = None
        if ql in aid.lower():
            matched = ("accused_id", aid)
        elif ql in name.lower():
            matched = ("name", name)
        else:
            for r in rows:
                for col, label in _LINK_FIELDS:
                    v = (r.get(col) or "").strip()
                    if v and ql in v.lower():
                        matched = (label, v)
                        break
                if matched:
                    break
        if matched:
            hits.append({
                "accused_id": aid,
                "alias": name,
                "name_note": "synthetic alias",
                "fir_count": len(rows),
                "districts": _distinct(rows, "District_Name"),
                "match_field": matched[0],
                "match_value": matched[1],
            })
    hits.sort(key=lambda h: (-h["fir_count"], h["accused_id"]))
    return hits[:limit]


# ── corridors: real inter-district movement from shared accused ─────────────────
def _fir_date(r: dict) -> str:
    """Sortable YYYY-MM-DD from the CSV's FIR_YEAR/MONTH/Day, or '' if unparseable."""
    try:
        return f"{int(r.get('FIR_YEAR')):04d}-{int(r.get('FIR_MONTH')):02d}-{int(r.get('FIR_Day')):02d}"
    except (TypeError, ValueError):
        return ""


def _dataset_max_date() -> str:
    _ensure()
    dates = [d for d in (_fir_date(r) for r in _rows) if d]
    return max(dates) if dates else ""


def _days_between(d1: str, d2: str) -> int | None:
    from datetime import date
    if not d1 or not d2:
        return None
    try:
        a = date.fromisoformat(d1)
        b = date.fromisoformat(d2)
        return abs((b - a).days)
    except ValueError:
        return None


# Karnataka's bounding box, a little padded. A point outside it is a recording error.
_KA_LAT, _KA_LON = (11.4, 18.6), (73.9, 78.7)


def _in_ka(lat: float, lon: float) -> bool:
    return _KA_LAT[0] <= lat <= _KA_LAT[1] and _KA_LON[0] <= lon <= _KA_LON[1]


def _ka_point(lat, lon) -> tuple[float, float] | None:
    """A usable Karnataka point from one row: as recorded, or with latitude and longitude
    swapped back when they were entered the wrong way round. None otherwise."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if _in_ka(lat, lon):
        return lat, lon
    if _in_ka(lon, lat):
        return lon, lat
    return None


def _district_centroids() -> dict[str, dict]:
    """Median lat/lon per district over its FIR coordinates (for map arc endpoints).

    A plain mean was dragged off by rows with latitude and longitude swapped, and by points
    outside the state: Bengaluru City's endpoint landed at 28.6 N, 60.9 E. Swapped pairs are
    put back, anything still outside Karnataka is dropped, and the median ignores the rest."""
    from statistics import median
    _ensure()
    acc: dict[str, tuple[list[float], list[float]]] = {}
    for r in _rows:
        dn = (r.get("District_Name") or "").strip()
        pt = _ka_point(r.get("Latitude"), r.get("Longitude")) if dn else None
        if pt is None:
            continue
        lats, lons = acc.setdefault(dn, ([], []))
        lats.append(pt[0])
        lons.append(pt[1])
    return {d: {"lat": round(median(la), 6), "lon": round(median(lo), 6)} for d, (la, lo) in acc.items() if la}


def corridors(limit: int = 20) -> list[dict]:
    """Real inter-district corridors: an accused appearing in ≥2 districts links each
    pair of those districts. Aggregated across all accused. Every field is COUNTED from
    the CSV rows — no fixtures. Deterministic (total sort). Used by the A2 Corridor agent."""
    _ensure()
    acc_districts: dict[str, set] = {}
    for aid, rows in _by_accused.items():
        ds = {(r.get("District_Name") or "").strip() for r in rows if (r.get("District_Name") or "").strip()}
        if len(ds) >= 2:
            acc_districts[aid] = ds

    pairs: dict[tuple, dict] = {}
    for aid, ds in acc_districts.items():
        dl = sorted(ds)
        rows = _by_accused[aid]
        for i in range(len(dl)):
            for j in range(i + 1, len(dl)):
                e = pairs.setdefault((dl[i], dl[j]), {"accused": {}, "crimes": {}, "last": "", "firs": 0})
                cnt = 0
                for r in rows:
                    dn = (r.get("District_Name") or "").strip()
                    if dn == dl[i] or dn == dl[j]:
                        cnt += 1
                        ch = (r.get("CrimeHead_Name") or r.get("CrimeGroup_Name") or "").strip()
                        if ch:
                            e["crimes"][ch] = e["crimes"].get(ch, 0) + 1
                        dt = _fir_date(r)
                        if dt > e["last"]:
                            e["last"] = dt
                e["accused"][aid] = cnt
                e["firs"] += cnt

    cent = _district_centroids()
    maxd = _dataset_max_date()
    out = []
    for (a, b), e in pairs.items():
        accused_ids = sorted(e["accused"], key=lambda x: (-e["accused"][x], x))
        # next-district estimate: among these linking offenders, which OTHER district do they most share?
        nextc: dict[str, int] = {}
        for aid in accused_ids:
            for d in acc_districts[aid]:
                if d != a and d != b:
                    nextc[d] = nextc.get(d, 0) + 1
        nd = None
        if nextc:
            top_d, top_n = max(nextc.items(), key=lambda kv: (kv[1], kv[0]))
            nd = {"district": top_d, "count": top_n, "of": len(accused_ids),
                  "probability": round(top_n / len(accused_ids), 2),
                  "reason": f"{top_n} of {len(accused_ids)} linked offenders also appear in {top_d}"}
        top_crime = max(e["crimes"].items(), key=lambda kv: (kv[1], kv[0]))[0] if e["crimes"] else ""
        out.append({
            "src": a, "dst": b,
            "linking_accused": len(accused_ids),
            "accused_ids": accused_ids,
            "fir_count": e["firs"],
            "last_date": e["last"],
            "recency_days": _days_between(e["last"], maxd),
            "top_crime": top_crime,
            "next_district": nd,
            "src_lat": cent.get(a, {}).get("lat"), "src_lon": cent.get(a, {}).get("lon"),
            "dst_lat": cent.get(b, {}).get("lat"), "dst_lon": cent.get(b, {}).get("lon"),
        })
    out.sort(key=lambda c: (-c["linking_accused"], -c["fir_count"], c["src"], c["dst"]))
    return out[:limit]


# ── linkage: MO case-matching via shared hard keys ──────────────────────────────
def _row_by_ref(ref: str) -> dict | None:
    """Resolve an evidence FIR ref 'EV-{i}' to its row. Strict — only EV- refs (an
    official 'FIR-2026-xxxx' id is NOT in the evidence layer and resolves to None)."""
    _ensure()
    ref = str(ref or "").strip()
    if not ref.upper().startswith("EV-"):
        return None
    try:
        i = int(ref.split("-", 1)[1])
    except (ValueError, IndexError):
        return None
    # 'EV-{i}' is the CSV row number, not a position in _rows: rows dated after today are
    # left out, so positions shift. _rows stays in CSV order, so a bisect finds it.
    from bisect import bisect_left
    k = bisect_left(_rows, i, key=lambda r: r["_i"])
    return _rows[k] if k < len(_rows) and _rows[k]["_i"] == i else None


def _key_index() -> dict:
    """Lazy index of rows by each shared hard key (vehicle / UPI / IP / place)."""
    global _kidx
    _ensure()
    if _kidx is None:
        idx = {"Vehicle_Reg_No": {}, "UPI_ID": {}, "IP_Address": {}, "Place_of_Offence": {}}
        for r in _rows:
            for col in idx:
                v = (r.get(col) or "").strip()
                if v:
                    idx[col].setdefault(v, []).append(r)
        _kidx = idx
    return _kidx


# (column, points, human label) — the transparent linkage scoring. Same-accused is
# the strongest signal; a shared vehicle/UPI/IP across DIFFERENT accused = a ring.
_LINK_SCORES = [
    ("Accused_ID", 50, "shared accused"),
    ("Vehicle_Reg_No", 40, "shared vehicle"),
    ("UPI_ID", 35, "shared UPI"),
    ("IP_Address", 30, "shared IP / device"),
    ("Place_of_Offence", 15, "shared place of offence"),
]


def linkage(fir_ref: str, limit: int = 8) -> dict | None:
    """Candidate same-offender / same-ring FIRs for one evidence FIR, ranked by a
    transparent shared-hard-key score. Every candidate cites the exact shared key.
    None if the ref isn't a real evidence row. Deterministic."""
    row = _row_by_ref(fir_ref)
    if row is None:
        return None
    idx = _key_index()
    cand: dict[int, dict] = {}
    for col, pts, label in _LINK_SCORES:
        v = (row.get(col) or "").strip()
        if not v:
            continue
        pool = _by_accused.get(v, []) if col == "Accused_ID" else idx.get(col, {}).get(v, [])
        for cr in pool:
            if cr["_i"] == row["_i"]:
                continue
            e = cand.setdefault(cr["_i"], {"row": cr, "score": 0, "chips": []})
            e["score"] += pts
            disp = f"{alias_for(v)} [{v}]" if col == "Accused_ID" else v
            e["chips"].append(f"{label}: {disp}")
    out = []
    for e in cand.values():
        cr = e["row"]
        sc = min(100, e["score"])
        out.append({
            "linked_fir_id": f"EV-{cr['_i']}",
            "district": (cr.get("District_Name") or "").strip(),
            "crime_type": (cr.get("CrimeHead_Name") or cr.get("CrimeGroup_Name") or "").strip(),
            "date": _fir_date(cr),
            "total_score": sc,
            "confidence": "High" if sc >= 70 else "Medium" if sc >= 40 else "Low",
            "reason_chips": e["chips"],
        })
    out.sort(key=lambda c: (-c["total_score"], c["linked_fir_id"]))
    return {"fir_ref": fir_ref, "candidates": out[:limit]}


def priority_fir_refs(limit: int = 10, min_firs: int = 2) -> list[str]:
    """EV-refs of a representative FIR for each of the most-active multi-FIR accused —
    the natural 'high-priority' set for bulk linkage compilation. Deterministic."""
    _ensure()
    accs = sorted(((aid, len(rows)) for aid, rows in _by_accused.items() if len(rows) >= min_firs),
                  key=lambda kv: (-kv[1], kv[0]))
    return [f"EV-{_by_accused[aid][0]['_i']}" for aid, _ in accs[:limit]]


def top_offenders(limit: int = 5) -> list[dict]:
    """Most-active accused by FIR count — real, deterministic. For briefs / voice answers."""
    _ensure()
    ranked = sorted(_by_accused.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:limit]
    return [{"accused_id": aid, "alias": alias_for(aid), "fir_count": len(rows),
             "districts": _distinct(rows, "District_Name")} for aid, rows in ranked]


_PLACE_FIELDS = ("District_Name", "UnitName", "Place_of_Offence", "Beat_Name", "Village_Area_Name")


def crime_count(keyword: str, place: str | None = None, limit_refs: int = 3) -> tuple[int, list[str]]:
    """Real count of FIRs whose crime text contains `keyword`, optionally within a place
    (matched across district/unit/place/beat/village). Returns (count, sample EV-refs)."""
    _ensure()
    kw = (keyword or "").strip().lower()
    if not kw:
        return 0, []
    pl = (place or "").strip().lower()
    hits = [r for r in _rows
            if kw in f"{r.get('CrimeGroup_Name', '')} {r.get('CrimeHead_Name', '')}".lower()
            and (not pl or any(pl in (r.get(f) or "").lower() for f in _PLACE_FIELDS))]
    return len(hits), [f"EV-{r['_i']}" for r in hits[:limit_refs]]
