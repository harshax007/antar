"""
Antar - answering "what social factors go with crime?" in chat
==============================================================
Questions such as "is alcohol linked to crimes against women?", "does literacy relate to
crime?" or "which social factors go with violent crime?" are answered from the district
analysis in app/services/social_indicators.py: the same numbers, sentences and caveats as
the Social insights screen. Deterministic; no model writes any of it.
"""
from __future__ import annotations

import re

from app.services import social_indicators as si

# what a social question names, mapped to the indicator keys it means
_INDICATORS = [
    (r"\b(alcohol|drink|drinking|liquor)\b", ["men_alcohol"]),
    (r"\b(tobacco|smok)", ["men_tobacco"]),
    (r"\b(literacy|literate|education|educated|school|schooling)\b", ["literacy_2011", "women_literate", "women_10y_school"]),
    (r"\b(urban|urbani[sz]ation|cities|city)\b", ["urban_pct", "density"]),
    (r"\b(migration|migrant|migrants|population growth)\b", ["decadal_growth"]),
    (r"\b(child marriage|married before 18|early marriage)\b", ["child_marriage"]),
    (r"\b(poverty|poor|economic|amenit|electricity|sanitation|cooking fuel|stunt)", ["clean_fuel", "sanitation", "electricity", "child_stunting"]),
    (r"\b(sex ratio)\b", ["sex_ratio_2011"]),
    (r"\b(teen|adolescent) (pregnan|mother)", ["teen_pregnancy"]),
    (r"\b(insurance)\b", ["health_insurance"]),
]
_CATEGORY = [
    (r"\b(women|woman|dowry|cruelty|sexual|rape|pocso)\b", "women"),
    (r"\b(violent|violence|murder|assault|hurt)\b", "violent"),
    (r"\b(property|theft|burglary|robbery)\b", "property"),
    (r"\b(fraud|cyber|cheating)\b", "fraud"),
    (r"\b(road|accident)", "road"),
]
_SOCIAL = re.compile(r"\b(social|socio|sociolog|demograph|indicator|factor|factors)\b")
_LINK = re.compile(r"\b(crime|crimes|offen[cs]e|fir|firs|violence|accidents?)\b")
_RELATE = re.compile(r"\b(link|linked|relat|correlat|associat|go with|goes with|affect|influence|driv|cause|connected|risk factor)")


def wants_social(text: str) -> bool:
    t = (text or "").lower()
    if not _LINK.search(t):
        return False
    names_indicator = any(re.search(p, t) for p, _ in _INDICATORS)
    return bool((_SOCIAL.search(t) and (_RELATE.search(t) or "which" in t))
                or (names_indicator and _RELATE.search(t)))


def answer(text: str, lang: str = "en") -> dict:
    t = (text or "").lower()
    cat = next((c for p, c in _CATEGORY if re.search(p, t)), "all")
    keys = [k for p, ks in _INDICATORS if re.search(p, t) for k in ks]
    a = si.analysis()
    block = a["correlations"][cat]
    links = block["links"]
    picked = [l for l in links if l["key"] in keys] if keys else [l for l in links if l["significant"]][:3]
    crime = si.CRIME_WORDS.get(cat, "crime")
    lines = []
    if keys and not picked:
        lines.append(f"The district figures do not include that indicator for {crime}.")
    elif not picked:
        lines.append(f"No social indicator lines up clearly with recorded {crime} across Karnataka's {a['districts']} districts.")
    else:
        head = (f"Across Karnataka's {a['districts']} districts, {crime} per lakh people "
                f"({a['years'][0]}-{a['years'][1]}) against Census 2011 and NFHS-5 figures:")
        lines.append(head)
        for l in picked:
            held = ""
            if l.get("partial_urban") is not None and l["significant"]:
                held = (" It holds with urbanisation held constant." if l.get("holds_without_urban")
                        else " It fades once urbanisation is held constant.")
            p = "p < 0.001" if l["p"] < 0.001 else f"p = {l['p']:.3f}"
            said = re.sub(r" \((\w+) link\)\.$", "", l["sentence"]).rstrip(".")
            lines.append(f"- {said}: a {l['strength']} link (Spearman ρ {l['spearman']:+.2f}, {p}).{held}"
                         + (f" {l['reading']}" if l.get("reading") else ""))
        lines.append("This is a link between districts, never about any person, and never a basis to target a group. "
                     "Correlation is not cause.")
    rows = [{"indicator": l["label"], "spearman": l["spearman"], "p": l["p"], "partial_urban": l.get("partial_urban"),
             "source": l["source"], "year": l["year"]} for l in picked]
    return {
        "answer": "\n".join(lines), "rows": rows, "citations": [], "template_id": "SOCIAL",
        "params": {"category": cat, "indicators": keys}, "agent": "query", "llm_answer": False,
        "suggested_followups": ["Is alcohol linked to crimes against women?", "Does literacy relate to property crime?",
                                "Which social factors go with violent crime?"],
        "reasoning": [{"step": "route", "detail": "A question about social factors and crime: answered from the "
                                                  "district analysis (Census 2011, NFHS-5), not a FIR template."},
                      {"step": "method", "detail": "Spearman rank correlation across districts, Pearson beside it, "
                                                   "and a partial correlation with urbanisation held constant."}],
        "actions": [{"type": "navigate", "payload": "/social", "label": "District social insights"}],
    }
