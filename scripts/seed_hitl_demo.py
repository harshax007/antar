"""
Antar - file demonstration requests into the officer-in-the-loop queue.

The Approvals screen is empty until someone proposes an action, so a demo opens on
"nothing is waiting". This files a few realistic requests through the SAME path an
officer uses (hitl.propose): each one is screened by Vigil, hash-locked and written to
the audit chain. Nothing executes; the approver still decides each one.

Every request is grounded in the register:
  * patrol redeployments come from the live anomaly alerts (observed vs expected, z-score,
    the FIRs behind the spike);
  * watchlist adds come from T19, UPI IDs that appear on FIRs in several districts.

The justification says "Demonstration request" so nobody mistakes it for a live order.
Patrol requests expire after 12 hours (hitl TTL), so run this on the morning of the demo.
Re-running is safe: an identical pending request is not queued twice.

    $env:ANTAR_EDITION="lab"; $env:ANTAR_DB="main_lab.db"
    D:\\Project\\.venv\\Scripts\\python.exe scripts/seed_hitl_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import hitl  # noqa: E402
from app.services import alerts_store  # noqa: E402
from app.services.zcql_local import run_query  # noqa: E402
from app.services.zcql_repo import build_spec  # noqa: E402

PROPOSER = "U-7001"        # Admin account: may propose, may not approve (approver is U-9001)
PROPOSER_ROLE = "Admin"
TAG = "Demonstration request."

# crime type -> (shift, units, hours): night for property crime, evening for street crime
_SHIFT = {"THEFT": ("night", 4, 8), "CHAIN SNATCHING": ("evening", 3, 6), "ROBBERY": ("night", 4, 8),
          "BURGLARY": ("night", 4, 8), "MURDER": ("all-day", 6, 12), "RIOTS": ("all-day", 6, 12)}


def _patrols(n: int = 3) -> list[dict]:
    seen, out = set(), []
    for a in alerts_store.list_recent(50):
        if a.get("direction") != "spike" or (a.get("z_score") or 0) < 3 or a.get("zone") in seen:
            continue
        seen.add(a["zone"])
        ct = str(a.get("crime_type") or "all crimes")
        shift, units, hours = _SHIFT.get(ct.upper(), ("evening", 3, 6))
        band = a.get("conformal_band") or {}
        firs = a.get("evidence_row_ids") or []
        out.append({
            "payload": {"zone": a["zone"], "units": units, "duration_hours": hours, "shift": shift,
                        "crime_focus": ct.lower()},
            "justification": (f"{TAG} Antar flagged a {ct.lower()} spike in {a['zone']}: "
                              f"{a.get('observed')} FIRs in the {a.get('window', 'latest week')} "
                              f"against an expected {a.get('expected')}. Requesting {units} units on the "
                              f"{shift} shift for {hours} hours while the cause is checked."),
            "evidence": [
                {"label": "Alert", "value": a.get("alert_id", "")},
                {"label": "Observed / expected", "value": f"{a.get('observed')} / {a.get('expected')}"},
                {"label": "Robust z-score", "value": f"{a.get('z_score', 0):.1f}"},
                {"label": "Calibrated range", "value": f"{band.get('lo')}–{band.get('hi')} ({band.get('coverage', '')})"},
                {"label": "FIRs behind it", "value": ", ".join(firs[:6]) + (f" +{len(firs) - 6} more" if len(firs) > 6 else "")},
            ],
        })
        if len(out) == n:
            break
    return out


def _watches(n: int = 2) -> list[dict]:
    rows = run_query(build_spec("T19", {"key_type": "upi", "min_districts": 3, "limit": 10}))
    out = []
    for r in rows:
        # only identifiers whose FIRs sit inside the real record (the register ends 2024-03-10)
        if str(r.get("last_date", "")) > "2024-03-10":
            continue
        out.append({
            "payload": {"watch_type": "entity", "target": r["key_value"],
                        "label": f"UPI {r['key_value']} · {r['firs']} FIRs in {r['districts']} districts"},
            "justification": (f"{TAG} UPI ID {r['key_value']} appears on {r['firs']} FIRs across "
                              f"{r['districts']} districts ({r['district_list']}) between {r['first_date']} "
                              f"and {r['last_date']}. Add it to the watchlist so a new FIR naming it alerts "
                              f"the investigating officers."),
            "evidence": [
                {"label": "Query", "value": "T19 - identifiers shared across districts"},
                {"label": "FIRs", "value": str(r["firs"])},
                {"label": "Districts", "value": r["district_list"]},
                {"label": "First / last seen", "value": f"{r['first_date']} / {r['last_date']}"},
            ],
        })
        if len(out) == n:
            break
    return out


def main() -> None:
    filed = 0
    for kind, items in (("patrol_redeployment", _patrols()), ("watchlist_add", _watches())):
        for it in items:
            try:
                a = hitl.propose(kind, it["payload"], officer=PROPOSER, role=PROPOSER_ROLE,
                                 justification=it["justification"], evidence=it["evidence"])
            except hitl.HitlError as e:
                print(f"  skipped {kind}: {e}")
                continue
            note = " (already pending)" if a.get("duplicate") else ""
            filed += not a.get("duplicate")
            print(f"  {a['action_id']}  {a['title']}{note}")
    s = hitl.stats()
    print(f"Filed {filed} new request(s); {s['pending']} pending, {s['pending_high_risk']} high risk.")


if __name__ == "__main__":
    main()
