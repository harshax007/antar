"""
Antar — Forecast Agent (M8, WOW 3)
=======================================
Runs the weekly anomaly scan, attaches Second-Brain pre-pattern context when the
brain is seeded (cosine match vs `resolved_pattern` summaries), persists alerts, and
returns the created count. The planted Rajajinagar chain-snatching spike (z≈3.1)
fires here, ideally with the Jan-2025 resolved-pattern match → the WOW-3 narrative.

No LLM on the hot path (z-score is deterministic); an LLM only phrases the banner later.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services import anomaly, alerts_store
from app.core.reasoning_logger import log_step


def _brain_context(text: str, terms: list[str] | None = None) -> tuple[str | None, str | None]:
    """Best-effort `resolved_pattern` match for an alert (the WOW-3 brain context).
    Degrades to (None, None) if the brain index is empty (not yet seeded). NOTE:
    semantic_recall has no kind filter, so we take top-k and pick the resolved_pattern."""
    try:
        from app.second_brain.retrieval import semantic_recall
        for hit in (semantic_recall(text, k=3, terms=terms) or []):
            if hit.get("kind") == "resolved_pattern":
                return hit.get("row_id"), hit.get("summary_text")
    except Exception:
        pass
    return None, None


def scan(session_id: str = "cron") -> dict:
    """Run the scan → alerts. Returns {created, alerts}. Idempotent (replaces the set).
    Writes every alert to the Warning Ledger (product_store) with input row provenance.
    """
    from app.services.product_store import put_product

    anomalies = anomaly.scan()
    alerts = []
    for a in anomalies:
        atype  = a.get("anomaly_type", "spike")
        conf   = a.get("confidence", 0.0)
        direction = a.get("direction", "spike")
        hotspot_flag = " [SPATIAL HOTSPOT]" if a.get("hotspot", {}).get("confirmed") else ""

        if direction == "silence":
            text = (
                f"{a['crime_type']} reporting silence in {a['zone']}: "
                f"dropped to {a['observed']} this week vs ~{a['expected']} expected "
                f"(MAD-z={a['z_score']}, score={a.get('anomaly_score', abs(a['z_score'])):.1f}/10, "
                f"confidence={conf*100:.0f}%)"
            )
        else:
            text = (
                f"{a['crime_type']} {atype} in {a['zone']}{hotspot_flag}: "
                f"{a['observed']} this week vs ~{a['expected']} expected "
                f"(MAD-z={a['z_score']}, score={a.get('anomaly_score', a['z_score']):.1f}/10, "
                f"confidence={conf*100:.0f}%)"
            )

        brain_terms = [a.get("zone"), a.get("crime_type")]
        brain_id, brain_summary = _brain_context(text, terms=brain_terms)
        alert_obj = {
            "alert_id":            f"AL-{uuid.uuid4().hex[:10]}",
            "created_at":          datetime.now(timezone.utc).isoformat(),
            **a,
            "direction":           direction,
            "evidence_row_ids":    a.get("evidence_row_ids", []),
            "brain_match_id":      brain_id,
            "brain_match_summary": brain_summary,
            "status":              "new",
            "pushed":              False,
        }
        alerts.append(alert_obj)
        put_product(f"warning_ledger:alert:{alert_obj['alert_id']}", alert_obj, ttl=86400)

    alerts_store.replace_all(alerts)
    put_product("warning_ledger:alerts:latest", alerts, ttl=86400)
    log_step(session_id, "forecast", "scan", "MAD-z multi-signal scan + silence detection", f"{len(alerts)} alerts", 0)
    return {"created": len(alerts), "alerts": alerts}
