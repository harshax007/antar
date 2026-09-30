"""
One-time helper: exchange a Zoho self-client GRANT CODE for a refresh token.
Use this only if plain client_credentials doesn't work for the QuickML scope.

Steps:
 1. Go to https://api-console.zoho.in → your Self Client → "Generate Code" tab.
 2. Scope:  QuickML.deployment.READ      Duration: 10 min      → Generate → copy the code.
 3. Run (within 10 min):
       python -m scripts.get_refresh_token <GRANT_CODE>
 4. Copy the printed refresh_token into .env as QUICKML_REFRESH_TOKEN, then run scripts.g4_battery.

Reads CLIENT_ID/SECRET + token URL from .env (app.core.settings).
"""

from __future__ import annotations

import sys

import httpx

from app.core.settings import settings


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python -m scripts.get_refresh_token <GRANT_CODE>")
    code = sys.argv[1].strip()
    if not (settings.QUICKML_CLIENT_ID and settings.QUICKML_CLIENT_SECRET):
        sys.exit("Set QUICKML_CLIENT_ID and QUICKML_CLIENT_SECRET in .env first.")

    resp = httpx.post(settings.QUICKML_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": settings.QUICKML_CLIENT_ID,
        "client_secret": settings.QUICKML_CLIENT_SECRET,
        "code": code,
    })
    data = resp.json()
    print("Response:", {k: v for k, v in data.items() if k != "access_token"})
    if data.get("refresh_token"):
        print("\n✅ Add this to .env:")
        print(f"QUICKML_REFRESH_TOKEN={data['refresh_token']}")
        if data.get("access_token"):
            print(f"\n(or paste this 1-hour token for an immediate test:)")
            print(f"QUICKML_ACCESS_TOKEN={data['access_token']}")
    else:
        print("\n❌ No refresh_token returned. Common causes: code expired (>10 min), "
              "wrong data center (use accounts.zoho.in for IN), or scope mismatch.")


if __name__ == "__main__":
    main()
