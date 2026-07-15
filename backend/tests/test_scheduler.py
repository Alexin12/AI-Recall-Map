"""Scheduler: a pure function mapping a Review Verdict to the next due date."""

from datetime import datetime, timedelta, timezone

from app.scheduler import next_due

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)


def test_verdicts_map_to_fixed_offsets():
    assert next_due("fail", NOW) == NOW
    assert next_due("partial", NOW) == NOW + timedelta(days=1)
    assert next_due("pass", NOW) == NOW + timedelta(days=3)
    assert next_due("strong", NOW) == NOW + timedelta(days=7)
