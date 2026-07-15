"""Scheduler: pure verdict -> next-due-date mapping (fixed rules in V1)."""

from datetime import datetime, timedelta

VERDICT_OFFSETS_DAYS = {"fail": 0, "partial": 1, "pass": 3, "strong": 7}


def next_due(verdict: str, now: datetime) -> datetime:
    """Return when the Concept is due again after a Review with this verdict."""
    return now + timedelta(days=VERDICT_OFFSETS_DAYS[verdict])
