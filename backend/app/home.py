"""Global Home summary: everything the Home screen needs in one request.

One purpose-built contract (Hard Rule) — no per-Concept calls, no scheduling
state derived by joining data in React.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.confirmation import CONCEPT_COLUMNS, concept_from_row
from app.deps import UserConn
from app.extraction import Concept
from app.scheduler import mastery

router = APIRouter()

NEXT_DAYS = 5
RECENTLY_LEARNED_LIMIT = 5
MASTERY_STATES = ["never-reviewed", "weak", "learning", "strong"]

# Table-qualified so this can join reviews without ambiguous column names
# (both tables have id/created_at) while staying in sync with CONCEPT_COLUMNS.
CONCEPT_COLUMNS_QUALIFIED = ", ".join(f"c.{col.strip()}" for col in CONCEPT_COLUMNS.split(","))


class DueDay(BaseModel):
    """One day's due count in the next-five-days plan."""

    date: date
    count: int


class TopicMasteryCounts(BaseModel):
    """A Topic's confirmed Concepts bucketed into the four Mastery States."""

    topic_id: str
    topic_name: str
    counts: dict[str, int]


class HomeSummary(BaseModel):
    """Everything the Global Home needs in one request."""

    review_due_count: int
    next_five_days: list[DueDay]
    recently_learned: list[Concept]
    topic_mastery: list[TopicMasteryCounts]
    inbox_count: int


@router.get("/home/summary", response_model=HomeSummary)
async def home_summary(conn: UserConn) -> HomeSummary:
    """One-request summary for the Global Home: review-needed count, the next
    five days' due counts, recently reviewed Concepts, each Topic's Mastery
    distribution, and the Inbox count.

    "Recently learned" is the most recently *reviewed* Concepts (by the
    review's created_at) — confirmation itself has no timestamp of its own.
    """
    today = datetime.now(timezone.utc).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    review_due_count = (
        await conn.execute(
            text(
                "SELECT COUNT(*) FROM concepts "
                "WHERE confirmed AND scheduled AND next_due_at <= now()"
            )
        )
    ).scalar_one()

    range_end = today_start + timedelta(days=NEXT_DAYS)
    day_rows = await conn.execute(
        text(
            "SELECT (next_due_at AT TIME ZONE 'UTC')::date AS due_date, COUNT(*) AS n "
            "FROM concepts WHERE confirmed AND scheduled "
            "AND next_due_at >= :start AND next_due_at < :end "
            "GROUP BY due_date"
        ),
        {"start": today_start, "end": range_end},
    )
    counts_by_date = {r.due_date: r.n for r in day_rows}
    next_five_days = [
        DueDay(
            date=today + timedelta(days=offset),
            count=counts_by_date.get(today + timedelta(days=offset), 0),
        )
        for offset in range(NEXT_DAYS)
    ]

    recent_rows = await conn.execute(
        text(
            f"SELECT {CONCEPT_COLUMNS_QUALIFIED} FROM concepts c "
            "JOIN reviews r ON r.concept_id = c.id "
            "GROUP BY c.id "
            "ORDER BY MAX(r.created_at) DESC "
            f"LIMIT {RECENTLY_LEARNED_LIMIT}"
        )
    )
    recently_learned = [concept_from_row(r) for r in recent_rows]

    topic_rows = await conn.execute(text("SELECT id, name FROM topics ORDER BY created_at"))
    topics = [(str(r.id), r.name) for r in topic_rows]
    counts_by_topic = {tid: dict.fromkeys(MASTERY_STATES, 0) for tid, _ in topics}

    verdict_rows = await conn.execute(
        text(
            "SELECT c.id AS concept_id, c.topic_id, r.verdict FROM concepts c "
            "LEFT JOIN reviews r ON r.concept_id = c.id "
            "WHERE c.confirmed AND c.topic_id IS NOT NULL "
            "ORDER BY c.id, r.created_at DESC"
        )
    )
    verdicts_by_concept: dict[str, list[str]] = {}
    topic_by_concept: dict[str, str] = {}
    for row in verdict_rows:
        cid = str(row.concept_id)
        topic_by_concept[cid] = str(row.topic_id)
        if row.verdict is not None:
            verdicts_by_concept.setdefault(cid, []).append(row.verdict)

    for cid, tid in topic_by_concept.items():
        state = mastery(verdicts_by_concept.get(cid, []))
        counts_by_topic[tid][state] += 1

    topic_mastery = [
        TopicMasteryCounts(topic_id=tid, topic_name=name, counts=counts_by_topic[tid])
        for tid, name in topics
    ]

    inbox_count = (
        await conn.execute(text("SELECT COUNT(*) FROM concepts WHERE topic_id IS NULL"))
    ).scalar_one()

    return HomeSummary(
        review_due_count=review_due_count,
        next_five_days=next_five_days,
        recently_learned=recently_learned,
        topic_mastery=topic_mastery,
        inbox_count=inbox_count,
    )
