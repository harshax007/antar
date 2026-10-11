"""
Create an officer account, or change its password.

    python scripts/set_password.py U-7001 Admin --name "Operations Officer"
    python scripts/set_password.py U-9001 Approver --name "Supervising Officer"

The password is asked for twice and never echoed. Only a salted scrypt hash is written,
to the accounts file (ANTAR_USERS_FILE, default auth_users.json beside the backend, which
git ignores). The change counts from the next sign-in; no restart is needed.

For a container, set the file's contents as the ANTAR_USERS environment variable instead:

    python scripts/set_password.py --show-env

See app/core/accounts.py and docs/SECURITY.md, "Identity".
"""

import argparse
import getpass
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import accounts  # noqa: E402
from app.core.auth_middleware import ROLES  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("user_id", nargs="?")
    ap.add_argument("role", nargs="?", choices=ROLES)
    ap.add_argument("--name", default="", help="display name shown after sign-in")
    ap.add_argument("--show-env", action="store_true",
                    help="print the accounts file as one line, for the ANTAR_USERS variable")
    a = ap.parse_args()

    if a.show_env:
        print(json.dumps(accounts.load(), separators=(",", ":"), ensure_ascii=False))
        return 0
    if not a.user_id or not a.role:
        ap.error("user_id and role are required")
    first = getpass.getpass(f"New password for {accounts.norm_id(a.user_id)}: ")
    if first != getpass.getpass("Again: "):
        print("The two entries differ. Nothing was changed.", file=sys.stderr)
        return 1
    try:
        path = accounts.set_password(a.user_id, a.role, first, a.name)
    except ValueError as e:
        print(f"Not changed: {e}", file=sys.stderr)
        return 1
    print(f"{accounts.norm_id(a.user_id)} ({a.role}) saved to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
