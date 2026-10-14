"""Archive the audit ledger and start a new chain linked to it.

    python scripts/audit_archive.py --officer <id> --reason "<why, in words>"          what it would do
    python scripts/audit_archive.py --officer <id> --reason "<why, in words>" --yes    do it

Stop the server first: it holds the chain's last hash in memory.

Nothing is edited or deleted from history. Every row of audit_log is copied unchanged into
audit_log_archive, then the live table starts again with one CHAIN_ARCHIVED entry whose
previous hash is the archived tail and which records the row count, a SHA-256 over the
archived hashes in order, and the breaks found in the old chain. See
app/services/audit_store.archive_and_restart.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import audit_store  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--officer", required=True)
ap.add_argument("--reason", required=True)
ap.add_argument("--yes", action="store_true")
a = ap.parse_args()

rep = audit_store.verify_chain_report()
print(json.dumps({k: rep.get(k) for k in ("ok", "total_entries", "verified", "broken_at_index", "broken_reason")}, indent=2))
if not a.yes:
    print("Dry run. Add --yes to archive these entries and start a new chain.")
    sys.exit(0)
out = audit_store.archive_and_restart(a.officer, a.reason)
print(json.dumps({k: v for k, v in out.items() if k != "after"}, indent=2))
print(json.dumps({k: out["after"].get(k) for k in ("ok", "total_entries", "verified", "chained_from_archive")}, indent=2))
