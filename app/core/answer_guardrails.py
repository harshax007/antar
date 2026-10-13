"""
Antar — Answer Guardrails (post-generation validation)
=====================================================
Prompt instructions are ADVISORY: a model can ignore them and usually does so under
pressure. These validators run on the composed answer AFTER generation and are the
thing that actually enforces the contract.

Design rules:
  • Never rewrite meaning — only STRIP what cannot be justified by the rows.
  • Never fabricate a replacement. If nothing survives, fall back to the deterministic
    answer the pipeline already computed.
  • Every guardrail is pure + synchronous so it can be unit-tested with a hostile input.
  • Failures are logged, not raised: a guardrail must never take the chat down.

Guardrails
  G1 number integrity   — every integer in the answer must exist in the rows/stats
  G2 no-result honesty  — empty rows => answer must lead with the absence
  G3 identifier fidelity— FIR / ACC / vehicle ids must appear verbatim in the rows
  G4 slop filter        — banned filler phrases removed
  G6 length cap         — per response-type sentence budget

G5 (future-dated records) is enforced upstream at the data layer by
`query_agent.drop_future_rows()` — owner decision 2026-07-18 was to EXCLUDE them
entirely rather than tag them, so they never reach this module.
"""

from __future__ import annotations

import re

# ── G4: filler / AI-slop phrases ──────────────────────────────────────────────
_SLOP = [
    "it is worth noting", "it's worth noting", "it is important to note",
    "it's important to note", "in conclusion", "as an ai", "i hope this helps",
    "based on the provided data", "based on the data provided", "the data shows that",
    "delve into", "leverage the", "a comprehensive overview", "in the landscape of",
    "it should be noted", "please note that", "here is the table", "here is a breakdown"
]
_SLOP_RE = re.compile("|".join(re.escape(s) for s in _SLOP), re.IGNORECASE)

# integers with optional thousands separators, not part of a longer token
_NUM_RE = re.compile(r"(?<![\w.-])(\d{1,3}(?:,\d{3})+|\d+)(?![\w.-])")
# identifier shapes used across the dataset (FIR numbers, ACC ids, vehicle regs)
# The second shape is the register's own FIR number (SYN-2026-908137, BG-2026-913354,
# FWD-2026-947135). It was missing, so an invented FIR of the commonest shape passed G3.
_ID_RE = re.compile(r"\b(?:\d{4}-[A-Z]{2,4}-[A-Z0-9]{1,4}-\d{2,6}|[A-Z]{2,4}-\d{4}-\d{3,}|ACC-\d+|S\d{4,}|[A-Z]{2}\d{2}[A-Z]{1,2}\d{3,4})\b")

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# per response-type sentence budget (RULE 4 in COMPOSE_SYSTEM)
LENGTH_BUDGET = {"COUNT": 2, "TREND": 3, "LIST": 4, "PROFILE": 6, "DEFAULT": 6}


def _norm_num(s: str) -> str:
    return s.replace(",", "")


def _allowed_numbers(rows: list, extra: list | None = None) -> set[str]:
    """Every number that legitimately appears in the evidence, plus derived counts."""
    allowed: set[str] = set()

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, bool):
            return
        elif isinstance(v, (int, float)):
            allowed.add(_norm_num(str(int(v)) if float(v).is_integer() else str(v)))
        elif isinstance(v, str):
            for m in _NUM_RE.findall(v):
                allowed.add(_norm_num(m))

    walk(rows)
    walk(extra or [])
    # the row count itself is a legitimate computed figure
    allowed.add(str(len(rows)))
    # small ordinals used for enumeration are always safe
    allowed.update({str(i) for i in range(0, 11)})
    return allowed


def check_numbers(answer: str, rows: list, extra: list | None = None) -> tuple[str, list[str]]:
    """G1 — drop sentences containing a number that the evidence cannot justify."""
    if not answer or not rows:
        return answer, []
    allowed = _allowed_numbers(rows, extra)
    kept, dropped = [], []
    for sent in _SENT_SPLIT.split(answer):
        bad = [n for n in _NUM_RE.findall(sent) if _norm_num(n) not in allowed]
        # a year-like number inside an identifier is handled by G3, ignore here
        bad = [n for n in bad if not _ID_RE.search(sent)]
        if bad:
            dropped.append(f"{bad} in: {sent.strip()[:80]}")
        else:
            kept.append(sent)
    return (" ".join(kept).strip() or answer), dropped


def check_identifiers(answer: str, rows: list) -> tuple[str, list[str]]:
    """G3 — an FIR/ACC/vehicle id must appear verbatim in the evidence."""
    if not answer or not rows:
        return answer, []
    blob = str(rows)
    kept, dropped = [], []
    for sent in _SENT_SPLIT.split(answer):
        bad = [i for i in _ID_RE.findall(sent) if i not in blob]
        if bad:
            dropped.append(f"{bad} in: {sent.strip()[:80]}")
        else:
            kept.append(sent)
    return (" ".join(kept).strip() or answer), dropped


def strip_slop(answer: str) -> tuple[str, int]:
    """G4 — remove filler phrases and tidy the seams they leave behind."""
    if not answer:
        return answer, 0
    n = len(_SLOP_RE.findall(answer))
    if not n:
        return answer, 0
    out = _SLOP_RE.sub("", answer)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"(^|\n)\s*[,;:]\s*", r"\1", out)
    # re-capitalise sentences left starting lowercase by the excision
    out = re.sub(r"(^|(?<=[.!?])\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out.strip(), n


def enforce_no_result(answer: str, rows: list, question: str, lang: str = "en") -> tuple[str, bool]:
    """G2 — with zero rows the answer MUST lead with the absence, never with related material."""
    if rows:
        return answer, False
    lead = (answer or "").strip().split("\n", 1)[0].lower()
    negative = any(k in lead for k in (
        "no ", "not found", "no matching", "none", "could not find", "0 records",
        "ಇಲ್ಲ", "ಕಂಡುಬಂದಿಲ್ಲ", "ದೊರೆತಿಲ್ಲ",
    ))
    if negative:
        return answer, False
    q = (question or "").strip()
    honest = (f"ಈ ಪ್ರಶ್ನೆಗೆ ಹೊಂದುವ ದಾಖಲೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ: “{q}”."
              if lang == "kn" else
              f"No records found for “{q}”.")
    return honest, True


def cap_length(answer: str, kind: str = "DEFAULT") -> tuple[str, bool]:
    """G6 — truncate at a sentence boundary to the per-type budget."""
    if not answer:
        return answer, False
    # never truncate structured blocks (tables / lists) by sentence count
    if "|" in answer or "\n- " in answer or "\n• " in answer:
        return answer, False
    sents = [s for s in _SENT_SPLIT.split(answer.strip()) if s.strip()]
    budget = LENGTH_BUDGET.get(kind, LENGTH_BUDGET["DEFAULT"])
    if len(sents) <= budget:
        return answer, False
    return " ".join(sents[:budget]).strip(), True


# template_id -> response kind (drives the length budget)
_KIND_BY_TEMPLATE = {
    "T3": "TREND", "T8": "COUNT", "T13": "COUNT", "T11": "COUNT",
    "T1": "LIST", "T12": "LIST", "T14": "LIST", "T15": "LIST",
    "T2": "PROFILE", "T4": "PROFILE", "T5": "PROFILE", "T9": "PROFILE", "T7": "PROFILE",
}


def apply_guardrails(
    answer: str,
    rows: list | None,
    question: str = "",
    lang: str = "en",
    template_id: str = "",
    citations: list | None = None,
) -> dict:
    """Run every guardrail. Returns {answer, violations:[...], changed:bool}.

    Never raises — a guardrail failure must not take the chat down.
    """
    rows = rows or []
    original = answer or ""
    violations: list[str] = []
    out = original
    rejected = False
    try:
        out, forced = enforce_no_result(out, rows, question, lang)
        if forced:
            violations.append("G2_no_result_not_honest")
            return {"answer": out, "violations": violations, "changed": True}

        out, n_slop = strip_slop(out)
        if n_slop:
            violations.append(f"G4_slop_removed:{n_slop}")

        # When EVERY sentence carries an unsupported number or identifier there is nothing
        # left to keep. The checks hand the text back unchanged in that case (this function
        # never returns an empty answer), which let a wholly invented one-line answer
        # through with only a log line. It is now marked `rejected`: the caller writes the
        # answer from the rows instead.
        n_sent = len([x for x in _SENT_SPLIT.split(out) if x.strip()])
        out, bad_nums = check_numbers(out, rows, citations)
        if bad_nums:
            violations.append(f"G1_unsupported_number:{len(bad_nums)}")
            rejected = rejected or len(bad_nums) >= n_sent

        n_sent = len([x for x in _SENT_SPLIT.split(out) if x.strip()])
        out, bad_ids = check_identifiers(out, rows)
        if bad_ids:
            violations.append(f"G3_unsupported_identifier:{len(bad_ids)}")
            rejected = rejected or len(bad_ids) >= n_sent

        out, capped = cap_length(out, _KIND_BY_TEMPLATE.get(template_id, "DEFAULT"))
        if capped:
            violations.append("G6_length_capped")
    except Exception as e:                                   # never break chat
        return {"answer": original, "violations": [f"guardrail_error:{type(e).__name__}"],
                "changed": False}

    out = (out or "").strip() or original
    res = {"answer": out, "violations": violations, "changed": out != original}
    if rejected:
        res["rejected"] = True
        violations.append("unsupported_answer_rejected")
    return res
