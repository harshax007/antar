"""
Antar — Edition detection (Lab vs Cloud).
"""

from __future__ import annotations

from app.core.settings import settings


def is_lab() -> bool:
    """Return True if running in local Lab edition (ANTAR_EDITION=lab)."""
    return (settings.ANTAR_EDITION or "").strip().lower() == "lab"
