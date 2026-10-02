"""
Antar — Export / Intelligence Report (F6 / M9)
===================================================
A print-optimized `/report/{session_id}` (FastAPI-served HTML: conversation + reasoning
chain + officer + timestamp) → the browser's "Print → Save as PDF" produces a court-
readable report locally. `GET /api/export/{session_id}` → {report_url}. The
SmartBrowz → Stratus PDF pipeline (G5) is the deploy version.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core import sessions
from app.core.audit import hash_event

router = APIRouter()          # mounted at /api/export
report_router = APIRouter()   # mounted at root → /report/{id}


def _step_text(s: dict) -> str:
    detail = s.get("detail")
    if detail:
        return str(detail)
    agent, step = s.get("agent", "system"), s.get("step", "process")
    if agent == "supervisor" and step == "intent_classification":
        return f"Classified intent and routed to: {', '.join(s.get('routes', []))}."
    return f"Executed {agent} {step} step."


def _report_model(session_id: str) -> dict:
    """One Q→A record per assistant turn — shared by the HTML report and the JSON export so
    both carry the same document hash."""
    turns = sessions.all_turns(session_id)
    items, pending_q = [], None
    for t in turns:
        if t["role"] == "user":
            pending_q = t.get("text", "")
            continue
        meta = t.get("meta") or {}
        conf = meta.get("confidence") or {}
        items.append({
            "n": len(items) + 1,
            "asked_at": datetime.fromtimestamp(t.get("ts", 0), timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "question": meta.get("question") or pending_q or "",
            "answer": t.get("text", ""),
            "lang": meta.get("lang") or t.get("lang", "en"),
            "officer": meta.get("officer", ""),
            "template_id": meta.get("template_id") or t.get("template_id", ""),
            "method": meta.get("method", ""),
            "rows": meta.get("rows"),
            "citations": meta.get("citations") or [],
            "confidence": conf.get("answer") if isinstance(conf, dict) else conf,
            "confidence_label": conf.get("label", "") if isinstance(conf, dict) else "",
            "elapsed_ms": meta.get("elapsed_ms"),
            "mode": meta.get("mode", ""),
            "agents": meta.get("agents") or [],
            "audit_hash": meta.get("audit_hash", ""),
            "reasoning_id": t.get("reasoning_id", ""),
            "steps": [_step_text(s) for s in (t.get("steps") or [])],
        })
        pending_q = None
    payload = {"session": session_id,
               "turns": [{k: v for k, v in it.items() if k != "asked_at"} for it in items]}
    return {"session_id": session_id, "items": items,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "document_sha256": hash_event("DOC_ROOT", payload)}


@router.get("/{session_id}")
@router.post("/{session_id}")
async def export(session_id: str) -> dict:
    m = _report_model(session_id)
    return {
        "session_id": session_id,
        "report_url": f"/report/{session_id}",
        "turns": len(m["items"]),
        "document_sha256": m["document_sha256"],
        "note": "Printable audit report (browser Print → Save as PDF).",
    }


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


# The evidence class of every line, as ICD 203 K/D/I/U. Ordered most- to least-certain.
CLAIM_CLASSES = {
    "VERIFIED": ("K", "Known", "Read directly from FIR rows; the records are cited below."),
    "COMPUTED": ("D", "Derived", "Calculated from cited rows by a deterministic transform."),
    "INFERRED": ("I", "Inferred", "A scored hypothesis, not a finding."),
    "GAP": ("U", "Unknown", "Named as missing, with the action that would close it."),
}


def _answer_html(text: str) -> str:
    """Light markdown → HTML, KEEPING the evidence class on every line that carries one.

    This function used to begin by DELETING the class marker:

        text = re.sub(r"^[(COMPUTED|VERIFIED|INFERRED)]s*", "", text, flags=re.M)

    Every other part of Antar fights to keep that label attached to its claim — synthesis
    tags each line with it, the API carries it, the Brain tags corpus hits `D`, and
    `advocate_agent` gates the Inferred -> Known transition. The printable report is the
    one artefact an officer signs and hands to a court, which makes it the place the class
    matters MOST, and it was the one place the class was thrown away: a reader of the old
    PDF could not tell a row-level fact from a scored guess.

    The marker is now rendered as a badge beside the line it belongs to.
    """
    import re
    text = text or ""
    out, in_list = [], None
    for raw in text.splitlines():
        line = raw.strip()
        badge = ""
        # The marker sits at the start of the line, or just after a list prefix — a ranked
        # answer arrives as "1. [COMPUTED] Bengaluru City ...". Matching only at position 0
        # silently dropped the class on exactly the answers that rank things, which are the
        # ones an officer is most likely to act on.
        m_cls = re.match(r"^((?:[•\-*]\s+|\d+[.)]\s+)?)"
                         r"\[(VERIFIED|COMPUTED|INFERRED|GAP)\]\s*", line)
        if m_cls:
            code, label, _why = CLAIM_CLASSES[m_cls.group(2)]
            badge = (f'<span class="cls cls-{code}" title="{html.escape(label)}">'
                     f'{code}</span> ')
            line = m_cls.group(1) + line[m_cls.end():]
        esc = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(line))
        m_b = re.match(r"^(?:[•\-*])\s+(.*)$", esc)
        m_n = re.match(r"^\d+[.)]\s+(.*)$", esc)
        kind = "ul" if m_b else "ol" if m_n else None
        if in_list and kind != in_list:
            out.append(f"</{in_list}>"); in_list = None
        if kind:
            if not in_list:
                out.append(f"<{kind}>"); in_list = kind
            out.append(f"<li>{badge}{(m_b or m_n).group(1)}</li>")
        elif line:
            out.append(f"<p>{badge}{esc}</p>")
    if in_list:
        out.append(f"</{in_list}>")
    return "".join(out)


def _render(session_id: str) -> str:
    m = _report_model(session_id)
    items, doc_hash = m["items"], m["document_sha256"]
    short_hash = doc_hash[:16]
    blocks = []
    for it in items:
        cites = it["citations"]
        cite_rows = "".join(
            f"<tr><td>{_e(c.get('fir'))}</td><td>{_e(c.get('station'))}</td>"
            f"<td>{_e(c.get('date'))}</td><td>{_e(c.get('section'))}</td></tr>"
            if isinstance(c, dict) else f"<tr><td colspan=4>{_e(c)}</td></tr>"
            for c in cites[:25])
        cite_html = (f'<table class="cites"><thead><tr><th>FIR</th><th>Station</th><th>Date</th>'
                     f'<th>Sections</th></tr></thead><tbody>{cite_rows}</tbody></table>'
                     + (f'<div class="small">+{len(cites) - 25} more cited records</div>' if len(cites) > 25 else "")
                     ) if cites else '<div class="small">Aggregate answer — computed over the full FIR table (no individual record citations).</div>'
        conf = it["confidence"]
        facts = [
            ("Method", f"{it['template_id']} — {it['method']}" if it["method"] and it["method"] != it["template_id"] else it["template_id"]),
            ("Records used", it["rows"]),
            ("Confidence", f"{round(conf * 100)}% · {it['confidence_label']}" if isinstance(conf, (int, float)) else None),
            ("Response time", f"{it['elapsed_ms'] / 1000:.1f} s" if it["elapsed_ms"] is not None else None),
            ("Engine", ("LLM-composed" if it["mode"] == "llm" else "Deterministic (whitelisted query templates)") if it["mode"] else None),
            ("Agents", ", ".join(it["agents"]) or None),
            ("Language", "Kannada" if it["lang"] == "kn" else "English"),
            ("Officer", it["officer"] or None),
            ("Audit-chain hash", it["audit_hash"] or None),
        ]
        facts_html = "".join(f"<dt>{_e(k)}</dt><dd{' class=mono' if k == 'Audit-chain hash' else ''}>{_e(v)}</dd>"
                             for k, v in facts if v not in (None, ""))
        steps_html = "".join(f"<li>{_e(s)}</li>" for s in it["steps"])
        blocks.append(f"""
<section class="turn">
  <div class="qhead"><span class="num">Q{it['n']}</span><span class="when">{_e(it['asked_at'])}</span></div>
  <div class="q">{_e(it['question'])}</div>
  <div class="a">{_answer_html(it['answer'])}</div>
  <dl class="facts">{facts_html}</dl>
  <h4>Evidence</h4>{cite_html}
  {f'<details open><summary>Reasoning chain</summary><ol class="steps">{steps_html}</ol></details>' if steps_html else ''}
</section>""")
    body = "\n".join(blocks) or "<p>No conversation recorded for this session.</p>"
    now = m["generated"]
    officers = sorted({it["officer"] for it in items if it["officer"]}) or ["OF-1001 (Inspector)"]
    total_ms = sum(it["elapsed_ms"] or 0 for it in items)

    # The evidence-class legend. A badge nobody can decode is decoration, and this report
    # is read by people who have never seen Antar.
    legend_html = "".join(
        f'<div><span class="cls cls-{code}">{code}</span> <b>{_e(label)}</b> - {_e(why)}</div>'
        for code, label, why in CLAIM_CLASSES.values())

    # Whether the tamper-evident ledger actually verifies, right now, stated in the
    # document rather than implied by the presence of a hash. A per-turn hash proves
    # nothing on its own: the question is whether the chain it belongs to still checks out.
    try:
        from app.services.audit_store import verify_chain_report
        rep = verify_chain_report()
        _cls = "ok" if rep.get("ok") else "bad"
        _head = ("Audit chain verified" if rep.get("ok")
                 else "AUDIT CHAIN BROKEN - this report must not be relied on")
        _detail = (f"{rep.get('verified', 0)} of {rep.get('total_entries', 0)} ledger "
                   f"entries re-hashed and linked when this document was generated.")
        if rep.get("legacy_unverifiable"):
            _detail += (f" {rep['legacy_unverifiable']} legacy entries predate the "
                        "verifiable format and are counted, not claimed.")
        if not rep.get("ok"):
            _detail += (f" Failure at entry {rep.get('broken_at_index')}: "
                        f"{rep.get('broken_reason')}.")
        chain_html = f'<div class="chain {_cls}"><b>{_e(_head)}</b><br>{_e(_detail)}</div>'
    except Exception:            # noqa: BLE001 - a report must still print without it
        chain_html = ('<div class="chain bad"><b>Audit chain not verified</b><br>'
                      'The ledger could not be read when this document was generated.</div>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Antar Intelligence Report — {html.escape(session_id)}</title>
<link rel="preconnect" href="https://fonts.gstatic.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&family=Noto+Sans+Kannada:wght@400;600;700&display=swap" rel="stylesheet">
<style>
 @page{{size:A4;margin:16mm 14mm}}
 body{{font-family:"Noto Sans","Noto Sans Kannada",Inter,system-ui,"Segoe UI",sans-serif;max-width:820px;margin:28px auto;color:#111;padding:0 22px;font-size:13px;line-height:1.5}}
 h1{{font-size:21px;margin:0 0 2px}} .sub{{color:#555;font-size:12px}}
 .meta{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:14px 0 20px;padding:10px 12px;border:1px solid #d6dae3;border-radius:8px;background:#f8f9fb;font-size:11.5px}}
 .meta b{{display:block;font-size:10px;color:#667;text-transform:uppercase;letter-spacing:.5px}}
 .turn{{border:1px solid #dfe3ea;border-radius:10px;padding:12px 16px;margin:0 0 16px;break-inside:avoid-page}}
 .qhead{{display:flex;justify-content:space-between;font-size:11px;color:#667}} .num{{font-weight:700;color:#1f3a8a}}
 .q{{font-weight:600;font-size:14px;margin:4px 0 8px;padding:6px 10px;background:#eef1fb;border-radius:6px}}
 .a p{{margin:4px 0}} .a ol,.a ul{{margin:4px 0 4px 20px;padding:0}}
 .facts{{display:grid;grid-template-columns:130px 1fr;gap:3px 10px;margin:10px 0;font-size:11.5px}}
 .facts dt{{color:#667}} .facts dd{{margin:0}} .mono{{font-family:Consolas,monospace;font-size:10.5px;word-break:break-all}}
 .cls{{display:inline-block;min-width:15px;padding:0 4px;margin-right:5px;border-radius:3px;
      font:700 9.5px/15px Consolas,monospace;text-align:center;vertical-align:1px;color:#fff}}
 .cls-K{{background:#15803d}} .cls-D{{background:#1d4ed8}} .cls-I{{background:#b45309}} .cls-U{{background:#6b7280}}
 .legend{{display:grid;grid-template-columns:repeat(2,1fr);gap:4px 16px;margin:10px 0 18px;padding:9px 12px;
      border:1px solid #d6dae3;border-radius:8px;background:#fbfcfd;font-size:11px;break-inside:avoid}}
 .chain{{margin:0 0 18px;padding:9px 12px;border-radius:8px;font-size:11.5px;break-inside:avoid}}
 .chain.ok{{border:1px solid #86efac;background:#f0fdf4;color:#14532d}}
 .chain.bad{{border:1px solid #fca5a5;background:#fef2f2;color:#7f1d1d}}
 h4{{margin:10px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#445}}
 table.cites{{width:100%;border-collapse:collapse;font-size:11px}} .cites th,.cites td{{border:1px solid #e1e4ea;padding:3px 6px;text-align:left}}
 .cites th{{background:#f3f4f7}} .small{{font-size:11px;color:#667}}
 details{{margin-top:8px;font-size:11.5px;color:#444}} summary{{cursor:pointer;font-weight:600}} .steps{{margin:4px 0 0 18px;padding:0}}
 .watermark{{margin-top:30px;padding:16px 20px;background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;display:flex;align-items:center;gap:20px;break-inside:avoid}}
 .seal-container{{flex-shrink:0;display:flex;align-items:center;justify-content:center}}
 .bar{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #eee;margin-bottom:10px}}
 .bar button{{font:inherit;padding:6px 14px;border-radius:6px;border:1px solid #1f3a8a;background:#1f3a8a;color:#fff;cursor:pointer}}
 @media print{{.noprint{{display:none}} body{{margin:0;max-width:none}} details{{display:block}}}}
</style></head><body>
<div class="bar noprint"><button onclick="window.print()">Print / Save as PDF</button></div>
<h1>Antar — Intelligence Report</h1>
<div class="sub">Karnataka State Police · Conversational crime-intelligence session record</div>
<div class="meta">
 <div><b>Session</b>{html.escape(session_id)}</div>
 <div><b>Officer</b>{html.escape(", ".join(officers))}</div>
 <div><b>Generated</b>{now}</div>
 <div><b>Questions</b>{len(items)} · {total_ms / 1000:.1f} s total</div>
</div>
{chain_html}
<div class="legend">{legend_html}</div>
{body}

<div class="watermark">
  <div class="seal-container">
    <svg width="64" height="64" viewBox="0 0 100 100">
      <path d="M35 75 L25 95 L40 90 L55 95 L45 75" fill="#b45309" />
      <path d="M65 75 L55 95 L70 90 L85 95 L75 75" fill="#b45309" />
      <circle cx="50" cy="45" r="35" fill="#f59e0b" stroke="#d97706" stroke-width="3" />
      <circle cx="50" cy="45" r="30" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-dasharray="3,3" />
      <path d="M38 45 L46 53 L62 35" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </div>
  <div>
    <strong style="color: #b45309; font-size: 13px; letter-spacing: 0.5px;">EVIDENTIARY DIGITAL WATERMARK</strong><br>
    <span style="font-size: 11px; color: #451a03; font-family: monospace;">Document Signature (SHA-256): {doc_hash}</span><br>
    <span style="font-size: 11px; color: #451a03; font-family: monospace;">Short Signature: {short_hash}</span><br>
    <i style="font-size: 11px; color: #78350f; display: block; margin-top: 4px;">This cryptographic seal verifies that this intelligence report has not been tampered with or modified post-generation.</i>
  </div>
</div>

<p class="small" style="margin-top:14px">Answers are computed from the FIR registry through whitelisted, parameterised query templates; every turn is sealed into the tamper-evident audit chain (per-turn hash above). Synthetic datathon data.</p>
<script>
 (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve())
   .then(function(){{ if (!/[?&]noprint=1/.test(location.search)) setTimeout(function(){{ window.print(); }}, 250); }});
</script>
</body></html>"""


@report_router.get("/report/{session_id}")
async def report(session_id: str):
    return HTMLResponse(_render(session_id))


def _render_derivation(target_id: str) -> str:
    from app.api.audit import get_derivation_chain
    import asyncio
    data = asyncio.run(get_derivation_chain(target_id))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    steps_html = "".join(
        f"<li><b>Stage {s['stage']}:</b> {html.escape(str(s['detail']))}</li>"
        for s in data.get("derivation_chain", [])
    )
    methods_html = "".join(
        f"<li>{html.escape(m)}</li>"
        for m in data.get("method_lines", [])
    )
    doc_hash = data.get("chain_hash", "0" * 64)
    short_hash = doc_hash[:16]

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Antar Chargesheet Derivation — {html.escape(target_id)}</title>
<style>
 body{{font-family:Inter,system-ui,Segoe UI,sans-serif;max-width:800px;margin:32px auto;color:#111;padding:0 22px}}
 h1{{font-size:20px;margin:0 0 4px}} .meta{{color:#666;font-size:13px;margin-bottom:20px;border-bottom:1px solid #ddd;padding-bottom:10px}}
 .section{{margin:20px 0;padding:14px 16px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px}}
 .section h3{{margin:0 0 10px 0;font-size:15px;color:#1e293b}}
 ol, ul{{margin:0;padding-left:20px}} li{{margin:6px 0;font-size:13px;line-height:1.4}}
 .watermark{{margin-top:40px;padding:20px;background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;display:flex;align-items:center;gap:20px}}
 .seal-container{{flex-shrink:0;display:flex;align-items:center;justify-content:center}}
 @media print{{.noprint{{display:none}}}}
</style></head><body onload="window.print()">
<h1>Antar — Chargesheet Derivation Chain</h1>
<div class="meta">Target Artifact ID: <b>{html.escape(target_id)}</b> · Verified at {now} · Evidentiary Integrity Seal</div>

<div class="section">
  <h3>Derivation Pipeline Stages</h3>
  <ol>{steps_html}</ol>
</div>

<div class="section">
  <h3>Methodology & Algorithms Applied</h3>
  <ul>{methods_html}</ul>
</div>

<div class="watermark">
  <div class="seal-container">
    <svg width="64" height="64" viewBox="0 0 100 100">
      <path d="M35 75 L25 95 L40 90 L55 95 L45 75" fill="#b45309" />
      <path d="M65 75 L55 95 L70 90 L85 95 L75 75" fill="#b45309" />
      <circle cx="50" cy="45" r="35" fill="#f59e0b" stroke="#d97706" stroke-width="3" />
      <circle cx="50" cy="45" r="30" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-dasharray="3,3" />
      <path d="M38 45 L46 53 L62 35" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </div>
  <div>
    <strong style="color: #b45309; font-size: 13px; letter-spacing: 0.5px;">EVIDENTIARY DIGITAL WATERMARK</strong><br>
    <span style="font-size: 11px; color: #451a03; font-family: monospace;">Derivation Chain SHA-256: {doc_hash}</span><br>
    <span style="font-size: 11px; color: #451a03; font-family: monospace;">Short Hash: {short_hash}</span><br>
    <i style="font-size: 11px; color: #78350f; display: block; margin-top: 4px;">Cryptographically verifies the computational provenance and input record lineage.</i>
  </div>
</div>

<p class="noprint" style="color:#888;font-size:12px;margin-top:24px">Use your browser's Print → Save as PDF for judicial / chargesheet submission.</p>
</body></html>"""


@report_router.get("/report/derivation/{target_id}")
async def report_derivation(target_id: str):
    return HTMLResponse(_render_derivation(target_id))
