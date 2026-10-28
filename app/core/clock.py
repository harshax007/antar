"""One "today" for the whole app.

ANTAR_TODAY = wallclock   (default) the calendar date in IST
            = real        the last date of the real KSP record in the register
            = YYYY-MM-DD  a fixed date (Lab demo, tests)
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

_IST = timezone(timedelta(hours=5, minutes=30))


def _spec() -> str:
    return (os.getenv("ANTAR_TODAY") or "wallclock").strip().lower()


@lru_cache(maxsize=1)
def _real_end() -> date | None:
    try:
        from app.core.db_path import DB_PATH, registry_connect
        con = registry_connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            top = con.execute("SELECT MAX(date) FROM FIRs WHERE is_synthetic_row = 0").fetchone()[0]
        finally:
            con.close()
        return date.fromisoformat(str(top)[:10]) if top else None
    except Exception:
        return None


def today() -> date:
    s = _spec()
    if s in ("", "wallclock", "today", "now"):
        return datetime.now(_IST).date()
    if s == "real":
        return _real_end() or datetime.now(_IST).date()
    return date.fromisoformat(s)


def is_fixed() -> bool:
    return _spec() not in ("", "wallclock", "today", "now")
