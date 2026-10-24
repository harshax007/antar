"""
Antar - one FIR, asked about in chat
====================================
"Status of FIR C00026", "show FIR C00001", "what happened in K1026329": a question about one
case is answered from that case (app/services/case_timeline.py) - its summary, where it is
now, and the steps - with a button to the full case timeline. Before this, the id went
unrecognised and the question fell through to a statewide count (every case by stage) or a
list of ten unrelated FIRs.

Two FIR ids in one question are left to T29 ("what links two FIRs").
"""
from __future__ import annotations

import re

from app.services import case_timeline

# every shape of fir_id in the register (sampled), plus the official FIR-YYYY-... form
_FIR = re.compile(r"\b(K\d{7}|C\d{5,8}|SYN-[a-f0-9]{12}|SYN-20\d\d-\d{3,8}|(?:BG|HIST|FWD)-20\d\d-\d{3,8}"
                  r"|FIR-20\d\d-[\w-]{4,40})\b", re.I)


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


def answer(text: str, lang: str = "en") -> dict:
    fir = fir_ids(text)[0]
    d = case_timeline.timeline(fir)
    base = {"citations": [], "agent": "query", "llm_answer": False, "params": {"fir_id": fir},
            "suggested_followups": [], "rows": []}
    if d is None:
        return {**base, "template_id": "UNRESOLVED",
                "answer": f"No FIR {fir} in the register. Check the id, or search by crime number in Search.",
                "reasoning": [{"step": "route", "detail": f"A question about one FIR ({fir}); it is not in the register."}]}
    # the same need-to-know rule as the case page: below Analyst, cases of one's own posting
    from app.services.zcql_repo import scoped_posting
    posting = scoped_posting()
    if posting and posting.strip().upper() not in {str(d.get("zone") or "").upper(), str(d.get("district") or "").upper()}:
        return {**base, "template_id": "UNRESOLVED",
                "answer": f"FIR {fir} is outside your posting ({posting}).",
                "reasoning": [{"step": "policy", "detail": "Case rows below Analyst are limited to the officer's posting."}]}
    # where the case is: the step it is at, or, once it has closed, the last step it reached
    now = next((s for s in d["steps"] if s["state"] == "current"), None)         or next((s for s in reversed(d["steps"]) if s["state"] == "done"), d["steps"][-1])
    lines = [d["summary"], "", f"**Where it is now:** {now['title']}" + (f" — {now['detail']}" if now.get("detail") else "")]
    for s in d["steps"]:
        mark = {"done": "✓", "current": "●", "pending": "○", "none": "–"}.get(s["state"], "·")
        when = f" ({s['date']})" if s.get("date") else ""
        lines.append(f"{mark} {s['title']}{when}: {s.get('detail') or ''}".rstrip(": "))
    sim = d.get("similar")
    if sim and sim.get("reached_court") is not None:
        lines.append(f"\nOf {sim['cases']:,} other {sim['crime_head']} cases "
                     f"{'across Karnataka' if sim['scope'] == 'state' else 'at ' + str(sim['where'])}, "
                     f"{sim['reached_court']}% reached court and {sim['undetected']}% were closed as undetected.")
    actions = [{"type": "navigate", "payload": f"/case/{d['fir_id']}", "label": "Open case timeline"}]
    if d.get("upi"):
        actions.append({"type": "navigate", "payload": f"/money?account={d['upi']}", "label": "Follow the money"})
    row = {"fir_id": d["fir_id"], "crime_no": d["crime_no"], "registered": d["registered"], "station": d["station"],
           "district": d["district"], "stage": d["stage"], **{k: v for k, v in d["counts"].items() if k != "victims_by"}}
    return {**base, "template_id": "CASE", "answer": "\n".join(lines), "rows": [row],
            "citations": [{"fir": d["crime_no"] or d["fir_id"], "id": d["fir_id"], "station": d["station"],
                           "date": d["registered"], "section": ", ".join(d["sections"][:3])}],
            "actions": actions,
            "suggested_followups": [f"What links FIR {d['fir_id']} to other cases?"] if d.get("same_accused", {}) and d["same_accused"].get("count") else [],
            "reasoning": [{"step": "route", "detail": f"A question about one FIR ({d['fir_id']}): answered from that case."},
                          {"step": "recorded", "detail": d["recorded"]}]}
