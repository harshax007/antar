"""
Antar - a briefing of the answer just given
===========================================
"Prepare a short briefing for the district superintendent summarising the result, priority
records and data limitations" asks about the previous answer, not about the register. It
used to be read as a fresh question, find no crime or place in it, and ask which hotspot
was meant.

The brief is built from the conversation alone, deterministically, with no model and no new
query: the question asked, the result as it was stated, the records it listed first, and
every limitation the answer carried plus the standing ones of the FIR register. Nothing in it
is new; a brief that added a finding would be a second answer nobody asked for. Phone
numbers, UPI ids and accounts are masked (redact_pii), as they would be in any copy that
leaves the chat.
"""
from __future__ import annotations

import re

# "brief / memo / summary" + something that points back at the answer, or names who it is for
_ASK = re.compile(r"\b(brief(?:ing)?|memo|note|summary|summari[sz]\w*|report|write[- ]?up)\b", re.I)
_BACK = re.compile(r"\b(?:the|this|that|these|those|above|previous|last|your)\s+(?:results?|answers?|findings?|"
                   r"analysis|response|output|records?|list)\b|\bsummari[sz]\w*\s+(?:it|this|that|the above)\b", re.I)
_FOR = re.compile(r"\bfor\s+(?:the\s+)?(?:district\s+)?(superintendent(?: of police)?|sp|dcp|commissioner|igp|dgp|"
                  r"senior officers?|my (?:boss|superior|senior))\b", re.I)
_TAG = re.compile(r"^\s*\[(?:VERIFIED|COMPUTED|INFERRED|DERIVED|UNVERIFIED)\]\s*")
_RECORD = re.compile(r"^\s*\d+\.\s+")
_LIMIT = re.compile(r"\b(note|not held|demonstration|data quality|no coordinates|not recorded|withheld|"
                    r"cannot|limitation|unavailable|missing)\b", re.I)

_STANDING = [
    "Counts are FIRs as registered: a registration records a complaint, not a finding of guilt or an outcome.",
    "Victims and complainants are recorded by sex and age group only; no identity is shown.",
]


def wants_briefing(text: str) -> bool:
    """A brief OF the answer: "brief the SP on theft in Mysuru" is a new question, and is not this."""
    t = text or ""
    if not (_ASK.search(t) and _BACK.search(t)):
        return False
    # "Retrieve FIR 1000112452023000001 and summarise it": the "it" is that FIR, a case question
    from app.agents.case_answer import fir_ids
    return not fir_ids(t)


def _title(who: str | None) -> str:
    w = (who or "").lower()
    if w.startswith("superintendent"):
        return "District Superintendent of Police"
    if w in ("sp", "dcp", "igp", "dgp"):
        return w.upper()
    return w.title() if w and not w.startswith("my ") else "Senior Officer"


def _previous(history: list[dict]) -> tuple[str | None, str | None]:
    """The last answer before this question, and the question it answered."""
    turns = list(history or [])
    if turns and turns[-1].get("role") == "user":
        turns = turns[:-1]
    answer = question = None
    for i in range(len(turns) - 1, -1, -1):
        if turns[i].get("role") == "assistant" and (turns[i].get("text") or "").strip():
            answer = turns[i]["text"]
            question = next((t.get("text") for t in reversed(turns[:i]) if t.get("role") == "user"), None)
            break
    return answer, question


def build(user_text: str, history: list[dict], lang: str = "en") -> dict:
    from app.core.guardrails import redact_pii
    answer, question = _previous(history)
    kn = lang == "kn"
    m = _FOR.search(user_text or "")
    who = m.group(1) if m else None
    if not answer:
        return {"answer": ("ಈ ಸಂಭಾಷಣೆಯಲ್ಲಿ ಇನ್ನೂ ಯಾವ ಉತ್ತರವೂ ಇಲ್ಲ. ಮೊದಲು ಪ್ರಶ್ನೆ ಕೇಳಿ, ನಂತರ ಅದರ ಸಾರಾಂಶ ಕೇಳಿ." if kn else
                           "There is no earlier answer in this conversation to brief on. Ask the question first, "
                           "then ask for the briefing."),
                "rows": [], "citations": [], "template_id": "CLARIFY", "params": {"missing": "answer"},
                "agent": "query", "suggested_followups": [], "llm_answer": False,
                "reasoning": [{"step": "briefing", "detail": "A briefing was asked for before any answer was given."}]}
    lines = [ln.rstrip() for ln in answer.splitlines() if ln.strip()]
    lead = next((ln for ln in lines if not _RECORD.match(ln) and not _LIMIT.search(ln)), lines[0])
    records = [_RECORD.sub("", ln) for ln in lines if _RECORD.match(ln)][:5]
    limits = list(dict.fromkeys(re.sub(r"^[^\w\[]*", "", ln) for ln in lines if _LIMIT.search(ln) and ln != lead))
    out = [f"**Briefing for the {_title(who)}**", ""]
    if question:
        out.append(f"**Question:** {question.strip()}")
    out.append(f"**Result:** {_TAG.sub('', lead).strip()}")
    if records:
        out.append("**Priority records** (as listed in the answer):")
        out += [f"{i}. {r}" for i, r in enumerate(records, 1)]
    out.append("**Data limitations:**")
    out += [f"- {x}" for x in limits + _STANDING]
    out.append("")
    out.append("_Prepared from the answer above; no new query was run and nothing has been added to it._")
    text = redact_pii("\n".join(out))
    return {"answer": text, "rows": [], "citations": [], "template_id": "BRIEFING",
            "params": {"for": who, "records": len(records)}, "agent": "query",
            "suggested_followups": [], "llm_answer": False,
            "reasoning": [{"step": "briefing", "detail": f"Brief built from the previous answer ({len(records)} records, "
                                                          f"{len(limits)} stated limitations); no new query."}]}
