"""
Antar — Catalyst App Singleton / Init Helper
=================================================
One place to get an authenticated `CatalystApp`. Every Catalyst service
(Data Store, ZCQL, Stratus, NoSQL, QuickML, Cron, Auth) is reached through it:

    from app.core.catalyst import get_app
    app = get_app()
    rows = app.zcql().execute_query("SELECT * FROM crimes LIMIT 5")
    app.datastore().table("crimes").insert_rows([...])
    app.stratus().bucket(settings.STRATUS_BUCKET_NAME).put_object(key, body)

Two runtime contexts:
  1. Inside AppSail (a FastAPI request): the platform injects context; the SDK can
     initialize from the incoming request. Preferred in production.
  2. Standalone script (e.g. `python -m app.seeds.load --push`): no request exists,
     so we initialize with admin credentials from env (RefreshTokenCredential).

API names below are VERIFIED against the installed zcatalyst-sdk==1.0.1 surface
(initialize / initialize_app / CatalystApp.{datastore,zcql,stratus,nosql,...}).
The exact CREDENTIAL wiring for the standalone path is marked [VERIFY] — confirm the
refresh-token object keys + scope against docs.catalyst.zoho.com when you first run
`--push` with real credentials (Phase 1, Step 1.7).
"""

from __future__ import annotations

import zcatalyst_sdk
from zcatalyst_sdk.credentials import RefreshTokenCredential

from app.core.settings import settings

_app = None  # cached CatalystApp


def get_app(req=None):
    """
    Return an authenticated CatalystApp.

    - In an AppSail request handler, pass the request object: get_app(req).
      The SDK initializes per-request from platform headers.
    - In a standalone script, call get_app() with no args → admin init from env.

    Cached after first standalone init so scripts don't re-auth on every call.
    """
    global _app

    # AppSail request context — initialize from the live request each call.
    if req is not None:
        # [VERIFY] exact request-context init in AppSail Python runtime (Gate G1 deploy).
        return zcatalyst_sdk.initialize(req=req)

    if _app is not None:
        return _app

    # Standalone (script) context — admin credentials from env.
    # [VERIFY] refresh-token object keys + scope against docs.catalyst.zoho.com.
    # Standard Zoho OAuth refresh object: client_id / client_secret / refresh_token.
    if not (settings.CATALYST_PROJECT_ID and settings.QUICKML_CLIENT_ID):
        raise RuntimeError(
            "Catalyst admin credentials missing. Set CATALYST_PROJECT_ID/SECRET/KEY and "
            "the OAuth client creds in .env before running a standalone Catalyst script."
        )

    credential = RefreshTokenCredential({
        # [VERIFY] these key names — confirm against the SDK's ICatalystRefreshObj.
        "client_id": settings.QUICKML_CLIENT_ID,
        "client_secret": settings.QUICKML_CLIENT_SECRET,
        "refresh_token": settings.CATALYST_PROJECT_SECRET,  # [VERIFY] which secret/token
        "scope": "admin",
    })
    options = {
        # [VERIFY] option keys — project_id / project_key / project_domain (IN DC).
        "project_id": settings.CATALYST_PROJECT_ID,
        "project_key": settings.CATALYST_PROJECT_KEY,
        "project_domain": "https://console.catalyst.zoho.in",
    }
    _app = zcatalyst_sdk.initialize_app(credential=credential, options=options)
    return _app


def zcql_query(query: str, olap: bool = False) -> list[dict]:
    """
    Run a ZCQL query and return plain dict rows.
    Aggregation / GROUP-BY-heavy reads → set olap=True (Data Store OLAP engine).
    The Query Agent and seed spot-checks use this.
    """
    app = get_app()
    z = app.zcql()
    results = z.execute_olap_query(query) if olap else z.execute_query(query)
    # ZcqlQueryOutput → dict. [VERIFY] exact accessor (.to_dict() / dict(...)) on first run.
    out = []
    for r in results:
        if hasattr(r, "to_dict"):
            out.append(r.to_dict())
        elif isinstance(r, dict):
            out.append(r)
        else:
            out.append(dict(r))
    return out
