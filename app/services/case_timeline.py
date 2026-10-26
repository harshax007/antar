"""
Antar - one case, start to finish
=================================
An automated case summary and investigation timeline for one FIR, and how cases like it
have ended. Deterministic: every line is read from the FIR row or counted over the register.
No model writes any of it.

What the register records, and what it does not, decides the shape:

  recorded        the registration date, the station, the sections, the stage the case is at
                  (Under Investigation, Pending Trial, Convicted, ...), and COUNTS of accused,
                  arrested, charge-sheeted and convicted
  not recorded    the DATES of arrest, charge-sheet and verdict

So the timeline dates only the registration. Every later step says how far the case got
and, where the date is missing, says so, rather than placing a guessed date on a line an
officer might quote. The one clock that can be computed honestly is the investigation's:
days since registration against the BNSS s.187(3) 60- and 90-day marks, which matter while
a case is still under investigation.

"Cases like this" are the same crime head at the same station, widened to the district
and then the state when the station has too few to be worth a percentage.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from app.core.db_path import DB_PATH, registry_connect

# BNSS s.187(3): default bail if the investigation is not complete in 60 days, or 90 for
# offences punishable with death, life or ten years or more. The register does not say
# which applies to a case, so both marks are shown (as on the Brain's pendency view).
LIMIT_SHORT, LIMIT_LONG = 60, 90
MIN_SIMILAR = 30                 # fewer cases than this and a rate is not worth showing
MIN_DECIDED = 10                 # a conviction rate over fewer verdicts than this misleads

_COLS = ("fir_id, CrimeNo, date, zone, District_Name, district_norm, UnitName, station, FIR_Type, FIR_Stage, "
         "status, CrimeGroup_Name, CrimeHead_Name, crime_type, ActSection, Place_of_Offence, "
         "Village_Area_Name, Beat_Name, IOName, VICTIM_COUNT, Male, Female, Boy, Girl, Accused_Count, "
         "Arrested_Count_No_, Accused_ChargeSheeted_Count, Conviction_Count, Accused_ID, MO_Details, UPI_ID, "
         "is_synthetic_row")

# How each recorded stage reads, and where it leaves the case.
#   step: the last step the case reached   end: how it closed (None = still open)
_STAGES = {
    "UNDER INVESTIGATION": ("investigation", None),
    "TRANSFERRED - UNDER INVESTIGATION": ("investigation", None),
    "TRACED": ("investigation", None),
    "PENDING TRIAL": ("court", None),
    "CONVICTED": ("court", "Convicted"),
    "DIS/ACQ": ("court", "Discharged or acquitted"),
    "COMPOUNDED": ("court", "Compounded (settled between the parties)"),
    "BOUNDOVER": ("court", "Bound over"),
    "ABATED": ("court", "Abated (the accused died)"),
    "UNDETECTED": ("investigation", "Closed as undetected"),
    "FALSE CASE": ("investigation", "Closed as a false case"),
    "OTHER DISPOSAL": ("investigation", "Disposed of otherwise"),
    # The 2026 demonstration rows spell stages their own way (CHARGE_SHEETED, UN TRACED,
    # DISPOSED). Unlisted, a charge-sheeted case read as "still under investigation", and
    # 167 Robbery cases at a station "0% reached court".
    "CHARGE SHEETED": ("court", None),
    "CHARGESHEETED": ("court", None),
    "UN TRACED": ("investigation", "Closed as undetected"),
    "DISPOSED": ("investigation", "Disposed of otherwise"),
}


def _stage(v) -> str:
    """A register stage as a _STAGES key: 'Under_Investigation' -> 'UNDER INVESTIGATION'."""
    return " ".join(str(v or "").upper().replace("_", " ").split())


def _by_stage(rows) -> dict:
    by: dict = {}
    for x in rows:
        k = _stage(x["st"])
        by[k] = by.get(k, 0) + x["n"]
    return by


def _undetected(by: dict) -> int:
    return sum(n for k, n in by.items() if _STAGES.get(k, ("", None))[1] == "Closed as undetected")
_STEPS = ("registered", "investigation", "arrest", "chargesheet", "court")
_ENDED_KN = {
    "Convicted": "ಶಿಕ್ಷೆಯಾಗಿದೆ",
    "Discharged or acquitted": "ಬಿಡುಗಡೆ ಅಥವಾ ಖುಲಾಸೆ",
    "Compounded (settled between the parties)": "ರಾಜಿ (ಪಕ್ಷಗಳ ನಡುವೆ ಇತ್ಯರ್ಥ)",
    "Bound over": "ಮುಚ್ಚಳಿಕೆ ಮೇಲೆ ಬಿಡುಗಡೆ",
    "Abated (the accused died)": "ಕೊನೆಗೊಂಡಿದೆ (ಆರೋಪಿ ಮೃತಪಟ್ಟಿದ್ದಾರೆ)",
    "Closed as undetected": "ಪತ್ತೆಯಾಗದೆ ಮುಚ್ಚಲಾಗಿದೆ",
    "Closed as a false case": "ಸುಳ್ಳು ಪ್ರಕರಣವೆಂದು ಮುಚ್ಚಲಾಗಿದೆ",
    "Disposed of otherwise": "ಬೇರೆ ರೀತಿಯಲ್ಲಿ ವಿಲೇವಾರಿ",
}


def _int(v) -> int:
    try:
        return max(0, int(v or 0))
    except (TypeError, ValueError):
        return 0


_MONTH_KN = ("ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್",
             "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್")


def _nice(iso: str | None, kn: bool = False) -> str:
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso or "")
    if kn:
        return f"{d.day} {_MONTH_KN[d.month - 1]} {d.year}"
    return f"{d.day} {d.strftime('%b %Y')}"          # %-d is not portable to Windows


def _crime_kn(label: str) -> str:
    """The crime in Kannada where the display map has it; the register's own words otherwise."""
    from app.agents.display_names import display_crime
    k = display_crime(label, "kn")
    return label if k == str(label).lower() else k


def _crime_label(group: str | None, head: str | None) -> str:
    """'THEFT' + 'Of Cattle' -> 'Theft (of cattle)'. The register's heads are sub-headings that
    read as nothing on their own ('Other Roads', 'Cash'), so the group goes first."""
    g = " ".join(str(group or "").replace("_", " ").split())
    h = " ".join(str(head or "").replace("_", " ").split())
    g = g[:1].upper() + g[1:].lower() if g else ""
    if g and h and h.lower() not in g.lower():
        return f"{g} ({h.lower()})"
    return g or h or "Case"


def _sections(act: str | None) -> list[str]:
    """'IPC 1860 U/s: 338 && IPC 1860 U/s: 337' -> ['IPC 338', 'IPC 337']"""
    out = []
    for part in str(act or "").split("&&"):
        p = " ".join(part.split())
        if not p:
            continue
        law, _, sec = p.partition("U/s:")
        law = " ".join(w for w in law.split() if not w.isdigit()) or law.strip()
        label = f"{law} {sec.strip()}".strip() if sec else p
        if label not in out:
            out.append(label)
    return out[:8]


def find(con: sqlite3.Connection, fir: str, station: str | None = None) -> sqlite3.Row | None:
    """By fir_id first (indexed, unique); else by crime number, narrowed by station because a
    crime number repeats across stations."""
    con.row_factory = sqlite3.Row
    today = date.today().isoformat()
    row = con.execute(f"SELECT {_COLS} FROM FIRs WHERE fir_id = ? AND date <= ?", (fir, today)).fetchone()
    if row is None and station:
        row = con.execute(f"SELECT {_COLS} FROM FIRs WHERE TRIM(UPPER(station)) = TRIM(UPPER(?)) "
                          "AND CrimeNo = ? AND date <= ? LIMIT 1", (station, fir, today)).fetchone()
    return row


def _similar(con: sqlite3.Connection, r: sqlite3.Row) -> dict | None:
    """How cases with the same crime head ended: the station, else the district, else the state."""
    head = r["CrimeHead_Name"] or r["crime_type"]
    if not head:
        return None
    col = "CrimeHead_Name" if r["CrimeHead_Name"] else "crime_type"
    today = date.today().isoformat()
    scopes = (("station", "TRIM(UPPER(station)) = TRIM(UPPER(?))", r["station"]),
              ("district", "TRIM(UPPER(district_norm)) = TRIM(UPPER(?))", r["district_norm"]),
              ("state", None, None))
    for scope, clause, val in scopes:
        if clause and not val:
            continue
        where = [f"{col} = ?", "date <= ?", "fir_id <> ?"]
        args: list = [head, today, r["fir_id"]]
        if clause:
            where.insert(0, clause)
            args.insert(0, val)
        rows = con.execute(
            "SELECT UPPER(TRIM(FIR_Stage)) AS st, COUNT(*) AS n FROM FIRs WHERE "
            + " AND ".join(where) + " GROUP BY 1", args).fetchall()
        total = sum(x["n"] for x in rows)
        if total < MIN_SIMILAR and scope != "state":
            continue
        by = _by_stage(rows)
        open_inv = sum(by.get(k, 0) for k in ("UNDER INVESTIGATION", "TRANSFERRED - UNDER INVESTIGATION", "TRACED"))
        reached_court = sum(n for k, n in by.items() if _STAGES.get(k, ("", None))[0] == "court")
        decided = by.get("CONVICTED", 0) + by.get("DIS/ACQ", 0)
        pct = lambda n, d: round(100 * n / d) if d else None   # noqa: E731
        where_label = {"station": r["station"], "district": r["district_norm"], "state": "Karnataka"}[scope]
        return {
            "scope": scope, "where": where_label, "cases": total,
            "crime_head": _crime_label(r["CrimeGroup_Name"], head),
            "still_under_investigation": pct(open_inv, total),
            "reached_court": pct(reached_court, total),
            "undetected": pct(_undetected(by), total),
            "convicted_of_decided": pct(by.get("CONVICTED", 0), decided) if decided >= MIN_DECIDED else None,
            "convicted": by.get("CONVICTED", 0),
            "decided": decided,
            "stages": sorted(({"stage": k.title(), "n": n} for k, n in by.items() if k), key=lambda x: -x["n"])[:8],
        }
    return None


def _victims(con: sqlite3.Connection, fir_id: str) -> list[dict]:
    """The FIR's victims, one row each (the victims table, matched to the FIR's counts)."""
    try:
        rows = con.execute("SELECT victim_id, gender, age_group, age_band, occupation, relation FROM victims "
                           "WHERE fir_id = ? ORDER BY victim_id LIMIT 25", (fir_id,)).fetchall()
    except sqlite3.OperationalError:            # an older database without the linked table
        return []
    sex = {"M": "Male", "F": "Female"}
    return [{"id": v["victim_id"], "sex": sex.get(v["gender"], v["gender"]), "age_group": v["age_group"],
             "age_band": v["age_band"], "occupation": v["occupation"], "relation": v["relation"]} for v in rows]


def _other_firs(con: sqlite3.Connection, r: sqlite3.Row) -> dict | None:
    """Other FIRs that name the same accused id (indexed): the accused's record in brief."""
    aid = (r["Accused_ID"] or "").strip()
    if not aid:
        return None
    rows = con.execute(
        "SELECT fir_id, date, district_norm, crime_type, FIR_Stage FROM FIRs WHERE Accused_ID = ? "
        "AND fir_id <> ? AND date <= ? ORDER BY date DESC LIMIT 25",
        (aid, r["fir_id"], date.today().isoformat())).fetchall()
    if not rows:
        return {"accused_id": aid, "count": 0, "firs": []}
    return {"accused_id": aid, "count": len(rows),
            "districts": sorted({x["district_norm"] for x in rows if x["district_norm"]}),
            "firs": [{"fir_id": x["fir_id"], "date": x["date"], "district": x["district_norm"],
                      "crime": x["crime_type"], "stage": " ".join(str(x["FIR_Stage"] or "").replace("_", " ").split()).title()} for x in rows[:8]]}


# ── Brain records ────────────────────────────────────────────────────────────
# The Brain graph is drawn from a smaller curated dataset (intelligent.db) whose records are
# not rows of the register. They open as cases too, as "B-<id>": the same timeline, built from
# the same kind of fields, with cases like it and the accused's other records drawn from that
# dataset. They carry no per-victim rows, only the count.
import os
INTEL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "intelligent.db")
BRAIN_PREFIX = "B-"


def _intel() -> sqlite3.Connection | None:
    if not os.path.exists(INTEL_DB):
        return None
    con = sqlite3.connect(f"file:{INTEL_DB}?immutable=1", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _brain_row(r: sqlite3.Row) -> dict:
    """An intelligent.db row in the register's shape, so build() can read it."""
    try:
        reg = f"{int(r['FIR_YEAR']):04d}-{int(r['FIR_MONTH']):02d}-{int(r['FIR_Day']):02d}"
    except (TypeError, ValueError):
        reg = ""
    return {
        "fir_id": f"{BRAIN_PREFIX}{r['id']}", "CrimeNo": None, "date": reg, "zone": r["UnitName"],
        "District_Name": r["District_Name"], "district_norm": r["District_Name"], "UnitName": r["UnitName"],
        "station": r["UnitName"], "FIR_Type": None, "FIR_Stage": r["FIR_Stage"], "status": None,
        "CrimeGroup_Name": r["CrimeGroup_Name"], "CrimeHead_Name": r["CrimeHead_Name"], "crime_type": r["CrimeGroup_Name"],
        "ActSection": None, "Place_of_Offence": r["Place_of_Offence"], "Village_Area_Name": None, "Beat_Name": None,
        "IOName": None, "VICTIM_COUNT": r["VICTIM_COUNT"], "Male": None, "Female": None, "Boy": None, "Girl": None,
        "Accused_Count": r["Accused_Count"], "Arrested_Count_No_": r["Arrested_Count_No_"],
        "Accused_ChargeSheeted_Count": r["Accused_ChargeSheeted_Count"], "Conviction_Count": r["Conviction_Count"],
        "Accused_ID": r["Accused_ID"], "MO_Details": r["MO_Details"], "UPI_ID": r["UPI_ID"],
        "is_synthetic_row": int(r["is_synthetic_row"] or 0),
        "_vehicle": r["Vehicle_Reg_No"], "_ip": r["IP_Address"],
    }


def _brain_similar(con: sqlite3.Connection, r: dict) -> dict | None:
    """How records with the same crime group ended: the station, else the district, else all."""
    group = r["CrimeGroup_Name"]
    if not group:
        return None
    rid = int(r["fir_id"][len(BRAIN_PREFIX):])
    for scope, clause, val in (("station", "UnitName = ?", r["UnitName"]), ("district", "District_Name = ?", r["District_Name"]),
                               ("state", None, None)):
        where, args = ["CrimeGroup_Name = ?", "id <> ?"], [group, rid]
        if clause:
            where.insert(0, clause)
            args.insert(0, val)
        rows = con.execute("SELECT UPPER(TRIM(FIR_Stage)) AS st, COUNT(*) AS n FROM FIRs WHERE "
                           + " AND ".join(where) + " GROUP BY 1", args).fetchall()
        total = sum(x["n"] for x in rows)
        if total < MIN_SIMILAR and scope != "state":
            continue
        by = _by_stage(rows)
        open_inv = sum(by.get(k, 0) for k in ("UNDER INVESTIGATION", "TRANSFERRED - UNDER INVESTIGATION", "TRACED"))
        reached_court = sum(n for k, n in by.items() if _STAGES.get(k, ("", None))[0] == "court")
        decided = by.get("CONVICTED", 0) + by.get("DIS/ACQ", 0)
        pct = lambda n, d: round(100 * n / d) if d else None   # noqa: E731
        return {"scope": scope, "where": {"station": r["UnitName"], "district": r["District_Name"], "state": "the Brain dataset"}[scope],
                "cases": total, "crime_head": _crime_label(group, None),
                "still_under_investigation": pct(open_inv, total), "reached_court": pct(reached_court, total),
                "undetected": pct(_undetected(by), total),
                "convicted_of_decided": pct(by.get("CONVICTED", 0), decided) if decided >= MIN_DECIDED else None,
                "convicted": by.get("CONVICTED", 0), "decided": decided,
                "stages": sorted(({"stage": k.title(), "n": n} for k, n in by.items() if k), key=lambda x: -x["n"])[:8]}
    return None


def _brain_others(con: sqlite3.Connection, r: dict) -> dict | None:
    aid = (r["Accused_ID"] or "").strip()
    if not aid:
        return None
    rid = int(r["fir_id"][len(BRAIN_PREFIX):])
    rows = con.execute("SELECT id, FIR_YEAR, FIR_MONTH, FIR_Day, District_Name, CrimeGroup_Name, FIR_Stage FROM FIRs "
                       "WHERE Accused_ID = ? AND id <> ? ORDER BY FIR_YEAR DESC, FIR_MONTH DESC LIMIT 25", (aid, rid)).fetchall()
    def day(x):
        try:
            return f"{int(x['FIR_YEAR']):04d}-{int(x['FIR_MONTH']):02d}-{int(x['FIR_Day']):02d}"
        except (TypeError, ValueError):
            return ""
    return {"accused_id": aid, "count": len(rows), "districts": sorted({x["District_Name"] for x in rows if x["District_Name"]}),
            "firs": [{"fir_id": f"{BRAIN_PREFIX}{x['id']}", "date": day(x), "district": x["District_Name"],
                      "crime": _crime_label(x["CrimeGroup_Name"], None), "stage": (x["FIR_Stage"] or "").title()} for x in rows[:8]]}


def brain_timeline(case_id: str) -> dict | None:
    try:
        rid = int(str(case_id)[len(BRAIN_PREFIX):])
    except ValueError:
        return None
    con = _intel()
    if con is None:
        return None
    try:
        row = con.execute("SELECT * FROM FIRs WHERE id = ?", (rid,)).fetchone()
        if row is None:
            return None
        r = _brain_row(row)
        d = build(con, r, brain=True)
        d["source"] = "brain"
        d["keys"] = {k: v for k, v in (("vehicle", r["_vehicle"]), ("upi", r["UPI_ID"]), ("ip", r["_ip"])) if v}
        d["recorded"] = ("A record of the Brain's curated dataset, not a row of the FIR register. Only the "
                         "registration is dated; arrests, charge-sheets and verdicts are counts.")
        d["recorded_kn"] = ("ಇದು ಬ್ರೈನ್‌ನ ಆಯ್ದ ದತ್ತಾಂಶದ ದಾಖಲೆ, FIR ರಿಜಿಸ್ಟರ್‌ನ ಸಾಲಲ್ಲ. ದಾಖಲಾತಿಗೆ ಮಾತ್ರ ದಿನಾಂಕ ಇದೆ; "
                            "ಬಂಧನ, ದೋಷಾರೋಪ ಪಟ್ಟಿ ಮತ್ತು ತೀರ್ಪುಗಳು ಎಣಿಕೆಗಳು.")
        return d
    finally:
        con.close()


def timeline(fir: str, station: str | None = None) -> dict | None:
    if str(fir).upper().startswith(BRAIN_PREFIX) and str(fir)[len(BRAIN_PREFIX):].isdigit():
        return brain_timeline(fir)
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        r = find(con, fir, station)
        if r is None:
            return None
        return build(con, r)
    finally:
        con.close()


def build(con: sqlite3.Connection, r, brain: bool = False) -> dict:
    today = date.today()
    reg = str(r["date"] or "")[:10]
    try:
        age = (today - date.fromisoformat(reg)).days
    except ValueError:
        age = None
    stage_raw = _stage(r["FIR_Stage"] or r["status"])
    reached, ended = _STAGES.get(stage_raw, ("investigation", None))
    accused, arrested = _int(r["Accused_Count"]), _int(r["Arrested_Count_No_"])
    charged, convicted = _int(r["Accused_ChargeSheeted_Count"]), _int(r["Conviction_Count"])
    victims = _int(r["VICTIM_COUNT"])
    open_inv = reached == "investigation" and ended is None
    in_court = reached == "court"

    station = r["station"] or r["UnitName"]
    district = r["district_norm"] or r["District_Name"]
    ended_kn = _ENDED_KN.get(ended, ended) if ended else None
    # the 60- and 90-day marks as dates, for the clock on the page and the charge-sheet step
    try:
        d0 = date.fromisoformat(reg)
        mark60, mark90 = (d0 + timedelta(days=LIMIT_SHORT)).isoformat(), (d0 + timedelta(days=LIMIT_LONG)).isoformat()
    except ValueError:
        mark60 = mark90 = None

    # Every line in English and Kannada (title_kn, detail_kn): the page shows the reader's language.
    steps = []

    def step(key, title, title_kn, state, detail, detail_kn, **extra):
        steps.append({"key": key, "title": title, "title_kn": title_kn, "state": state,
                      "detail": detail, "detail_kn": detail_kn, **extra})

    step("registered", "FIR registered", "FIR ದಾಖಲಾಗಿದೆ", "done",
         f"At {station}, {district}." + (f" {r['FIR_Type']}." if r["FIR_Type"] else ""),
         f"{station}, {district} ನಲ್ಲಿ." + (f" {r['FIR_Type']}." if r["FIR_Type"] else ""), date=reg)
    clock = None
    if open_inv:
        en = kn = None
        if age is not None:
            if age < LIMIT_SHORT:
                en = f"Day {age}. The 60-day mark is in {LIMIT_SHORT - age} days, the 90-day mark in {LIMIT_LONG - age}."
                kn = f"{age}ನೇ ದಿನ. 60 ದಿನಗಳ ಮಿತಿಗೆ ಇನ್ನೂ {LIMIT_SHORT - age} ದಿನ, 90 ದಿನಗಳ ಮಿತಿಗೆ {LIMIT_LONG - age} ದಿನ."
            elif age < LIMIT_LONG:
                en = f"Day {age}. Past the 60-day mark; the 90-day mark is in {LIMIT_LONG - age} days."
                kn = f"{age}ನೇ ದಿನ. 60 ದಿನಗಳ ಮಿತಿ ದಾಟಿದೆ; 90 ದಿನಗಳ ಮಿತಿಗೆ ಇನ್ನೂ {LIMIT_LONG - age} ದಿನ."
            else:
                en = f"Day {age}. Past both the 60- and 90-day marks."
                kn = f"{age}ನೇ ದಿನ. 60 ಮತ್ತು 90 ದಿನಗಳ ಎರಡೂ ಮಿತಿಗಳು ದಾಟಿವೆ."
            clock = {"day": age, "short": LIMIT_SHORT, "long": LIMIT_LONG, "short_date": mark60, "long_date": mark90}
        step("investigation", "Under investigation", "ತನಿಖೆಯಲ್ಲಿದೆ", "current", en or "Open.", kn or "ತೆರೆದಿದೆ.",
             days_open=age,
             note="BNSS s.187(3): if the investigation is not finished in 60 days (90 for the gravest offences), "
                  "an accused in custody gets bail by default.",
             note_kn="BNSS ಸೆ.187(3): 60 ದಿನಗಳಲ್ಲಿ (ಅತಿ ಗಂಭೀರ ಅಪರಾಧಗಳಿಗೆ 90 ದಿನ) ತನಿಖೆ ಮುಗಿಯದಿದ್ದರೆ, "
                     "ಬಂಧನದಲ್ಲಿರುವ ಆರೋಪಿಗೆ ಡೀಫಾಲ್ಟ್ ಜಾಮೀನು ಸಿಗುತ್ತದೆ.")
    else:
        closed_here = reached == "investigation" and ended
        step("investigation", "Investigation", "ತನಿಖೆ", "done",
             f"{ended}." if closed_here else "Completed.", f"{ended_kn}." if closed_here else "ಪೂರ್ಣಗೊಂಡಿದೆ.",
             date_missing=True)
    if accused:
        step("arrest", "Arrests", "ಬಂಧನಗಳು", "done" if arrested else ("current" if open_inv else "none"),
             f"{arrested} of {accused} accused arrested.", f"{accused} ಆರೋಪಿಗಳಲ್ಲಿ {arrested} ಬಂಧಿತರು.",
             date_missing=bool(arrested))
    else:
        step("arrest", "Arrests", "ಬಂಧನಗಳು", "none",
             "No accused named yet." if open_inv else "No accused named in the FIR.",
             "ಇನ್ನೂ ಯಾವುದೇ ಆರೋಪಿಯನ್ನು ಹೆಸರಿಸಿಲ್ಲ." if open_inv else "FIR ನಲ್ಲಿ ಯಾವುದೇ ಆರೋಪಿಯನ್ನು ಹೆಸರಿಸಿಲ್ಲ.")
    if charged or in_court:
        step("chargesheet", "Charge-sheet filed", "ದೋಷಾರೋಪ ಪಟ್ಟಿ ಸಲ್ಲಿಸಲಾಗಿದೆ", "done",
             f"{charged} of {accused or charged} accused charge-sheeted." if charged else "Filed.",
             f"{accused or charged} ಆರೋಪಿಗಳಲ್ಲಿ {charged} ವಿರುದ್ಧ ದೋಷಾರೋಪ ಪಟ್ಟಿ." if charged else "ಸಲ್ಲಿಸಲಾಗಿದೆ.",
             date_missing=True)
    elif open_inv:
        due = f" Day 60 falls on {_nice(mark60)}, day 90 on {_nice(mark90)}." if mark60 else ""
        due_kn = f" 60ನೇ ದಿನ {_nice(mark60, True)}, 90ನೇ ದಿನ {_nice(mark90, True)}." if mark60 else ""
        step("chargesheet", "Charge-sheet", "ದೋಷಾರೋಪ ಪಟ್ಟಿ", "pending", "Not filed yet." + due, "ಇನ್ನೂ ಸಲ್ಲಿಸಿಲ್ಲ." + due_kn)
    else:
        step("chargesheet", "Charge-sheet", "ದೋಷಾರೋಪ ಪಟ್ಟಿ", "none", "Not filed.", "ಸಲ್ಲಿಸಿಲ್ಲ.")
    if in_court:
        if ended == "Convicted":
            det, det_kn = (f"{convicted} convicted." if convicted else ""), (f"{convicted} ಮಂದಿಗೆ ಶಿಕ್ಷೆ." if convicted else "")
        elif not ended:
            det, det_kn = "Before the court; no verdict recorded yet.", "ನ್ಯಾಯಾಲಯದಲ್ಲಿದೆ; ಇನ್ನೂ ತೀರ್ಪು ದಾಖಲಾಗಿಲ್ಲ."
        else:
            det = det_kn = ""
        step("court", ended or "Pending trial", ended_kn or "ವಿಚಾರಣೆ ಬಾಕಿ", "done" if ended else "current",
             det, det_kn, date_missing=bool(ended))
    else:
        step("court", "Court", "ನ್ಯಾಯಾಲಯ", "pending" if open_inv else "none", "Not reached.", "ತಲುಪಿಲ್ಲ.")

    sections = _sections(r["ActSection"])
    where = r["Place_of_Offence"] or r["Village_Area_Name"] or r["Beat_Name"]
    head = _crime_label(r["CrimeGroup_Name"], r["CrimeHead_Name"] or r["crime_type"])
    secs = ", ".join(sections[:3])
    bits = [f"{head} registered at {station} on {_nice(reg)}" + (f" under {secs}" if sections else "") + "."]
    bits_kn = [f"{_crime_kn(head)}: {station} ನಲ್ಲಿ {_nice(reg, True)} ರಂದು" + (f" {secs} ಅಡಿ" if sections else "") + " ದಾಖಲಾಗಿದೆ."]
    if accused:
        bits.append(f"{accused} accused named; {arrested} arrested, {charged} charge-sheeted"
                    + (f", {convicted} convicted" if convicted else "") + ".")
        bits_kn.append(f"{accused} ಆರೋಪಿಗಳನ್ನು ಹೆಸರಿಸಲಾಗಿದೆ; {arrested} ಬಂಧಿತರು, {charged} ವಿರುದ್ಧ ದೋಷಾರೋಪ ಪಟ್ಟಿ"
                       + (f", {convicted} ಮಂದಿಗೆ ಶಿಕ್ಷೆ" if convicted else "") + ".")
    else:
        bits.append("No accused named in the FIR.")
        bits_kn.append("FIR ನಲ್ಲಿ ಯಾವುದೇ ಆರೋಪಿಯನ್ನು ಹೆಸರಿಸಿಲ್ಲ.")
    if victims:
        bits.append(f"{victims} {'victim' if victims == 1 else 'victims'} recorded.")
        bits_kn.append(f"{victims} ಸಂತ್ರಸ್ತರು ದಾಖಲಾಗಿದ್ದಾರೆ.")
    if open_inv:
        bits.append(f"Still under investigation, day {age}." if age is not None else "Still under investigation.")
        bits_kn.append(f"ಇನ್ನೂ ತನಿಖೆಯಲ್ಲಿದೆ, {age}ನೇ ದಿನ." if age is not None else "ಇನ್ನೂ ತನಿಖೆಯಲ್ಲಿದೆ.")
    elif ended:
        bits.append(f"{ended}.")
        bits_kn.append(f"{ended_kn}.")
    elif in_court:
        bits.append("Pending trial.")
        bits_kn.append("ವಿಚಾರಣೆ ಬಾಕಿ.")

    return {
        "fir_id": r["fir_id"], "crime_no": r["CrimeNo"], "registered": reg, "zone": r["zone"],
        "station": station, "district": district,
        "crime_group": r["CrimeGroup_Name"], "crime_head": head, "sections": sections,
        "place": where, "io": r["IOName"], "stage": " ".join(str(r["FIR_Stage"] or r["status"] or "").replace("_", " ").split()).title(),
        "counts": {"accused": accused, "arrested": arrested, "chargesheeted": charged,
                   "convicted": convicted, "victims": victims,
                   "victims_by": {"men": _int(r["Male"]), "women": _int(r["Female"]),
                                  "boys": _int(r["Boy"]), "girls": _int(r["Girl"])}},
        "mo": r["MO_Details"],
        "upi": (r["UPI_ID"] or "").strip() or None,
        "victims": [] if brain else _victims(con, r["fir_id"]),
        "summary": " ".join(bits),
        "summary_kn": " ".join(bits_kn),
        "steps": steps,
        "clock": clock,
        "similar": _brain_similar(con, r) if brain else _similar(con, r),
        "same_accused": _brain_others(con, r) if brain else _other_firs(con, r),
        "demonstration": bool(r["is_synthetic_row"]),
        "recorded": "Only the registration is dated in the register. Arrests, charge-sheets and "
                    "verdicts are recorded as counts, so their dates are shown as not recorded.",
        "recorded_kn": "ರಿಜಿಸ್ಟರ್‌ನಲ್ಲಿ ದಾಖಲಾತಿಯ ದಿನಾಂಕ ಮಾತ್ರ ಇದೆ. ಬಂಧನ, ದೋಷಾರೋಪ ಪಟ್ಟಿ ಮತ್ತು ತೀರ್ಪುಗಳು "
                       "ಎಣಿಕೆಗಳಾಗಿ ಮಾತ್ರ ದಾಖಲಾಗಿವೆ, ಆದ್ದರಿಂದ ಅವುಗಳ ದಿನಾಂಕ ತೋರಿಸಲಾಗಿಲ್ಲ.",
    }
