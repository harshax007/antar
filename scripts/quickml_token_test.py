"""
Test whether we can get a QuickML access token from .env credentials alone
(client_credentials grant — no grant code needed).

Run:  python -m scripts.quickml_token_test
"""

from __future__ import annotations

import asyncio
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.quickml import _get_access_token
from app.core.settings import settings


async def main() -> None:
    print(f"token URL : {settings.QUICKML_TOKEN_URL}")
    print(f"scope     : {settings.QUICKML_SCOPE}")
    print(f"soid      : {settings.QUICKML_SOID or ('ZohoCatalyst.' + settings.QUICKML_ORG_ID)}")
    print(f"client id : {settings.QUICKML_CLIENT_ID[:12]}…\n")
    try:
        tok = await _get_access_token()
        print(f"✅ SUCCESS — got an access token (length {len(tok)}).")
        print("   client_credentials works — no grant code needed. Run:  python -m scripts.g4_battery")
    except Exception as e:
        print(f"❌ FAILED: {e}\n")
        print("Read the {...} above:")
        print(" • 'invalid_client'  → client id/secret wrong, or wrong data center (use accounts.zoho.in for IN).")
        print(" • 'invalid_scope' / 'access_denied' → client_credentials not enabled for this scope;")
        print("     use the self-client refresh-token route: scripts.get_refresh_token (same client + same DC).")
        print(" • 'invalid_soid'    → the org id is off; check QUICKML_ORG_ID.")


if __name__ == "__main__":
    asyncio.run(main())
