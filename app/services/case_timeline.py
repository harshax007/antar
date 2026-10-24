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
from datetime import date

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
         "Arrested_Count_No_, Accused_ChargeSheeted_Count, Conviction_Count, Accused_ID, MO_Details, "
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
}
_STEPS = ("registered", "investigation", "arrest", "chargesheet", "court")


def _int(v) -> int:
    try:
        return max(0, int(v or 0))
    except (TypeError, ValueError):
        return 0


def _nice(iso: str | None) -> str:
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso or "")
    return f"{d.day} {d.strftime('%b %Y')}"          # %-d is not portable to Windows


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
        by = {x["st"] or "": x["n"] for x in rows}
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
            "undetected": pct(by.get("UNDETECTED", 0), total),
            "convicted_of_decided": pct(by.get("CONVICTED", 0), decided) if decided >= MIN_DECIDED else None,
            "convicted": by.get("CONVICTED", 0),
            "decided": decided,
            "stages": sorted(({"stage": k.title(), "n": n} for k, n in by.items() if k), key=lambda x: -x["n"])[:8],
        }
    return None


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
                      "crime": x["crime_type"], "stage": (x["FIR_Stage"] or "").title()} for x in rows[:8]]}


def timeline(fir: str, station: str | None = None) -> dict | None:
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        r = find(con, fir, station)
        if r is None:
            return None
        return build(con, r)
    finally:
        con.close()


def build(con: sqlite3.Connection, r: sqlite3.Row) -> dict:
    today = date.today()
    reg = str(r["date"] or "")[:10]
    try:
        age = (today - date.fromisoformat(reg)).days
    except ValueError:
        age = None
    stage_raw = " ".join(str(r["FIR_Stage"] or r["status"] or "").upper().replace("_", " ").split())
    reached, ended = _STAGES.get(stage_raw, ("investigation", None))
    accused, arrested = _int(r["Accused_Count"]), _int(r["Arrested_Count_No_"])
    charged, convicted = _int(r["Accused_ChargeSheeted_Count"]), _int(r["Conviction_Count"])
    victims = _int(r["VICTIM_COUNT"])
    open_inv = reached == "investigation" and ended is None
    in_court = reached == "court"

    steps = []
    steps.append({"key": "registered", "title": "FIR registered", "state": "done", "date": reg,
                  "detail": f"At {r['station'] or r['UnitName']}, {r['district_norm'] or r['District_Name']}."
                            + (f" {r['FIR_Type']}." if r["FIR_Type"] else "")})
    if open_inv:
        clock = None
        if age is not None:
            if age < LIMIT_SHORT:
                clock = f"Day {age}. The 60-day mark is in {LIMIT_SHORT - age} days, the 90-day mark in {LIMIT_LONG - age}."
            elif age < LIMIT_LONG:
                clock = f"Day {age}. Past the 60-day mark; the 90-day mark is in {LIMIT_LONG - age} days."
            else:
                clock = f"Day {age}. Past both the 60- and 90-day marks."
        steps.append({"key": "investigation", "title": "Under investigation", "state": "current",
                      "detail": clock or "Open.", "days_open": age,
                      "note": "BNSS s.187(3): an accused in custody gets default bail if the investigation "
                              "is not complete in 60 days, or 90 for the gravest offences."})
    else:
        steps.append({"key": "investigation", "title": "Investigation", "state": "done",
                      "detail": f"{ended}." if (reached == "investigation" and ended) else "Completed.",
                      "date_missing": True})
    if accused:
        steps.append({"key": "arrest", "title": "Arrests", "state": "done" if arrested else ("current" if open_inv else "none"),
                      "detail": f"{arrested} of {accused} accused arrested.", "date_missing": bool(arrested)})
    else:
        steps.append({"key": "arrest", "title": "Arrests", "state": "none",
                      "detail": "No accused named in the FIR." if not open_inv else "No accused named yet."})
    if charged or in_court:
        steps.append({"key": "chargesheet", "title": "Charge-sheet filed", "state": "done",
                      "detail": f"{charged} of {accused or charged} accused charge-sheeted." if charged else "Filed.",
                      "date_missing": True})
    else:
        steps.append({"key": "chargesheet", "title": "Charge-sheet", "state": "pending" if open_inv else "none",
                      "detail": "Not filed yet." if open_inv else "Not filed."})
    if in_court:
        steps.append({"key": "court", "title": ended or "Pending trial", "state": "done" if ended else "current",
                      "detail": (f"{convicted} convicted." if convicted else "") if ended == "Convicted"
                                else ("Before the court; no verdict recorded yet." if not ended else ""),
                      "date_missing": bool(ended)})
    else:
        steps.append({"key": "court", "title": "Court", "state": "pending" if open_inv else "none",
                      "detail": "Not reached."})

    sections = _sections(r["ActSection"])
    where = r["Place_of_Offence"] or r["Village_Area_Name"] or r["Beat_Name"]
    head = _crime_label(r["CrimeGroup_Name"], r["CrimeHead_Name"] or r["crime_type"])
    bits = [f"{head} registered at {r['station'] or r['UnitName']} on {_nice(reg)}"
            + (f" under {', '.join(sections[:3])}" if sections else "") + "."]
    if accused:
        bits.append(f"{accused} accused named; {arrested} arrested, {charged} charge-sheeted"
                    + (f", {convicted} convicted" if convicted else "") + ".")
    else:
        bits.append("No accused named in the FIR.")
    if victims:
        bits.append(f"{victims} {'victim' if victims == 1 else 'victims'} recorded.")
    if open_inv:
        bits.append(f"Still under investigation, day {age}." if age is not None else "Still under investigation.")
    elif ended:
        bits.append(f"{ended}.")
    elif in_court:
        bits.append("Pending trial.")

    return {
        "fir_id": r["fir_id"], "crime_no": r["CrimeNo"], "registered": reg, "zone": r["zone"],
        "station": r["station"] or r["UnitName"], "district": r["district_norm"] or r["District_Name"],
        "crime_group": r["CrimeGroup_Name"], "crime_head": head, "sections": sections,
        "place": where, "io": r["IOName"], "stage": (r["FIR_Stage"] or r["status"] or "").title(),
        "counts": {"accused": accused, "arrested": arrested, "chargesheeted": charged,
                   "convicted": convicted, "victims": victims,
                   "victims_by": {"men": _int(r["Male"]), "women": _int(r["Female"]),
                                  "boys": _int(r["Boy"]), "girls": _int(r["Girl"])}},
        "mo": r["MO_Details"],
        "summary": " ".join(bits),
        "steps": steps,
        "similar": _similar(con, r),
        "same_accused": _other_firs(con, r),
        "demonstration": bool(r["is_synthetic_row"]),
        "recorded": "Only the registration is dated in the register. Arrests, charge-sheets and "
                    "verdicts are recorded as counts, so their dates are shown as not recorded.",
    }
