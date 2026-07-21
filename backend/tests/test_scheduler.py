"""Scheduler: a pure function mapping a Review Verdict to the next due date."""

from datetime import datetime, timedelta, timezone

from app.scheduler import next_due

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)


def test_verdicts_map_to_fixed_offsets():
    assert next_due("fail", NOW) == NOW
    assert next_due("partial", NOW) == NOW + timedelta(days=1)
    assert next_due("pass", NOW) == NOW + timedelta(days=3)
    assert next_due("strong", NOW) == NOW + timedelta(days=7)


def test_mastery_from_review_history():
    from app.scheduler import mastery

    # Verdicts are newest-first, as review history is stored.
    assert mastery([]) == "never-reviewed"  # zero reviews is its own state, not weak
    assert mastery(["fail"]) == "weak"  # latest attempt failed
    assert mastery(["fail", "strong", "strong"]) == "weak"  # a fail resets mastery
    assert mastery(["partial"]) == "learning"
    assert mastery(["pass"]) == "learning"  # one good attempt is not yet strong
    assert mastery(["strong"]) == "learning"
    assert mastery(["pass", "partial"]) == "learning"
    assert mastery(["pass", "strong"]) == "strong"  # two good attempts in a row
    assert mastery(["strong", "pass", "fail"]) == "strong"  # older fail forgiven
