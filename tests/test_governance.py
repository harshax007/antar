"""
Governance (P6 · F7 RBAC + audit, F6 report/export) — via the HTTP layer (TestClient),
so the role guards + audit middleware actually run.
Run: python -m pytest tests/test_governance.py -v
"""

from fastapi.testclient import TestClient

from main import app
from app.services import audit_store

client = TestClient(app)


def test_constable_blocked_from_audit_admin_ok():
    """The live demo beat: Constable → 403 on /api/audit; Admin → 200."""
    assert client.get("/api/audit", headers={"X-Role": "Constable"}).status_code == 403
    r = client.get("/api/audit", headers={"X-Role": "Admin"})
    assert r.status_code == 200 and "rows" in r.json()


def test_every_api_call_is_audited():
    """M10: a row is written for each API call."""
    audit_store.clear()
    client.get("/api/dashboard/overview")
    rows = audit_store.query()
    assert rows and any(r["path"] == "/api/dashboard/overview" for r in rows)


def test_inspector_default_allows_graph_constable_blocked():
    """Inspector+ guard on /api/graph: default (no header) = Inspector → ok; Constable → 403."""
    assert client.get("/api/graph/S0001").status_code == 200
    assert client.get("/api/graph/S0001", headers={"X-Role": "Constable"}).status_code == 403


def test_export_and_report_render():
    """F6: export returns a report URL and the report HTML renders."""
    j = client.get("/api/export/ses-demo")
    assert j.status_code == 200 and j.json()["report_url"] == "/report/ses-demo"
    h = client.get("/report/ses-demo")
    assert h.status_code == 200 and "Intelligence Report" in h.text
