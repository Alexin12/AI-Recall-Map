"""Concept detail endpoint: one Concept with mastery, due state, and history."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.confirmation import CONCEPT_COLUMNS, concept_from_row
from app.deps import UserConn
from app.extraction import Concept, Question
from app.reviews import Feedback, Review
from app.scheduler import mastery

router = APIRouter()


class ConceptDetail(Concept):
    """A Concept plus its derived mastery, due state, and full review history."""

    mastery: str
    due: bool
    next_due_at: datetime
    reviews: list[Review] = []


# Registered before /concepts/{concept_id} so "unclassified" isn't read as an id.
@router.get("/concepts/unclassified", response_model=list[Concept])
async def list_unclassified(conn: UserConn) -> list[Concept]:
    """The inbox: the user's Concepts with no Topic yet (ADR-0005)."""
    rows = await conn.execute(
        text(
            f"SELECT {CONCEPT_COLUMNS} FROM concepts "
            "WHERE topic_id IS NULL ORDER BY created_at"
        )
    )
    return [concept_from_row(r) for r in rows]


@router.get("/concepts/{concept_id}", response_model=ConceptDetail)
async def concept_detail(concept_id: str, conn: UserConn) -> ConceptDetail:
    """Everything about one Concept (404 if it isn't the user's)."""
    found = await conn.execute(
        text(
            f"SELECT {CONCEPT_COLUMNS}, next_due_at, "
            "(confirmed AND scheduled AND next_due_at <= now()) AS due "
            "FROM concepts WHERE id = :id"
        ),
        {"id": concept_id},
    )
    row = found.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

    q_rows = await conn.execute(
        text(
            "SELECT id, concept_id, kind, prompt FROM questions "
            "WHERE concept_id = :concept_id ORDER BY kind"
        ),
        {"concept_id": concept_id},
    )
    questions = [
        Question(id=str(q.id), concept_id=str(q.concept_id), kind=q.kind, prompt=q.prompt)
        for q in q_rows
    ]
    r_rows = (
        await conn.execute(
            text(
                "SELECT id, concept_id, question_id, answer, verdict, ai_verdict, feedback, "
                "created_at FROM reviews WHERE concept_id = :concept_id "
                "ORDER BY created_at DESC"
            ),
            {"concept_id": concept_id},
        )
    ).all()
    reviews = [
        Review(
            id=str(r.id),
            concept_id=str(r.concept_id),
            question_id=str(r.question_id),
            answer=r.answer,
            verdict=r.verdict,
            ai_verdict=r.ai_verdict,
            verdict_overridden=r.verdict != r.ai_verdict,
            feedback=Feedback(**r.feedback),
            next_due_at=row.next_due_at,
            created_at=r.created_at,
        )
        for r in r_rows
    ]
    base = concept_from_row(row, questions)
    return ConceptDetail(
        **base.model_dump(),
        mastery=mastery([r.verdict for r in reviews]),
        due=row.due,
        next_due_at=row.next_due_at,
        reviews=reviews,
    )
