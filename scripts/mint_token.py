"""
Mint a signed Antar bearer token (signed identity mode).

    ANTAR_AUTH_SECRET=<secret> python scripts/mint_token.py U-7001 Admin
    ANTAR_AUTH_SECRET=<secret> python scripts/mint_token.py U-9001 Approver --ttl 3600

Generate a secret once with:
    python -c "import secrets; print(secrets.token_urlsafe(48))"

This is the bridge until Catalyst Auth is wired: whatever issues tokens (this script,
or a login endpoint behind real authentication) must hold the secret; the API only
verifies. See docs/SECURITY.md, "Identity".
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.auth_middleware import ROLES, mint_token  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("officer")
    ap.add_argument("role", choices=ROLES)
    ap.add_argument("--ttl", type=int, default=None, help="seconds (default ANTAR_TOKEN_TTL_S, 8 h)")
    a = ap.parse_args()
    secret = os.environ.get("ANTAR_AUTH_SECRET", "")
    if len(secret) < 32:
        print("ANTAR_AUTH_SECRET must be set and at least 32 characters.", file=sys.stderr)
        return 2
    print(mint_token(a.officer, a.role, ttl_s=a.ttl, secret=secret))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
