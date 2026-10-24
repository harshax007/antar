"""
Antar — Structured Answer Layout
=====================================
Deterministic post-composer that turns a finished answer + query results into
a typed presentation layout the frontend can render as sectioned cards:

    {
      "headline":  str,                     # lead sentence of the answer
      "stats":     [{"label", "value"}],    # small stat chips (real numbers only)
      "facts":     [str],                   # bullet lines from the answer
      "kdiu":      [{"tag", "text"}],       # K/D/I/U-tagged claims
      "evidence":  [ ...citations ],        # source FIR rows (pass-through)
    }

No LLM involved — every field is derived from data already computed, so the
layout can never contradict the prose answer.
"""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"^\[(VERIFIED|COMPUTED|INFERRED|GAP|K|D|I|U)\]\s*(.*)$", re.IGNORECASE)
_BULLET_RE = re.compile(r"^(?:[•\-*]|\d+\.)\s+(.*)$")

# Pipeline internals must never surface as officer-facing "facts". These lines are
# reasoning-trail steps (route/parameters/query/answer) or raw param dicts. They belong
# in the Why? trail. Defence-in-depth: even if something upstream concatenates them into
# the answer again, the layout will not promote them to the visible summary.
_INTERNAL_RE = re.compile(
    r"^\s*(?:"
    r"classified as\b|extracted\s*:|queried the crime database|summarized using only|"
    r"no filters needed|reasoning trail|routed to\b|template\s+T\d+\b|"
    r"\{['\"]?\w+['\"]?\s*:"                      # a raw python/JSON param dict
    r")", re.IGNORECASE)


def _is_internal(line: str) -> bool:
    t = (line or "").strip()
    if not t:
        return False
    # strip a list prefix first — the trail arrives as "1. Classified as ..." / "• Extracted: ..."
    t = _BULLET_RE.sub(r"\1", t).strip()
    if not t:
        return False
    if _INTERNAL_RE.search(t):
        return True
    # a line that is mostly a dict/JSON blob is machine output, not an answer
    return t.count("'") + t.count('"') >= 6 and ("{" in t or ":" in t)

_TAG_CANON = {"VERIFIED": "K", "COMPUTED": "D", "INFERRED": "I", "GAP": "U",
              "K": "K", "D": "D", "I": "I", "U": "U"}


def _headline(answer: str) -> str:
    for line in answer.splitlines():
        t = line.strip()
        if not t or _is_internal(t):     # never lead with a pipeline internal
            continue
        m = _TAG_RE.match(t)
        if m:
            t = m.group(2).strip()
        if _BULLET_RE.match(t):
            t = _BULLET_RE.match(t).group(1).strip()
        # First sentence of the first substantive line.
        for sep in (". ", "! "):
            if sep in t:
                t = t.split(sep, 1)[0] + "."
                break
        return t[:220]
    return ""


def _date_range(rows: list[dict]) -> str | None:
    dates = sorted(str(r["occurred_at"])[:10] for r in rows if r.get("occurred_at"))
    if not dates:
        return None
    return dates[0] if dates[0] == dates[-1] else f"{dates[0]} → {dates[-1]}"


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _chart_from_rows(query: dict, rows: list[dict]) -> dict | None:
    """A compact, minimal inline chart spec — only from REAL aggregate rows.
    Trend templates → line; breakdown/hotspot templates → bar. None otherwise,
    so the chat never renders a chart it can't back with data."""
    if not rows:
        return None
    template = query.get("template_id", "")
    # T24 stages per station/district, T27 sides: bars of the count each row stands on.
    if template in ("T24", "T27") and "grp" in rows[0] and rows[0].get("grp") != "ALL":
        key = "under_investigation" if template == "T24" else "firs"
        pts = [{"label": str(r.get("grp")), "value": _num(r.get(key))}
               for r in rows if _num(r.get(key)) is not None][:8]
        return {"kind": "bar", "unit": "cases", "points": pts} if len(pts) >= 2 else None
    # T26 day-of-week / month-of-year: bars in calendar order
    if template == "T26" and "slot" in rows[0]:
        pts = [{"label": str(r.get("slot")), "value": _num(r.get("n"))}
               for r in sorted(rows, key=lambda r: r.get("slot_index") or 0)]
        return {"kind": "bar", "unit": "cases", "points": pts} if len(pts) >= 2 else None
    if "n" not in rows[0]:
        return None
    if template == "T25":
        try:
            from app.services.zcql_repo import head_label
        except Exception:
            head_label = str
        k = "CrimeHead_Name" if "CrimeHead_Name" in rows[0] else "crime_type"
        pts = [{"label": head_label(r.get(k)) if k == "CrimeHead_Name" else str(r.get(k)).title(),
                "value": _num(r.get("n"))} for r in rows if r.get(k) and _num(r.get("n")) is not None][:8]
        return {"kind": "bar", "unit": "cases", "points": pts} if len(pts) >= 2 else None
    # Trend over months → line
    if template == "T3" and "month" in rows[0]:
        pts = [{"label": str(r.get("month")), "value": _num(r.get("n"))}
               for r in rows if _num(r.get("n")) is not None]
        pts = pts[:14]
        return {"kind": "line", "unit": "cases", "points": pts} if len(pts) >= 2 else None
    # Breakdown / hotspot tables → bar (label = first non-count column)
    if template in ("T7", "T8", "T11", "T13", "T4", "T23"):
        # T23 rows are {Beat_Name, UnitName, n} / {Village_Area_Name, district_norm, n}: label by name.
        label_key = next((k for k in ("Beat_Name", "Village_Area_Name") if k in rows[0]), None) \
            or next((k for k in rows[0] if k != "n"), None)
        if not label_key:
            return None
        pts = [{"label": str(r.get(label_key)).replace("_", " "), "value": _num(r.get("n"))}
               for r in rows if _num(r.get("n")) is not None]
        pts = pts[:8]
        return {"kind": "bar", "unit": "cases", "points": pts} if len(pts) >= 2 else None
    return None


# Which base table each template reads — for the chain-of-custody "source" line.
_TEMPLATE_SOURCE = {"T2": "suspects", "T4": "suspects", "T5": "suspects"}


def build_custody(query: dict, mode: str = "offline") -> dict | None:
    """Chain-of-custody strip — the evidentiary provenance of a factual answer.

    Deterministic and reuses what the pipeline already computed (rows, citations,
    template, dataset date). Rendered COLLAPSED by default in the UI; expands to the
    full FIR list. Returns None when there is nothing to attest (no rows), so the
    strip never appears on a no-result or chit-chat turn.

    Shape:
      {record_count, source, as_of, range, firs[], fir_total, verification, method}
    verification is "K" (Verified — from records) because every row came from a
    whitelisted ZCQL template over the real crime tables; it is NOT an LLM claim.
    """
    try:
        rows = query.get("rows", []) or []
        if not rows:
            return None
        citations = query.get("citations", []) or []
        tid = query.get("template_id", "") or ""
        firs = [c.get("fir") for c in citations if c.get("fir")]
        if tid == "CASE":
            r0 = rows[0] if isinstance(rows[0], dict) else {}
            return {"record_count": 1, "groups": None, "source": "FIR register",
                    "as_of": r0.get("registered"), "range": None, "firs": firs[:1], "fir_total": len(firs[:1]),
                    "verification": "K", "method": "Case timeline of one FIR"}
        if tid == "SOCIAL":
            # a link between districts, computed from FIR rates and public indicators: Derived
            from app.services.social_indicators import YEARS
            return {"record_count": 30, "groups": None, "source": "District indicators (Census 2011, NFHS-5) and FIR rates",
                    "as_of": f"FIRs {YEARS[0]}-{YEARS[1]}", "range": None, "firs": [], "fir_total": 0,
                    "verification": "D", "method": "Spearman rank correlation across 30 districts"}

        from app.services.zcql_repo import data_today, TEMPLATES
        tmpl = TEMPLATES.get(tid)
        method = f"ZCQL {tid}".strip()
        if tmpl and getattr(tmpl, "description", None):
            method = f"{method} · {tmpl.description}"

        # A grouped answer returns one row per group, each carrying its count in `n`. The
        # strip says how many RECORDS stand behind the answer, not how many groups came
        # back: the IPC/SLL split read "400 records" (its group limit) under a headline
        # about 996,000 FIRs. The groups are capped, so their sum understates it too; the
        # figure is the count over the template's own filters, as the answer's headline is.
        counts = [r.get("n") for r in rows if isinstance(r, dict)]
        grouped = len(counts) == len(rows) and all(isinstance(n, int) and not isinstance(n, bool) for n in counts)
        behind = len(rows)
        if grouped:
            behind = sum(counts)
            try:
                from app.agents.answer_writer import _total_like
                behind = max(behind, _total_like(tid, query.get("params") or {}) or 0)
            except Exception:
                pass
        return {
            "record_count": behind,
            "groups": len(rows) if grouped else None,
            "source": _TEMPLATE_SOURCE.get(tid, "crimes"),
            "as_of": data_today().isoformat(),
            "range": _date_range(rows),
            "firs": firs[:12],
            "fir_total": len(firs),
            "verification": "K",
            "method": method[:90],
        }
    except Exception:
        return None


def build_layout(answer: str, query: dict, results: dict | None = None) -> dict:
    """Build the typed layout. Cheap (string scans + counters), never raises."""
    try:
        rows = query.get("rows", []) or []
        citations = query.get("citations", []) or []
        params = query.get("params", {}) or {}

        stats: list[dict] = []
        if rows:
            stats.append({"label": "records", "value": str(len(rows))})
        if citations:
            stats.append({"label": "citations", "value": str(len(citations))})
        zone = (params.get("zones") or [None])[0]
        if zone:
            stats.append({"label": "zone", "value": str(zone)})
        ct = (params.get("crime_types") or [None])[0]
        if ct:
            stats.append({"label": "crime type", "value": str(ct)})
        dr = _date_range(rows)
        if dr:
            stats.append({"label": "period", "value": dr})
        results = results or {}
        graph = results.get("network") or {}
        if graph.get("nodes"):
            stats.append({"label": "network", "value": f"{len(graph['nodes'])} nodes"})

        facts: list[str] = []
        kdiu: list[dict] = []
        for line in (answer or "").splitlines():
            t = line.strip()
            if not t or _is_internal(t):
                continue
            m = _TAG_RE.match(t)
            if m:
                body = m.group(2).strip()
                if body and not _is_internal(body):
                    kdiu.append({"tag": _TAG_CANON[m.group(1).upper()], "text": body})
                continue
            b = _BULLET_RE.match(t)
            if b:
                item = b.group(1).strip()
                if item and not _is_internal(item):
                    facts.append(item)

        return {
            "headline": _headline(answer or ""),
            "stats": stats[:6],
            "facts": facts[:8],
            "kdiu": kdiu[:8],
            "evidence": citations[:6],
            "chart": _chart_from_rows(query, rows),
        }
    except Exception:
        return {"headline": "", "stats": [], "facts": [], "kdiu": [], "evidence": [], "chart": None}


def with_identity(layout: dict, identity: dict | None) -> dict:
    """Attach Antar's template sections and evidence class to a layout.

    The bottom line becomes the headline, the per-claim K/D/I/U classes replace the old
    tag scrape, and the frontend gets `sections` to render the response template.
    """
    if not isinstance(layout, dict) or not identity or not identity.get("sections"):
        return layout
    sec = identity["sections"]
    out = dict(layout)
    if sec.get("bottom_line"):
        out["headline"] = sec["bottom_line"]
    out["sections"] = sec
    out["evidence_class"] = identity.get("evidence_class")
    out["evidence_label"] = identity.get("evidence_label")
    out["kind"] = identity.get("kind")
    if identity.get("claims"):
        out["kdiu"] = identity["claims"]
    return out
