"""Review endpoints: due list, flashcard answering with grading, rescheduling."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.confirmation import CONCEPT_COLUMNS, concept_from_row
from app.deps import UserConn
from app.extraction import Concept, Question
from app.llm import GradeResult
from app.llm import grade_answer as llm_grade_answer
from app.scheduler import next_due

router = APIRouter()


@router.get("/topics/{topic_id}/due", response_model=list[Concept])
async def due_list(topic_id: str, conn: UserConn) -> list[Concept]:
    """Confirmed, scheduled Concepts of this Topic that are due now, oldest first."""
    found = await conn.execute(
        text("SELECT id FROM topics WHERE id = :id"), {"id": topic_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    rows = await conn.execute(
        text(
            f"SELECT {CONCEPT_COLUMNS} FROM concepts "
            "WHERE topic_id = :topic_id AND confirmed AND scheduled "
            "AND next_due_at <= now() ORDER BY next_due_at"
        ),
        {"topic_id": topic_id},
    )
    concepts = [concept_from_row(r) for r in rows]
    for concept in concepts:
        q_rows = await conn.execute(
            text(
                "SELECT id, concept_id, kind, prompt FROM questions "
                "WHERE concept_id = :concept_id ORDER BY kind"
            ),
            {"concept_id": concept.id},
        )
        concept.questions = [
            Question(id=str(q.id), concept_id=str(q.concept_id), kind=q.kind, prompt=q.prompt)
            for q in q_rows
        ]
    return concepts


class AnswerBody(BaseModel):
    """The learner's answer to a Question."""

    answer: str


class Feedback(BaseModel):
    """Structured grading feedback shown with the verdict."""

    correct_points: list[str]
    missing_points: list[str]
    misconceptions: list[str]


class Review(BaseModel):
    """One persisted review attempt on a Concept.

    `verdict` is the final verdict the Scheduler reads; `ai_verdict` is what
    the AI originally said. They differ only after a user override.
    """

    id: str
    concept_id: str
    question_id: str
    answer: str
    verdict: str
    ai_verdict: str
    verdict_overridden: bool
    feedback: Feedback
    next_due_at: datetime
    created_at: datetime


@router.post("/questions/{question_id}/answer", response_model=Review)
async def answer_question(question_id: str, body: AnswerBody, conn: UserConn) -> Review:
    """Grade the answer, persist the Review, and reschedule the Concept."""
    found = await conn.execute(
        text(
            "SELECT q.id, q.concept_id, q.prompt, c.explanation, c.source_snippet "
            "FROM questions q JOIN concepts c ON c.id = q.concept_id "
            "WHERE q.id = :id"
        ),
        {"id": question_id},
    )
    question = found.first()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    grade: GradeResult = await llm_grade_answer(
        question.explanation, question.source_snippet, question.prompt, body.answer
    )
    feedback = Feedback(
        correct_points=grade.correct_points,
        missing_points=grade.missing_points,
        misconceptions=grade.misconceptions,
    )
    row = (
        await conn.execute(
            text(
                "INSERT INTO reviews (concept_id, question_id, answer, verdict, ai_verdict, "
                "feedback) VALUES (:concept_id, :question_id, :answer, :verdict, :verdict, "
                "CAST(:feedback AS jsonb)) "
                "RETURNING id, concept_id, question_id, answer, verdict, ai_verdict, created_at"
            ),
            {
                "concept_id": str(question.concept_id),
                "question_id": question_id,
                "answer": body.answer,
                "verdict": grade.verdict,
                "feedback": feedback.model_dump_json(),
            },
        )
    ).one()
    due_at = next_due(grade.verdict, row.created_at)
    await conn.execute(
        text("UPDATE concepts SET next_due_at = :due_at WHERE id = :id"),
        {"due_at": due_at, "id": str(question.concept_id)},
    )
    return Review(
        id=str(row.id),
        concept_id=str(row.concept_id),
        question_id=str(row.question_id),
        answer=row.answer,
        verdict=row.verdict,
        ai_verdict=row.ai_verdict,
        verdict_overridden=False,
        feedback=feedback,
        next_due_at=due_at,
        created_at=row.created_at,
    )


@router.get("/concepts/{concept_id}/reviews", response_model=list[Review])
async def list_reviews(concept_id: str, conn: UserConn) -> list[Review]:
    """The Concept's review history, newest first (404 if not the user's)."""
    found = await conn.execute(
        text("SELECT id, next_due_at FROM concepts WHERE id = :id"), {"id": concept_id}
    )
    concept = found.first()
    if concept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    rows = await conn.execute(
        text(
            "SELECT id, concept_id, question_id, answer, verdict, ai_verdict, feedback, "
            "created_at FROM reviews WHERE concept_id = :concept_id ORDER BY created_at DESC"
        ),
        {"concept_id": concept_id},
    )
    return [
        Review(
            id=str(r.id),
            concept_id=str(r.concept_id),
            question_id=str(r.question_id),
            answer=r.answer,
            verdict=r.verdict,
            ai_verdict=r.ai_verdict,
            verdict_overridden=r.verdict != r.ai_verdict,
            feedback=Feedback(**r.feedback),
            next_due_at=concept.next_due_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


class OverrideBody(BaseModel):
    """The learner's replacement verdict."""

    verdict: Literal["fail", "partial", "pass", "strong"]


@router.post("/reviews/{review_id}/override", response_model=Review)
async def override_verdict(review_id: str, body: OverrideBody, conn: UserConn) -> Review:
    """Replace the AI verdict with the learner's; reschedule from the final verdict."""
    result = await conn.execute(
        text(
            "UPDATE reviews SET verdict = :verdict WHERE id = :id "
            "RETURNING id, concept_id, question_id, answer, verdict, ai_verdict, "
            "feedback, created_at"
        ),
        {"verdict": body.verdict, "id": review_id},
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    due_at = next_due(row.verdict, row.created_at)
    await conn.execute(
        text("UPDATE concepts SET next_due_at = :due_at WHERE id = :id"),
        {"due_at": due_at, "id": str(row.concept_id)},
    )
    return Review(
        id=str(row.id),
        concept_id=str(row.concept_id),
        question_id=str(row.question_id),
        answer=row.answer,
        verdict=row.verdict,
        ai_verdict=row.ai_verdict,
        verdict_overridden=row.verdict != row.ai_verdict,
        feedback=Feedback(**row.feedback),
        next_due_at=due_at,
        created_at=row.created_at,
    )
