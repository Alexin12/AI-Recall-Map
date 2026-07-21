"""Scheduler: pure verdict -> next-due-date mapping (fixed rules in V1)."""

from datetime import datetime, timedelta

VERDICT_OFFSETS_DAYS = {"fail": 0, "partial": 1, "pass": 3, "strong": 7}


def next_due(verdict: str, now: datetime) -> datetime:
    """Return when the Concept is due again after a Review with this verdict."""
    return now + timedelta(days=VERDICT_OFFSETS_DAYS[verdict])


def mastery(verdicts_newest_first: list[str]) -> str:
    """Derive the four-state Mastery State from final verdicts, newest first.

    Rule (M3): weak until proven otherwise, strong only on a streak —
    - no reviews yet                                         -> "never-reviewed"
    - the most recent verdict is "fail"                      -> "weak"
    - the two most recent verdicts are both pass or strong   -> "strong"
    - anything else (recovering, or only one good attempt)   -> "learning"
    """
    if not verdicts_newest_first:
        return "never-reviewed"
    if verdicts_newest_first[0] == "fail":
        return "weak"
    good = {"pass", "strong"}
    if len(verdicts_newest_first) >= 2 and set(verdicts_newest_first[:2]) <= good:
        return "strong"
    return "learning"
