"""
Antar - "are there any unusual spikes right now?"
=================================================
Answered from the anomaly scan the Predict screen and the alerts use (services/anomaly.scan:
MAD-z against 13 weeks, seasonal residual, Gi* confirmation), for the week ending on the
map's as-of date. It used to find no crime word, and either ask which crime type was meant
or list the newest FIRs in the state.

A place or crime named in the question narrows the list. A flag is a statistical signal to
look at, never a finding; the answer says how far above usual each one is, on what counts.
"""
from __future__ import annotations

import re

_ASK = re.compile(r"\b(spikes?|anomal\w*|unusual|abnormal|surges?|outliers?|sudden (?:rise|jump|increase)|"
                  r"early warnings?|red flags?|alerts?|flagged|out of the ordinary)\b", re.I)
# "alert the SP", "festival spikes" (T30), "spike in 2023" are other questions
_NOT = re.compile(r"\b(deepavali|diwali|dasara|ganesh|festival|holiday|new year|before|during|after)\b|\b(19|20)\d\d\b", re.I)


_KN_ASK = ("ಅಸಾಮಾನ್ಯ", "ಅಸಹಜ", "ಎಚ್ಚರಿಕೆ", "ದಿಢೀರ್ ಏರಿಕೆ")     # unusual, abnormal, alert(s), sudden rise


def wants_spikes(text: str) -> bool:
    t = text or ""
    return bool(_ASK.search(t) or any(k in t for k in _KN_ASK)) and not _NOT.search(t)


def _norm(s) -> str:
    return " ".join(str(s or "").replace("_", " ").split()).upper()


def answer(text: str, ents: dict, lang: str = "en") -> dict:
    from app.services import anomaly
    from app.services.zcql_repo import expand_crime_types, resolve_zones
    rows = [r for r in anomaly.scan() if (r.get("direction") or "up") != "down"]
    cts = {_norm(c) for c in expand_crime_types(ents.get("crime_types") or [])}
    zones = {_norm(z) for z in (resolve_zones(ents.get("zones") or []) or [])} | {_norm(z) for z in ents.get("zones") or []}
    if cts:
        rows = [r for r in rows if _norm(r.get("crime_type")) in cts]
    if zones:
        rows = [r for r in rows if _norm(r.get("zone")) in zones]
    window = (rows[0].get("window") if rows else None) or "this week"
    scope = (" for " + " / ".join(c.title() for c in (ents.get("crime_types") or []))) if cts else ""
    scope += (" in " + ", ".join(ents.get("zones"))) if zones else ""
    kn = lang == "kn"
    if not rows:
        msg = (f"[COMPUTED] {({'this week': 'ಈ ವಾರ', 'last week': 'ಕಳೆದ ವಾರ'}).get(window, window)}: ಯಾವುದೇ ಅಸಾಮಾನ್ಯ ಏರಿಕೆ ಕಂಡುಬಂದಿಲ್ಲ; ಎಲ್ಲವೂ ಹಿಂದಿನ 13 ವಾರಗಳ ಸಾಮಾನ್ಯ ಮಟ್ಟದಲ್ಲಿದೆ." if kn else
               f"[COMPUTED] No unusual rise is flagged{scope} for the {window}: every crime type and area is "
               f"within its usual range against the 13 weeks before.")
        return {"answer": msg, "rows": [], "citations": [], "template_id": "ALERTS", "params": {"n": 0},
                "agent": "query", "suggested_followups": ["Where should I patrol next week?", "most crimes?"],
                "llm_answer": False, "reasoning": [{"step": "anomaly", "detail": f"Scan: 0 flags{scope}."}]}
    window_kn = {"this week": "ಈ ವಾರ", "last week": "ಕಳೆದ ವಾರ", "this month": "ಈ ತಿಂಗಳು"}.get(window, window)
    import re as _re
    from app.agents.answer_writer import _date
    m = _re.fullmatch(r"week ending (\d{4}-\d{2}-\d{2})", str(window))
    if m:                                    # "week ending 2026-10-26" -> "week ending 26 Oct 2026"
        window = f"week ending {_date(m.group(1), False)}"
        window_kn = f"{_date(m.group(1), True)} ಕ್ಕೆ ಕೊನೆಗೊಂಡ ವಾರ"
    lines = [f"[COMPUTED] **{len(rows)}** ಅಸಾಮಾನ್ಯ ಏರಿಕೆಗಳು ಗುರುತಾಗಿವೆ ({window_kn}), ಪ್ರತಿಯೊಂದೂ ತನ್ನ ಹಿಂದಿನ 13 ವಾರಗಳ ವಿರುದ್ಧ:"
             if kn else
             f"[COMPUTED] **{len(rows)}** unusual rise{'s' if len(rows) != 1 else ''} flagged{scope}, {window}, "
             f"each against its own last 13 weeks:"]
    from app.agents.display_names import display_crime
    # In words an officer reads at a glance. The z-score and the "confidence" (a logistic of
    # that same z, not a measured hit rate) used to be printed here; neither tells an officer
    # anything the two counts do not, and "confidence 50%" reads as a coin toss.
    kinds = {"spike": ("a sudden jump", "ಹಠಾತ್ ಏರಿಕೆ"),
             "seasonal_surge": ("more than this time of year usually brings", "ಈ ಕಾಲದ ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು"),
             "hotspot": ("a confirmed hotspot", "ದೃಢಪಟ್ಟ ಹಾಟ್‌ಸ್ಪಾಟ್"),
             "spatial_spike": ("a jump in one place", "ಒಂದೇ ಸ್ಥಳದಲ್ಲಿ ಏರಿಕೆ")}
    for i, r in enumerate(rows[:8], 1):
        ct = display_crime(r.get("crime_type") or "crime", "kn" if kn else "en")
        obs, exp = r.get("observed"), r.get("expected")
        kind = kinds.get(r.get("anomaly_type"), ("a rise", "ಏರಿಕೆ"))[1 if kn else 0]
        usual = f"{exp:g}" if isinstance(exp, (int, float)) else str(exp)
        lines.append(f"{i}. **{r.get('zone')}** ನಲ್ಲಿ **{ct}** — {obs} FIR, ಸಾಮಾನ್ಯವಾಗಿ {usual} ({kind})" if kn else
                     f"{i}. **{ct}** in **{r.get('zone')}** — {obs} FIRs where {usual} is usual ({kind})")
    if len(rows) > 8:
        lines.append(f"…ಇನ್ನೂ {len(rows) - 8} Predict ಪರದೆಯಲ್ಲಿ." if kn else
                     f"…and {len(rows) - 8} more on the Predict screen.")
    lines.append("ಗುರುತು ಎಂದರೆ ಪರಿಶೀಲಿಸಬೇಕಾದ ಸಂಕೇತ, ತೀರ್ಮಾನ ಅಲ್ಲ; ಕಡಿಮೆ ಸಂಖ್ಯೆಗಳಲ್ಲಿ ಒಂದೆರಡು ಪ್ರಕರಣಗಳೇ ಅದನ್ನು ಎಬ್ಬಿಸಬಹುದು." if kn else
                 "A flag is a signal to look at, not a finding: on small counts one or two cases can raise it. "
                 "Open the area on the Map to read the FIRs behind it.")
    top = rows[0]
    fups = [f"{str(top.get('crime_type') or '').replace('_', ' ').title()} in {top.get('zone')} this month",
            f"Where should I patrol next week in {top.get('zone')}?"]
    return {"answer": "\n".join(lines), "rows": rows[:20], "citations": [], "template_id": "ALERTS",
            "params": {"n": len(rows), "crime_types": ents.get("crime_types") or [], "zones": ents.get("zones") or []},
            "agent": "query", "suggested_followups": fups, "llm_answer": False,
            "actions": [{"type": "navigate", "payload": "/predict", "label": "Open Predict"}],
            "reasoning": [{"step": "anomaly", "detail": f"Anomaly scan ({window}): {len(rows)} upward flags{scope}."}]}
