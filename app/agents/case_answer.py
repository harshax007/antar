"""
Antar - one FIR, asked about in chat
====================================
"Status of FIR C00026", "show FIR C00001", "what happened in K1026329": a question about one
case is answered from that case (app/services/case_timeline.py) - its summary, where it is
now, and the steps - with a button to the full case timeline. Before this, the id went
unrecognised and the question fell through to a statewide count (every case by stage) or a
list of ten unrelated FIRs.

Two FIR ids in one question are left to T29 ("what links two FIRs").

A crime number (18 digits, 100011245202300001) is also one case, but it repeats across
stations, and some register ids are carried by two rows; every match is named and the first
is answered, rather than one being picked silently. What an officer asks about a case that
the register does not hold (witness statements, CDRs, seized property, bank accounts, the
complainant's name) is named as not held, not skipped.
"""
from __future__ import annotations

import re
import sqlite3

from app.services import case_timeline

# every shape of fir_id in the register (sampled), the official FIR-YYYY-... form, and the
# 18-digit crime number
_FIR = re.compile(r"\b(K\d{7}|C\d{5,8}|SYN-[a-f0-9]{12}|SYN-20\d\d-\d{3,8}|(?:BG|HIST|FWD)-20\d\d-\d{3,8}"
                  r"|FIR-20\d\d-[\w-]{4,40}|\d{18})\b", re.I)

# Asked about one case, not held in the FIR register: said so, by name.
_NOT_HELD = (
    (r"\bwitness", "witness statements"),
    (r"\b(cdr|call detail|call records?|tower dump)", "call detail records (CDR)"),
    (r"\b(locker|seized|seizure|property room|malkhana)", "seized-property and locker records"),
    (r"\b(bank account|account numbers?|transactions?|money trail)", "bank accounts and transactions"),
    (r"\bcomplainant", "the complainant's name, address and occupation"),
    (r"\b(court|hearing|judge)\b", "the court and hearing dates"),
    (r"\b(arrest|surrender)\w*\b.*\bdates?\b|\bdates?\b.*\b(arrest|surrender)", "arrest and surrender dates"),
    (r"\b(forensic|fsl|post[- ]?mortem|autopsy)", "forensic and post-mortem reports"),
    (r"\b(judgment|judgement|verdict text|court order)", "judgments and court orders"),
    (r"\b(case diary|investigation diary|cd entries)", "the case diary"),
)
_SIMILAR = re.compile(r"\b(similar|alike|like (?:this|it)|comparable|resembl\w*|same kind)\b", re.I)


def _nearest(fir_id: str, n: int = 5) -> tuple[list[dict], str]:
    """The FIRs of the same crime type at the same station (else district), nearest in date.

    A similarity of record - same crime, same place, close in time - and nothing more: it is
    not a link between the cases, and the answer says so."""
    from datetime import date
    from app.core.db_path import DB_PATH, registry_connect
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    today = date.today().isoformat()
    try:
        r = con.execute("SELECT crime_type, station, district_norm, date, Beat_Name, MO_Details, CrimeNo FROM FIRs WHERE fir_id = ?",
                        (fir_id,)).fetchone()
        if not r or not r["crime_type"]:
            return [], ""
        for scope, col, val in (("station", "station", r["station"]), ("district", "district_norm", r["district_norm"])):
            if not val:
                continue
            rows = con.execute(
                f"SELECT fir_id, CrimeNo, date, station, Beat_Name, FIR_Stage, MO_Details FROM FIRs "
                f"WHERE {col} = ? AND crime_type = ? AND fir_id <> ? AND date <= ? "
                f"ORDER BY ABS(julianday(date) - julianday(?)) LIMIT ?",
                (val, r["crime_type"], fir_id, today, r["date"], 4 * n)).fetchall()
            # one line per case: a crime number carried by two register rows, or this case's own, is not another case
            seen, kept = {str(r["CrimeNo"] or fir_id)}, []
            for x in rows:
                k = str(x["CrimeNo"] or x["fir_id"])
                if k not in seen:
                    seen.add(k); kept.append(x)
            rows = kept[:n]
            if rows:
                out = []
                for x in rows:
                    same = [w for w, a, b in (("beat", x["Beat_Name"], r["Beat_Name"]), ("MO", x["MO_Details"], r["MO_Details"]))
                            if a and b and str(a).strip().upper() == str(b).strip().upper()]
                    out.append({"fir_id": x["fir_id"], "crime_no": x["CrimeNo"], "date": x["date"], "station": x["station"],
                                "stage": " ".join(str(x["FIR_Stage"] or "").replace("_", " ").split()).title(), "same": same})
                return out, f"same crime type ({str(r['crime_type']).replace('_', ' ').lower()}) at the same {scope}, nearest in date"
        return [], ""
    finally:
        con.close()


def fir_ids(text: str) -> list[str]:
    out = []
    for m in _FIR.finditer(text or ""):
        v = m.group(1)
        v = "SYN-" + v[4:].lower() if re.match(r"(?i)SYN-[a-f0-9]{12}$", v) else v.upper()
        if v not in out:
            out.append(v)
    return out


def wants_case(text: str) -> bool:
    return len(fir_ids(text)) == 1


# "summary of this case", "status of that FIR": one case, but not named here.
_BACK_REF = re.compile(r"\b(this|that|the same|the above|the said)\s+(case|fir)\b", re.I)


def refers_back(text: str) -> bool:
    return not fir_ids(text) and bool(_BACK_REF.search(text or ""))


def fir_from_history(history: list[dict] | None) -> str | None:
    """The FIR the officer last named, from their own questions only: an answer lists ten
    FIRs, and "this case" after a list is not any one of them."""
    for t in reversed(history or []):
        if t.get("role") == "user":
            ids = fir_ids(t.get("text") or "")
            if len(ids) == 1:
                return ids[0]
    return None


def _matches(fir: str) -> list[dict]:
    """Every register row carrying this id, or this crime number."""
    from datetime import date
    from app.core.db_path import DB_PATH, registry_connect
    con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    today = date.today().isoformat()
    cols = case_timeline._COLS
    try:
        rows = con.execute(f"SELECT {cols} FROM FIRs WHERE fir_id = ? AND date <= ? LIMIT 5", (fir, today)).fetchall()
        if not rows and fir.isdigit():
            rows = con.execute(f"SELECT {cols} FROM FIRs WHERE CrimeNo = ? AND date <= ? LIMIT 5", (fir, today)).fetchall()
        return [case_timeline.build(con, r) for r in rows]
    finally:
        con.close()


def answer(text: str, lang: str = "en") -> dict:
    fir = fir_ids(text)[0]
    found = _matches(fir)
    base = {"citations": [], "agent": "query", "llm_answer": False, "params": {"fir_id": fir},
            "suggested_followups": [], "rows": []}
    if not found:
        return {**base, "template_id": "UNRESOLVED",
                "answer": f"No FIR {fir} in the register. Check the id, or search by crime number in Search.",
                "reasoning": [{"step": "route", "detail": f"A question about one FIR ({fir}); it is not in the register."}]}
    # the same need-to-know rule as the case page: below Analyst, cases of one's own posting
    from app.services.zcql_repo import scoped_posting
    posting = scoped_posting()
    if posting:
        mine = [d for d in found
                if posting.strip().upper() in {str(d.get("zone") or "").upper(), str(d.get("district") or "").upper()}]
        if not mine:
            return {**base, "template_id": "UNRESOLVED",
                    "answer": f"FIR {fir} is outside your posting ({posting}).",
                    "reasoning": [{"step": "policy", "detail": "Case rows below Analyst are limited to the officer's posting."}]}
        found = mine
    d = found[0]
    low = (text or "").lower()
    # where the case is: the step it is at, or, once it has closed, the last step it reached
    now = next((s for s in d["steps"] if s["state"] == "current"), None) \
        or next((s for s in reversed(d["steps"]) if s["state"] == "done"), d["steps"][-1])
    lines = []
    if len(found) > 1:
        lines.append(f"{len(found)} FIRs carry {fir}: "
                     + "; ".join(f"{x['fir_id']} at {x['station']}, {x['registered']}" for x in found)
                     + ". The first is shown; open the others from Search.\n")
    lines.append(d["summary"])
    if d.get("demonstration"):
        lines.append("This is a demonstration record, not a registered FIR.")
    lines += ["", f"**Where it is now:** {now['title']}" + (f" — {now['detail']}" if now.get("detail") else "")]
    for s in d["steps"]:
        mark = {"done": "✓", "current": "●", "pending": "○", "none": "–"}.get(s["state"], "·")
        when = f" ({s['date']})" if s.get("date") else (" (date not recorded)" if s.get("date_missing") else "")
        lines.append(f"{mark} {s['title']}{when}: {s.get('detail') or ''}".rstrip(": "))

    c = d["counts"]
    same = d.get("same_accused")
    rec = [f"**Acts and sections:** {', '.join(d['sections']) if d['sections'] else 'none recorded'}"]
    if d.get("crime_no"):
        rec.append(f"**Crime number:** {d['crime_no']} (register id {d['fir_id']})")
    else:
        rec.append(f"**Register id:** {d['fir_id']}")      # no crime number: the id is the only name it has
    if d.get("place"):
        rec.append(f"**Place:** {d['place']}")
    if d.get("io"):
        rec.append(f"**Investigating officer:** {' '.join(str(d['io']).split())}")
    if c.get("accused"):
        rec.append(f"**Accused:** {c['accused']} named, {c['arrested']} arrested, {c['chargesheeted']} charge-sheeted, "
                   f"{c['convicted']} convicted" + (f"; accused id {same['accused_id']}" if same else ""))
    if c.get("victims"):
        vb = c.get("victims_by") or {}
        one = {"men": "man", "women": "woman", "boys": "boy", "girls": "girl"}
        parts = [f"{vb[k]} {one[k] if vb[k] == 1 else k}" for k in ("men", "women", "boys", "girls") if vb.get(k)]
        rec.append(f"**Victims:** {c['victims']}" + (f" ({', '.join(parts)})" if parts else "")
                   + ", recorded by sex and age group; no names or addresses")
    if d.get("mo"):
        rec.append(f"**Modus operandi:** {' '.join(str(d['mo']).split())[:200]}")
    if d.get("upi"):
        rec.append(f"**UPI id:** {d['upi']}")
    lines.append("")
    lines += [f"• {x}" for x in rec]
    if same and same.get("count"):
        lines.append(f"• The same accused id is on {same['count']} other FIR{'s' if same['count'] != 1 else ''}"
                     + (f" ({', '.join(same['districts'])})" if same.get("districts") else "")
                     + ": " + ", ".join(f["fir_id"] for f in same["firs"][:4]) + ".")
    sim = d.get("similar")
    if sim and sim.get("reached_court") is not None:
        lines.append(f"\nOf {sim['cases']:,} other {sim['crime_head']} cases "
                     f"{'across Karnataka' if sim['scope'] == 'state' else 'at ' + str(sim['where'])}, "
                     f"{sim['reached_court']}% reached court and {sim['undetected']}% were closed as undetected"
                     + (f"; {sim['convicted_of_decided']}% of those decided ended in conviction"
                        if sim.get("convicted_of_decided") is not None else "")
                     + ".")
    near = []
    if _SIMILAR.search(low):
        near, how = _nearest(d["fir_id"])
        if near:
            lines.append(f"\n**{len(near)} similar cases** ({how}):")
            lines += [f"{i}. FIR {x['crime_no'] or x['fir_id']} — {x['station']}, {x['date']}"
                      + (f" · {x['stage']}" if x["stage"] else "")
                      + (f" · same {' and '.join(x['same'])}" if x["same"] else "")
                      for i, x in enumerate(near, 1)]
            lines.append("Similar on the record is not a link: no shared accused, vehicle, phone or account is "
                         "claimed. Compare the case files before treating any two as connected.")
        else:
            lines.append("\nNo other FIR of the same crime type is on record at this station or district.")
    not_held = [label for rx, label in _NOT_HELD if re.search(rx, low)]
    if not_held:
        lines.append("\n**Not held in the FIR register:** " + "; ".join(not_held)
                     + ". Only the case file or the investigating officer has these.")

    actions = [{"type": "navigate", "payload": f"/case/{d['fir_id']}", "label": "Open case timeline"}]
    if d.get("upi"):
        actions.append({"type": "navigate", "payload": f"/search?view=money&account={d['upi']}", "label": "Follow the money"})
    rows = [{"fir_id": x["fir_id"], "crime_no": x["crime_no"], "registered": x["registered"], "station": x["station"],
             "district": x["district"], "stage": x["stage"], **{k: v for k, v in x["counts"].items() if k != "victims_by"}}
            for x in found]
    follow = []
    if same and same.get("count"):
        follow.append(f"cases for accused {same['accused_id']}")
    if d.get("crime_group") and d.get("district"):
        follow.append(f"Conviction rate for {str(d['crime_group']).replace('_', ' ').lower()} in {d['district']}")
    return {**base, "template_id": "CASE", "answer": "\n".join(lines), "rows": rows,
            "citations": [{"fir": x["crime_no"] or x["fir_id"], "id": x["fir_id"], "station": x["station"],
                           "date": x["registered"], "section": ", ".join(x["sections"][:3])} for x in found],
            "actions": actions,
            "suggested_followups": follow[:3],
            "reasoning": [{"step": "route", "detail": f"A question about one FIR ({d['fir_id']}): answered from that case."}]
                         + ([{"step": "match", "detail": f"{len(found)} register rows carry {fir}; all are named."}]
                            if len(found) > 1 else [])
                         + [{"step": "recorded", "detail": d["recorded"]}]}
