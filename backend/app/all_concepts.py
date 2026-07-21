"""All Concepts: one purpose-built, Topic-scoped listing contract (issue #77).

Returns everything the All Concepts page needs in a single request — no
per-Concept follow-up calls for review history or questions.
"""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn

router = APIRouter()


class AllConceptsRow(BaseModel):
    """One row of the All Concepts listing."""

    id: str
    name: str
    goal_relevance: Literal["irrelevant", "supporting", "core"] | None
    topic_id: str
    topic_name: str
    confirmed: bool
    last_reviewed_at: datetime | None
    last_verdict: Literal["fail", "partial", "pass", "strong"] | None
    # None when the Concept is unscheduled or its Topic has no Goal — there is
    # no schedule to show. A date, never a timestamp (story 46).
    next_due_date: date | None
    written_question: str | None
    written_answer: str | None


_RELEVANCE_ORDER = "CASE c.goal_relevance WHEN 'core' THEN 0 WHEN 'supporting' THEN 1 WHEN 'irrelevant' THEN 2 ELSE 3 END"


@router.get("/topics/{topic_id}/all-concepts", response_model=list[AllConceptsRow])
async def list_all_concepts(topic_id: str, conn: UserConn) -> list[AllConceptsRow]:
    """One request: name, relevance, Topic, latest Review, next due date, latest
    written Q&A, per Concept. Ordering: due-now, then nearest next-due, then
    relevance, then name (story 36)."""
    found = await conn.execute(text("SELECT id FROM topics WHERE id = :id"), {"id": topic_id})
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    rows = await conn.execute(
        text(
            "SELECT c.id, c.name, c.goal_relevance, c.topic_id, t.name AS topic_name, "
            "c.confirmed, c.scheduled, c.next_due_at, t.goal AS topic_goal, "
            "(c.confirmed AND c.scheduled AND c.next_due_at <= now()) AS due, "
            "lr.verdict AS last_verdict, lr.created_at AS last_reviewed_at, "
            "wq.prompt AS written_question, wa.answer AS written_answer "
            "FROM concepts c "
            "JOIN topics t ON t.id = c.topic_id "
            "LEFT JOIN LATERAL ("
            "  SELECT verdict, created_at FROM reviews "
            "  WHERE concept_id = c.id ORDER BY created_at DESC LIMIT 1"
            ") lr ON true "
            "LEFT JOIN questions wq ON wq.concept_id = c.id AND wq.kind = 'written' "
            "LEFT JOIN LATERAL ("
            "  SELECT answer FROM reviews "
            "  WHERE question_id = wq.id ORDER BY created_at DESC LIMIT 1"
            ") wa ON true "
            "WHERE c.topic_id = :topic_id "
            "ORDER BY due DESC, "
            "CASE WHEN c.scheduled AND t.goal IS NOT NULL THEN c.next_due_at END ASC NULLS LAST, "
            f"{_RELEVANCE_ORDER}, c.name"
        ),
        {"topic_id": topic_id},
    )
    result = []
    for r in rows:
        show_next_due = r.scheduled and r.topic_goal is not None
        result.append(
            AllConceptsRow(
                id=str(r.id),
                name=r.name,
                goal_relevance=r.goal_relevance,
                topic_id=str(r.topic_id),
                topic_name=r.topic_name,
                confirmed=r.confirmed,
                last_reviewed_at=r.last_reviewed_at,
                last_verdict=r.last_verdict,
                next_due_date=r.next_due_at.date() if show_next_due else None,
                written_question=r.written_question,
                written_answer=r.written_answer,
            )
        )
    return result
