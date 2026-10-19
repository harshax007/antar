"""
Antar — Sentinel Agent (A1: Watchlists & Tripwires · honest)
==================================================================
Monitors registered watchlists (entity / pattern / corridor) against the evidence
ledger. Each tripwire scan computes REAL signals — a resolved entity, a real crime
count, or a real inter-district corridor — and only fires when the data supports it.
No fabricated hit rows, no invented z-scores. Fires a watchhit product + an alert.
"""

from __future__ import annotations

import uuid
import time
from datetime import datetime, timezone
from typing import Any

from app.services import product_store, alerts_store, evidence_ledger
from app.services.entity_bridge import search_all

# Seed watches point at REAL targets so a scan produces genuine hits.
_WATCHES: list[dict[str, Any]] = [
    {"watch_id": "W-001", "watch_type": "entity", "target": "ACC-831453",
     "label": "Habitual offender watch · ACC-831453",
     "officer_id": "SHO-Rajajinagar", "created_at": "2026-04-01T08:00:00Z", "active": True},
    {"watch_id": "W-002", "watch_type": "pattern", "target": "theft:Bengaluru City",
     "label": "Pattern watch · theft in Bengaluru City",
     "officer_id": "SHO-Rajajinagar", "created_at": "2026-04-05T10:30:00Z", "active": True},
    {"watch_id": "W-003", "watch_type": "corridor", "target": "Bengaluru City",
     "label": "Corridor tripwire · inter-district movement via Bengaluru City",
     "officer_id": "SP-North", "created_at": "2026-04-08T14:15:00Z", "active": True},
]


def register_watch(watch_type: str, target: str, label: str, officer_id: str = "SHO-Rajajinagar") -> dict[str, Any]:
    """Register a new watchlist tripwire."""
    wid = f"W-{uuid.uuid4().hex[:6].upper()}"
    watch = {
        "watch_id": wid, "watch_type": watch_type, "target": target, "label": label,
        "officer_id": officer_id, "created_at": datetime.now(timezone.utc).isoformat(), "active": True,
    }
    _WATCHES.append(watch)
    product_store.put_product(f"sentinel:watch:{wid}", watch, ttl=3600)
    return watch


def list_watches(officer_id: str | None = None) -> list[dict[str, Any]]:
    """List active watches, optionally filtered by officer."""
    if officer_id:
        return [w for w in _WATCHES if w.get("officer_id") == officer_id and w.get("active")]
    return [w for w in _WATCHES if w.get("active")]


def scan_watches() -> list[dict[str, Any]]:
    """Scan active watchlists against real ledger signals; emit watchhit products + alerts."""
    hits: list[dict[str, Any]] = []
    ts = datetime.now(timezone.utc).isoformat()

    for w in _WATCHES:
        if not w.get("active"):
            continue
        wid, wtype, target = w["watch_id"], w["watch_type"], w["target"]
        hit_rows: list[dict] = []
        summary = ""
        metric: dict[str, Any] = {}

        if wtype == "entity":
            ev_hits = search_all(target, limit=5)
            if ev_hits:
                hit_rows = ev_hits
                metric = {"signals": len(ev_hits)}
                summary = f"Entity tripwire: {len(ev_hits)} ledger signal(s) for {target}."

        elif wtype == "pattern":
            crime, _, zone = target.partition(":")
            crime, zone = crime.strip(), zone.strip()
            n, refs = evidence_ledger.crime_count(crime, zone or None)
            if n > 0:
                hit_rows = [{"ref": r} for r in refs]
                metric = {"count": n}
                summary = (f"Pattern watch: {n} {crime} case(s) on record"
                           f"{f' in {zone}' if zone else ''} (evidence ledger).")

        elif wtype == "corridor":
            cors = [c for c in evidence_ledger.corridors(limit=20)
                    if target.lower() in f"{c['src']} {c['dst']}".lower()]
            if cors:
                c = cors[0]
                nd = c.get("next_district")
                hit_rows = [{
                    "corridor": f"{c['src']} ↔ {c['dst']}",
                    "linking_offenders": c["linking_accused"],
                    "recency_days": c["recency_days"],
                }]
                metric = {"linking_offenders": c["linking_accused"]}
                summary = (f"Corridor watch: {c['linking_accused']} linked offender(s) moving "
                           f"{c['src']} ↔ {c['dst']}"
                           + (f", onward {nd['district']}" if nd else "") + ".")

        if not hit_rows:
            continue

        hit_payload = {
            "hit_id": f"HIT-{uuid.uuid4().hex[:6].upper()}",
            "watch_id": wid, "label": w["label"], "watch_type": wtype, "target": target,
            "triggered_at": ts, "summary": summary, "metric": metric, "evidence_rows": hit_rows,
            "provenance": {
                "agent": "A1: Sentinel Watchdog",
                "method": "deterministic diff against evidence ledger",
                "compiled_at": ts,
            },
        }
        hits.append(hit_payload)
        product_store.put_product(f"sentinel:hit:{wid}:{int(time.time())}", hit_payload, ttl=600)

        alerts_store.add_alert({
            "alert_type": "sentinel_tripwire",
            "watch_id": wid,
            "severity": "high",
            "zone": target.split(":")[1] if ":" in target else target,
            "crime_type": target.split(":")[0] if ":" in target else "special_watch",
            "message": f"[ANTAR ALERT] {w['label']} — {summary}",
            "timestamp": ts,
        })

    return hits
