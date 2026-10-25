"""
Antar - questions about fields the FIR register does not hold
=============================================================
Some questions are answerable in a real police database but not in this one, because the
column does not exist. They used to be routed to the nearest template by keyword, so
"the delay between the incident date and registration in Bagalkot" was answered with the
crime-type breakdown for Bagalkot, and "counts by case category (FIR, UDR, Zero FIR)" with
a list of ten FIRs. Neither said the question had not been answered.

Each gap here is checked against the register's actual columns (the FIRs table holds one
date, the registration date; its FIR_Type is Heinous / Non Heinous). The answer says what is
missing, what IS recorded, and the nearest question that can be answered.

One gap is answered rather than refused: data quality (missing coordinates, missing act and
section) is a count over columns that do exist.
"""
from __future__ import annotations

import re

_INCIDENT = re.compile(r"\b(incident|occurrence|offen[cs]e)\s+(date|time)|\bdate of (incident|occurrence|offen[cs]e)\b"
                       r"|\b(delay|gap|time|lag)\b[^.?!]{0,40}\b(incident|occurrence|offen[cs]e)\b[^.?!]{0,40}\bregist", re.I)
_CATEGORY = re.compile(r"\b(udr|zero fir|unnatural death|case categor\w*)\b", re.I)
_QUALITY = re.compile(r"\b(data quality|missing (?:gps |)coordinates?|missing (?:lat|long)\w*|unmapped sections?|"
                      r"missing (?:act|sections?)|implausible|incomplete records?)\b", re.I)


def _quality(zones: list[str]) -> tuple[str, list[str]]:
    """Counted, not refused: FIRs with no coordinates, and with no act or section recorded."""
    from app.core.db_path import DB_PATH, registry_connect
    from app.services.zcql_repo import resolve_zones
    zs = resolve_zones(zones or [])
    from datetime import date
    # the same cut-off as every other answer: rows dated after today are not on record yet
    where, args = " WHERE date <= ?", [date.today().isoformat()]
    if zs:
        where += " AND TRIM(UPPER(zone)) IN (" + ",".join("?" * len(zs)) + ")"
        args += [z.strip().upper() for z in zs]
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        n, no_xy, no_act, no_io = con.execute(
            "SELECT COUNT(*), "
            "SUM(CASE WHEN COALESCE(Latitude, location_lat) IS NULL OR COALESCE(Latitude, location_lat) = 0 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN ActSection IS NULL OR TRIM(ActSection) = '' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN IOName IS NULL OR TRIM(IOName) = '' THEN 1 ELSE 0 END) FROM FIRs" + where, args).fetchone()
    finally:
        con.close()
    place = ", ".join(zs) if zs else "Karnataka"
    pct = lambda k: f"{(100 * (k or 0) / n):.1f}%" if n else "0%"   # noqa: E731
    lines = [f"Data quality of the {n:,} FIRs on record in {place}:",
             f"• No coordinates: {no_xy or 0:,} ({pct(no_xy)}) - these cannot appear on the map or in beat hotspots.",
             f"• No act or section recorded: {no_act or 0:,} ({pct(no_act)}).",
             f"• No investigating officer recorded: {no_io or 0:,} ({pct(no_io)}).",
             "Counted over the register's own columns. Implausible values (a wrong section for the crime, a date typed wrong) are not checked here."]
    return "\n".join(lines), [f"Top beats in {zs[0]}" if zs else "Which districts have the most crime?"]


def check(user_text: str, zones: list[str] | None = None, lang: str = "en") -> tuple[str, list[str], str] | None:
    """(answer, follow-ups, reason) when the question is about a field the register lacks."""
    t = user_text or ""
    place = f" in {zones[0]}" if zones else ""
    if _QUALITY.search(t):
        msg, again = _quality(zones or [])
        return msg, again, "Data-quality counts over the register's columns."
    if _INCIDENT.search(t):
        return ("The register records one date per FIR, the date it was registered. It holds no incident (offence) date, "
                "so the delay between an incident and its registration cannot be measured from it.\n"
                "What it can show: how long registered cases have stayed open, and their stage.",
                [f"Cases under investigation for more than 90 days{place}", f"Case stages{place}"],
                "Not held: incident date.")
    if _CATEGORY.search(t):
        return ("The register has no case-category field: UDR (unnatural death) reports and Zero FIRs are not marked. "
                "Each FIR is typed only as Heinous or Non Heinous, and by crime group.\n"
                "What it can show: the split by law (IPC/BNS against special and local laws), and by crime type.",
                [f"IPC/BNS vs SLL split{place}", f"Breakdown of crimes by type{place}"],
                "Not held: case category (FIR / UDR / Zero FIR).")
    return None
