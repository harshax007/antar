"""Forecast questions in chat — Phase 6 of docs/MAP_FORECASTING_PLAN.md.

"Where should I patrol next week in Mysuru?" · "theft forecast Bengaluru City next 4 weeks"
· "ಮುಂದಿನ ವಾರ ಮೈಸೂರಿನಲ್ಲಿ ಕಳ್ಳತನ ಎಲ್ಲಿ"

Before this, forecast questions were routed to the monthly TREND template — a question
about next week answered with last year's months. That is answering a different question
(Law 1), so forecast questions are now intercepted in query_agent_run and answered from
/api/forecast's data (app/forecast/service.py), in the constitution's template:

    BOTTOM LINE  [I] the highest forecast in scope, as a range in ICD 203 words
    CONTEXT      as-of date and the back-test accuracy of this kind of forecast
    EVIDENCE     the top units, each a range and its main reason
    LIMITS       reported FIRs ≠ crime; dates, not times; seeded history when it is

Resolve or refuse: a place that is not a police district or station, or two crime
categories at once, is refused with the nearest valid names — never widened.
"""
from __future__ import annotations

import difflib
import re
import sqlite3
from datetime import timedelta

from app.forecast import service as S
from app.forecast.categories import categorize
from app.forecast.features import ALL

# ── is this a forecast question? ─────────────────────────────────────────────

_FC_EN = re.compile(
    r"\b(forecast\w*|predict\w*|projection|next\s+(?:week|7\s+days|seven\s+days|month|"
    r"4\s+weeks|four\s+weeks|28\s+days|few\s+weeks|fortnight)|coming\s+week|upcoming\s+week|"
    r"where\s+(?:should|do|must)\s+(?:i|we)\s+(?:patrol|deploy)|likely\s+(?:to\s+)?(?:happen|occur)\s+next)\b",
    re.I)
_FC_KN = ("ಮುನ್ಸೂಚನೆ", "ಮುಂದಿನ ವಾರ", "ಮುಂದಿನ ತಿಂಗಳು", "ಮುಂದಿನ 7", "ಮುಂದಿನ 28", "ಮುಂಬರುವ ವಾರ")
_LONG = re.compile(r"next\s+(?:month|4\s+weeks|four\s+weeks|28\s+days|few\s+weeks)|ಮುಂದಿನ ತಿಂಗಳು|ಮುಂದಿನ 28", re.I)
# a past-looking question that happens to say "predicted" is not a forecast request
_PAST = re.compile(r"\b(?:last|past|previous)\s+(?:week|month|year|\d+\s+(?:days|weeks|months))\b", re.I)
_ZW = dict.fromkeys(map(ord, "‌‍​"), None)


def wants_forecast(text: str) -> bool:
    t = (text or "").translate(_ZW)
    if any(k in t for k in _FC_KN):
        return True
    return bool(_FC_EN.search(t)) and not _PAST.search(t)


def horizon_of(text: str) -> int:
    return 28 if _LONG.search((text or "").translate(_ZW)) else 7


# ── category ─────────────────────────────────────────────────────────────────

_KN_CRIME = {
    "ಸರಗಳ್ಳತನ": "PROPERTY", "ಕಳ್ಳತನ": "PROPERTY", "ಕಲ್ಲತನ": "PROPERTY", "ದರೋಡೆ": "PROPERTY",
    "ಮನೆಗಳ್ಳತನ": "PROPERTY", "ಕೊಲೆ": "MURDER", "ಅಪಹರಣ": "KIDNAP", "ಸೈಬರ್": "CYBER",
    "ವಂಚನೆ": "ECONOMIC", "ಅಪಘಾತ": "ROAD", "ಮಾದಕ": "NARCOTICS", "ಹಲ್ಲೆ": "VIOLENT",
    "ಕಾಣೆ": "MISSING", "ಮಹಿಳೆ": "WOMEN", "ಮಕ್ಕಳ": "CHILDREN",
}
_EN_CRIME = [(re.compile(rf"\b{w}\b", re.I), c) for w, c in (
    (r"thefts?|stolen|steal\w*|burglar\w*|robber\w*|dacoit\w*|chain[\s-]?snatch\w*|snatch\w*|"
     r"house[\s-]?break\w*|property\s+crimes?", "PROPERTY"),
    (r"murders?|homicides?", "MURDER"),
    (r"kidnap\w*|abduct\w*", "KIDNAP"),
    (r"cyber\s*crimes?|cyber|online\s+fraud", "CYBER"),
    (r"fraud|cheating|forgery|economic\s+offen[cs]es?", "ECONOMIC"),
    (r"drugs?|narcotics?|ndps|ganja", "NARCOTICS"),
    (r"accidents?|road\s+accidents?|traffic\s+accidents?", "ROAD"),
    (r"assault\w*|hurt|violen\w*|riot\w*|attempt\s+to\s+murder", "VIOLENT"),
    (r"missing(?:\s+persons?)?", "MISSING"),
    (r"crimes?\s+against\s+women|dowry|cruelty|molest\w*", "WOMEN"),
    (r"pocso|crimes?\s+against\s+children", "CHILDREN"),
    (r"sc/st|atrocit\w*", "SCST"),
)]


def categories_in(text: str) -> list[str]:
    t = (text or "").translate(_ZW)
    found: list[str] = []
    for rx, c in _EN_CRIME:
        if rx.search(t) and c not in found:
            found.append(c)
    for w, c in _KN_CRIME.items():
        if w in t and c not in found:
            found.append(c)
    # "attempt to murder" is violent, not murder
    if "VIOLENT" in found and "MURDER" in found and re.search(r"attempt\s+to\s+murder", t, re.I) \
            and not re.search(r"\bmurders?\b(?!.*attempt)", re.sub(r"attempt\s+to\s+murder", "", t, flags=re.I), re.I):
        found.remove("MURDER")
    return found


# ── place ─────────────────────────────────────────────────────────────────────

_KN_PLACE = {   # stems: Kannada inflects the ending ("ಮೈಸೂರು" → "ಮೈಸೂರಿನಲ್ಲಿ")
    "ಬೆಂಗಳೂರ": "bengaluru", "ಮೈಸೂರ": "mysuru", "ಬೆಳಗಾವ": "belagavi", "ಮಂಗಳೂರ": "mangaluru",
    "ಹುಬ್ಬಳ್ಳ": "hubballi", "ಧಾರವಾಡ": "dharwad", "ಕಲಬುರಗ": "kalaburagi", "ತುಮಕೂರ": "tumakuru",
    "ಶಿವಮೊಗ್ಗ": "shivamogga", "ಬಳ್ಳಾರ": "ballari", "ಉಡುಪ": "udupi", "ಮಂಡ್ಯ": "mandya",
    "ಹಾಸನ": "hassan", "ದಾವಣಗೆರ": "davanagere", "ವಿಜಯಪುರ": "vijayapura", "ಬೀದರ": "bidar",
    "ರಾಯಚೂರ": "raichur", "ಚಿತ್ರದುರ್ಗ": "chitradurga", "ಕೋಲಾರ": "kolar", "ಗದಗ": "gadag",
    "ಕೊಡಗ": "kodagu", "ಬಾಗಲಕೋಟ": "bagalkot", "ಹಾವೇರ": "haveri", "ಕೊಪ್ಪಳ": "koppal",
    "ಯಾದಗಿರ": "yadgir", "ಚಾಮರಾಜನಗರ": "chamarajanagar", "ಚಿಕ್ಕಮಗಳೂರ": "chikkamagaluru",
    "ಚಿಕ್ಕಬಳ್ಳಾಪುರ": "chickballapura", "ರಾಮನಗರ": "ramanagara", "ಇಂದಿರಾನಗರ": "indiranagar",
    "ಜಯನಗರ": "jayanagar", "ರಾಜಾಜಿನಗರ": "rajajinagar", "ಕರ್ನಾಟಕ": "karnataka",
}
_STATION_STOP = {"women", "traffic", "cyber", "city", "rural", "town", "east", "west", "north",
                 "south", "central", "market", "crime", "economic", "railway", "extension",
                 "layout", "nagar", "halli", "puram", "police", "station", "cen", "karnataka"}
_STATEWIDE = re.compile(r"\b(?:karnataka|state|statewide|whole state|all districts)\b", re.I)
_PLACE_HINT = re.compile(r"\b(?:in|for|at|around|near|of)\s+((?:[A-Z][\w.'-]*)(?:\s+[A-Z][\w.'-]*){0,3})")


class Scope:
    def __init__(self, kind: str, label: str, districts: list[str] | None = None,
                 station: str | None = None):
        self.kind, self.label, self.districts, self.station = kind, label, districts or [], station


def _normalise(text: str) -> str:
    t = (text or "").translate(_ZW)
    for stem, en in _KN_PLACE.items():
        if stem in t:
            t = t.replace(stem, f" {en} ")
    t = t.lower()
    for old, new in S._OLD_NAMES.items():
        t = re.sub(rf"\b{old}\b", new, t)
    return re.sub(r"\s+", " ", t)


def _word(t: str, phrase: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(phrase)}(?![\w])", t) is not None


def resolve_scope(conn: sqlite3.Connection, text: str) -> Scope:
    """Karnataka, one or more police districts, or one station — or a Refusal."""
    t = _normalise(text)
    districts = S._names(conn, "SELECT DISTINCT district FROM geo_units WHERE n_real > 0")
    full = sorted((d for d in districts if _word(t, d.lower())), key=len, reverse=True)
    picked: list[str] = []
    for d in full:                              # "bengaluru city" beats "bengaluru"
        if not any(d.lower() in p.lower() for p in picked):
            picked.append(d)
    if not picked:
        for d in districts:                     # "district" is spelled "Dist" in the registry
            if _word(t, d.lower().replace(" dist", " district")):
                picked.append(d)
    if not picked:
        # a bare city ("Mysuru") is every police district that carries its name — City AND
        # Dist — and the answer names both, so the scope is stated, not guessed
        bases = {d.split()[0].lower(): [] for d in districts if d.split()[0].lower() != "karnataka"}
        for d in districts:
            b = d.split()[0].lower()
            if b in bases:
                bases[b].append(d)
        for b, ds in bases.items():
            if len(b) >= 4 and _word(t, b):
                picked.extend(ds)
    if picked:
        label = " and ".join(sorted(picked)) if len(picked) <= 2 else f"{', '.join(sorted(picked)[:-1])} and {sorted(picked)[-1]}"
        return Scope("district", label, sorted(picked))

    stations = S._names(conn, "SELECT unit FROM geo_units WHERE unit_type = 'station' AND n_firs >= 20")
    keyed: dict[str, list[str]] = {}
    for s in stations:
        k = re.sub(r"\s+(?:ps|police station)$", "", s.lower().strip()).strip()
        if len(k) >= 5 and k not in _STATION_STOP:
            keyed.setdefault(k, []).append(s)
    hits = sorted((k for k in keyed if _word(t, k)), key=len, reverse=True)
    if hits:
        best = [s for s in keyed[hits[0]]]
        if len(best) == 1:
            return Scope("station", best[0], station=best[0])
        raise S.Refusal(f"“{hits[0]}” matches more than one police station.", best[:5], "place")

    if _STATEWIDE.search(t):
        return Scope("state", "Karnataka")
    m = _PLACE_HINT.search(text or "")
    if m and m.group(1).lower() not in {"karnataka", "next", "the", "this"}:
        name = m.group(1)
        pool = districts + [s for ss in keyed.values() for s in ss]
        near = difflib.get_close_matches(name, pool, n=4, cutoff=0.55)
        raise S.Refusal(f"“{name}” is not a police district or station in the registry.",
                        near or sorted(districts)[:6], "place")
    return Scope("state", "Karnataka")


# ── writing the answer ───────────────────────────────────────────────────────

_KN_CAT = {
    ALL: "ಅಪರಾಧ", "PROPERTY": "ಆಸ್ತಿ ಅಪರಾಧ", "VIOLENT": "ಹಿಂಸಾತ್ಮಕ ಅಪರಾಧ", "MURDER": "ಕೊಲೆ",
    "KIDNAP": "ಅಪಹರಣ", "WOMEN": "ಮಹಿಳೆಯರ ವಿರುದ್ಧದ ಅಪರಾಧ", "CHILDREN": "ಮಕ್ಕಳ ವಿರುದ್ಧದ ಅಪರಾಧ",
    "SCST": "SC/ST ದೌರ್ಜನ್ಯ", "ECONOMIC": "ಆರ್ಥಿಕ ಅಪರಾಧ", "CYBER": "ಸೈಬರ್ ಅಪರಾಧ",
    "NARCOTICS": "ಮಾದಕ ದ್ರವ್ಯ ಪ್ರಕರಣ", "MISSING": "ಕಾಣೆಯಾದವರ ಪ್ರಕರಣ", "CORRUPTION": "ಭ್ರಷ್ಟಾಚಾರ",
    "FOREIGN": "ವಿದೇಶಿಯರ ಪ್ರಕರಣ", "ENVIRON": "ಪರಿಸರ ಅಪರಾಧ", "ROAD": "ರಸ್ತೆ ಅಪಘಾತ",
    "LOCAL": "ಪೊಲೀಸ್ ಮತ್ತು ಸ್ಥಳೀಯ ಕಾಯ್ದೆ ಪ್ರಕರಣ", "OTHER": "ಇತರೆ ಪ್ರಕರಣ",
}


def _r(lo: int, hi: int) -> str:
    return f"{lo}" if lo == hi else f"{lo}–{hi}"


def _where(it: dict) -> str:
    return (f"{it['name']} ({it['station']})" if it["unit_type"] == "beat"
            else f"{it['name']} ({it['district']})")


def _week_span(hs: dict) -> str:
    from datetime import date
    wk = [date.fromisoformat(w) for w in hs["target_weeks"]]
    end = wk[-1] + timedelta(days=6)
    return f"{wk[0].strftime('%d %b')} – {end.strftime('%d %b %Y')}"


def _refusal(r: S.Refusal, lang: str) -> str:
    opts = ", ".join(r.options[:5])
    instead = {"category": ("all crime", "ಎಲ್ಲಾ ಅಪರಾಧಗಳ"),
               "place": ("somewhere else", "ಬೇರೆ ಸ್ಥಳದ")}.get(r.field, ("something else", "ಬೇರೆ"))
    if lang == "kn":
        return (f"ಈ ಮುನ್ಸೂಚನೆಗೆ ಉತ್ತರಿಸಲಿಲ್ಲ: {r.message} {instead[1]} ಉತ್ತರ ಬೇರೆ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರವಾಗುತ್ತದೆ."
                + (f"\nಆಯ್ಕೆಗಳು: {opts}" if opts else ""))
    return (f"I could not answer this forecast: {r.message} Answering for {instead[0]} would "
            f"answer a different question." + (f"\nTry: {opts}." if opts else ""))


def answer(conn: sqlite3.Connection, text: str, lang: str = "en") -> dict:
    """The query-agent result for a forecast question (same keys as query_agent_run)."""
    kn = lang == "kn"
    h = horizon_of(text)
    base = {"rows": [], "citations": [], "agent": "query", "template_id": "FORECAST",
            "llm_answer": False, "suspects": []}
    reasoning = [{"step": "route", "detail": "Forecast question — answered from the map "
                                             "forecast (Poisson GLM, conformal ranges), not a past trend."}]
    try:
        cats = categories_in(text)
        if len(cats) > 1:
            raise S.Refusal("a forecast covers one crime category at a time, and this question "
                            "names " + " and ".join(S.LABELS[c] for c in cats) + ".",
                            [S.LABELS[c] for c in cats], "category")
        cat = cats[0] if cats else ALL
        scope = resolve_scope(conn, text)
        kw = {"horizon": h, "category": cat, "limit": 5}
        if scope.kind == "state":
            kw["unit_type"] = "station"
        elif scope.kind == "district":
            kw.update(unit_type="beat", district="|".join(scope.districts))
        else:
            kw.update(unit_type="beat", station=scope.station)
        hs = S.hotspots(conn, **kw)
    except S.Refusal as r:
        return {**base, "template_id": "UNRESOLVED", "answer": _refusal(r, lang), "params": {},
                "reasoning": reasoning + [{"step": "filters", "detail": f"Refused: {r.message}"}],
                "suggested_followups": _followups(None, lang)}
    except S.NotReady as n:
        msg = ("ಈ ದಿನಾಂಕದ ಮುನ್ಸೂಚನೆ ಸಿದ್ಧವಾಗುತ್ತಿದೆ; ಒಂದು ನಿಮಿಷದಲ್ಲಿ ಮತ್ತೆ ಕೇಳಿ." if kn
                else f"I can't answer yet: {n} Ask again in a minute.")
        return {**base, "template_id": "UNRESOLVED", "answer": msg, "params": {},
                "reasoning": reasoning, "suggested_followups": []}

    params = {"horizon_days": h, "category": cat, "scope": scope.label, "unit_type": kw["unit_type"],
              "districts": scope.districts, "station": scope.station}
    items = hs["items"]
    usable = [i for i in items if i["history"] == "ok"]
    as_of = hs["as_of"]
    span = _week_span(hs)
    cat_en = "FIRs" if cat == ALL else f"{S.LABELS[cat].lower()} FIRs"
    cat_kn = _KN_CAT.get(cat, S.LABELS[cat])
    lines: list[str] = []

    if not usable:
        lines.append(
            (f"[U] {scope.label}: ಕಳೆದ ವರ್ಷದಲ್ಲಿ ಇಲ್ಲಿ {cat_kn} FIR ಗಳು ಬಹಳ ಕಡಿಮೆ ದಾಖಲಾಗಿವೆ — "
             f"ವಿಶ್ವಾಸಾರ್ಹ ಮುನ್ಸೂಚನೆಗೆ ದಾಖಲೆ ಸಾಲದು; ಈ ಮಾಹಿತಿ ದಾಖಲಾಗಿಲ್ಲ.") if kn else
            (f"[U] Too few {cat_en} are on record in {scope.label} in the year to "
             f"{as_of['history_through']} for a reliable forecast. That history is not recorded "
             f"well enough to say — which is not the same as a quiet place."))
    else:
        top = usable[0]
        b8, b9 = top["band80"], top["band90"]
        if kn:
            lines.append(f"[I] ಮುಂದಿನ {h} ದಿನಗಳಲ್ಲಿ ({span}) {scope.label} ನಲ್ಲಿ ಅತಿ ಹೆಚ್ಚು {cat_kn} "
                         f"ಮುನ್ಸೂಚನೆ {_where(top)} ಗೆ: ಸಂಭವನೀಯ {_r(b8['lo'], b8['hi'])} FIR "
                         f"(ಬಹಳ ಸಂಭವನೀಯ {_r(b9['lo'], b9['hi'])}).")
        else:
            noun = "crime" if cat == ALL else S.LABELS[cat].lower()
            lines.append(f"[I] {_where(top)} has the highest {noun} forecast in {scope.label} "
                         f"for the next {h} days ({span}): likely {_r(b8['lo'], b8['hi'])} FIRs, "
                         f"very likely {_r(b9['lo'], b9['hi'])}.")
        acc = hs.get("accuracy")
        if kn:
            ctx = (f"• ಪ್ರವೃತ್ತಿ: ಮುನ್ಸೂಚನೆ {as_of['as_of']} ದಿನಾಂಕದಂತೆ (ಅಂದಾಜು)"
                   + (f"; ನೈಜ ದಾಖಲೆಯ ಹಿಂದಿನ ಪರೀಕ್ಷೆಯಲ್ಲಿ ಮೇಲಿನ 5% "
                      f"{'ಬೀಟ್‌ಗಳು' if hs['unit_type'] == 'beat' else 'ಠಾಣೆಗಳು'} ಮುಂದಿನ {h} ದಿನಗಳ "
                      f"{round(100 * acc['top5_share_caught'])}% FIR ಹಿಡಿದವು." if acc else "."))
        else:
            ctx = (f"• Direction: forecast as of {as_of['as_of']}"
                   + (f"; back-tested on the real record, the top 5% of {hs['unit_type']}s caught "
                      f"{round(100 * acc['top5_share_caught'])}% of the next {h} days' FIRs "
                      f"(last-4-weeks hotspots: {round(100 * acc['top5_share_caught_last4'])}%)."
                      if acc else "."))
        lines.append(ctx)
        for n, it in enumerate(items[:5], 1):
            if it["history"] != "ok":
                lines.append(f"[U] {n}. {_where(it)} — "
                             + ("ದಾಖಲೆ ಕಡಿಮೆ, ಮುನ್ಸೂಚನೆ ಇಲ್ಲ" if kn else "too little history to forecast"))
                continue
            # the level (shrinkage) reason is true of most beats; quote the one that differs
            reasons = [d for d in it["drivers"] if d["key"] != "level"]
            r = reasons[0]["text"].rstrip(".") if reasons else None
            if kn:
                lines.append(f"[I] {n}. {_where(it)} — ಸಂಭವನೀಯ {_r(it['band80']['lo'], it['band80']['hi'])}, "
                             f"ಬಹಳ ಸಂಭವನೀಯ {_r(it['band90']['lo'], it['band90']['hi'])}")
            else:
                lines.append(f"[I] {n}. {_where(it)} — likely {_r(it['band80']['lo'], it['band80']['hi'])}, "
                             f"very likely {_r(it['band90']['lo'], it['band90']['hi'])}"
                             + (f"; {r[0].lower()}{r[1:]}" if r else ""))
    # limits — always
    if kn:
        lines.append("ಗಮನಿಸಿ: ಮುನ್ಸೂಚನೆ ದಾಖಲಾದ FIR ಗಳನ್ನು ಎಣಿಸುತ್ತದೆ, ಅಪರಾಧವನ್ನಲ್ಲ; ದಾಖಲೆಯಲ್ಲಿ "
                     "ದಿನಾಂಕ ಮಾತ್ರ ಇದೆ, ಸಮಯ ಇಲ್ಲ. ಗಸ್ತು ನಿರ್ಧಾರ ಅಧಿಕಾರಿಯದು.")
        if (as_of.get("real_share") or 0) < 0.99:
            lines.append(f"ಗಮನಿಸಿ: ಈ ಮುನ್ಸೂಚನೆಯ ಹಿಂದಿನ ಇತ್ತೀಚಿನ ವಾರಗಳು ಪ್ರದರ್ಶನ (seeded) ದತ್ತಾಂಶ "
                         f"— ನೈಜ ದಾಖಲೆ {round(100 * (as_of.get('real_share') or 0))}%.")
    else:
        lines.append("Note: forecasts count reported FIRs, not crime, and the record has dates, "
                     "not times. The map proposes; the officer decides.")
        if (as_of.get("real_share") or 0) < 0.99:
            lines.append(f"Note: the recent weeks behind this forecast are seeded demonstration "
                         f"data ({round(100 * (as_of.get('real_share') or 0))}% real record); its "
                         f"accuracy was measured on the real record.")

    rows = [{"unit": i["unit"], "unit_type": i["unit_type"], "station": i["station"],
             "district": i["district"], "expected": i["expected"], "lo80": i["band80"]["lo"],
             "hi80": i["band80"]["hi"], "lo90": i["band90"]["lo"], "hi90": i["band90"]["hi"],
             "history": i["history"], "evidence_class": "I"} for i in items]
    reasoning += [
        {"step": "parameters", "detail": f"Scope {scope.label} ({hs['unit_type']}s), "
                                          f"{S.LABELS[cat]}, next {h} days."},
        {"step": "query", "detail": f"Read {len(items)} forecast(s) as of {as_of['as_of']} "
                                    f"from forecast_output; {as_of['basis']}"},
    ]
    top_unit = usable[0]["unit"] if usable else None
    return {**base, "answer": "\n".join(lines), "rows": rows, "params": params,
            "reasoning": reasoning, "forecast": hs,
            "actions": [{"type": "navigate", "payload": "/map",
                         "label": "ಮುನ್ಸೂಚನೆ ನಕ್ಷೆ ತೆರೆಯಿರಿ" if kn else "Open the forecast on the map",
                         "params": {"forecast_unit": top_unit, "forecast_horizon": h,
                                    "forecast_category": cat}}],
            "suggested_followups": _followups(scope, lang, cat, h)}


def _followups(scope: Scope | None, lang: str, cat: str = ALL, h: int = 7) -> list[str]:
    kn = lang == "kn"
    if scope is None:
        return (["ಮುಂದಿನ ವಾರ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಕಳ್ಳತನ ಎಲ್ಲಿ", "ಮುಂದಿನ ವಾರದ ಅಪರಾಧ ಮುನ್ಸೂಚನೆ"] if kn else
                ["where should I patrol next week in Mysuru",
                 "theft forecast Bengaluru City next 4 weeks", "crime forecast for Karnataka next week"])
    place = scope.station or scope.label
    if kn:
        return [f"ಮುಂದಿನ ತಿಂಗಳು {place} ಮುನ್ಸೂಚನೆ" if h == 7 else f"ಮುಂದಿನ ವಾರ {place} ಮುನ್ಸೂಚನೆ"]
    out = [f"{'next 4 weeks' if h == 7 else 'next week'} forecast for {place}"]
    if cat == ALL:
        out.append(f"theft forecast for {place} next week")
    else:
        out.append(f"all crime forecast for {place} next week")
    if scope.kind == "state":
        out.append("where should I patrol next week in Bengaluru City")
    return out
