"""Shared clock helpers for timestamped knowledge artifacts."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_today() -> str:
    """Return today's UTC date as an ISO ``YYYY-MM-DD`` string."""
    return datetime.now(timezone.utc).date().isoformat()
