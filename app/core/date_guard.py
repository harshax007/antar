"""
Antar — Future-Date Guard
==============================
Policy: future-date AI/ML computation runs INTERNALLY only. No future calendar
date may leave the backend through any endpoint. Risk levels, incident bands
and relative windows ("next 7 days") are allowed; a concrete future date
(e.g. "2026-07-19") is not.

`redact_future_dates(payload)` recursively replaces any ISO calendar date
strictly after today with None (lists/dicts/strings traversed in place-safe
copies). `find_future_dates(payload)` lists offending values — used by tests.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _dates_in(text: str) -> list[date]:
    out = []
    for y, m, d in _ISO_RE.findall(text):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    return out


def find_future_dates(obj: Any, today: date | None = None) -> list[str]:
    """Return every ISO date string strictly after *today* found in obj."""
    today = today or date.today()
    found: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            found.extend(d.isoformat() for d in _dates_in(v) if d > today)
        elif isinstance(v, dict):
            for item in v.values():
                walk(item)
        elif isinstance(v, (list, tuple)):
            for item in v:
                walk(item)

    walk(obj)
    return found


def redact_future_dates(obj: Any, today: date | None = None) -> Any:
    """Deep-copy *obj* with any future calendar date scrubbed.

    A string that IS a bare future date becomes None; a string that merely
    CONTAINS one gets the date replaced with 'upcoming'.
    """
    today = today or date.today()

    def scrub(v: Any) -> Any:
        if isinstance(v, str):
            dates = _dates_in(v)
            future = [d for d in dates if d > today]
            if not future:
                return v
            if _ISO_RE.fullmatch(v.strip()):
                return None
            out = v
            for d in future:
                out = out.replace(d.isoformat(), "upcoming")
            return out
        if isinstance(v, dict):
            return {k: scrub(item) for k, item in v.items()}
        if isinstance(v, (list, tuple)):
            return [scrub(item) for item in v]
        return v

    return scrub(obj)
