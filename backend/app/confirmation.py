"""Confirmation endpoints: edit, delete, toggle-schedule, and confirm Concepts."""

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn
from app.extraction import Concept, Question

router = APIRouter()

CONCEPT_COLUMNS = (
    "id, topic_id, material_id, name, explanation, source_snippet, "
    "goal_relevance, confidence, scheduled, confirmed, created_at"
)


class ConceptEdit(BaseModel):
    """Partial edit of a Concept before confirming; omitted fields keep their values."""

    name: str | None = None
    explanation: str | None = None
    scheduled: bool | None = None
    goal_relevance: Literal["irrelevant", "supporting", "core"] | None = None


def concept_from_row(row, questions: list[Question] | None = None) -> Concept:
    return Concept(
        id=str(row.id),
        topic_id=str(row.topic_id),
        material_id=str(row.material_id),
        name=row.name,
        explanation=row.explanation,
        source_snippet=row.source_snippet,
        goal_relevance=row.goal_relevance,
        confidence=row.confidence,
        scheduled=row.scheduled,
        confirmed=row.confirmed,
        created_at=row.created_at,
        questions=questions or [],
    )


@router.patch("/concepts/{concept_id}", response_model=Concept)
async def edit_concept(concept_id: str, body: ConceptEdit, conn: UserConn) -> Concept:
    """Update a Concept's name, explanation, scheduled flag, or relevance override.

    A relevance override is the user's final say (story 14): it also recomputes
    scheduled (core/supporting reviewed, irrelevant browsable) unless the body
    sets scheduled explicitly.
    """
    if body.goal_relevance is not None and body.scheduled is None:
        body.scheduled = body.goal_relevance in ("core", "supporting")
    result = await conn.execute(
        text(
            "UPDATE concepts SET "
            "name = COALESCE(:name, name), "
            "explanation = COALESCE(:explanation, explanation), "
            "scheduled = COALESCE(:scheduled, scheduled), "
            "goal_relevance = COALESCE(:goal_relevance, goal_relevance) "
            f"WHERE id = :id RETURNING {CONCEPT_COLUMNS}"
        ),
        {
            "id": concept_id,
            "name": body.name,
            "explanation": body.explanation,
            "scheduled": body.scheduled,
            "goal_relevance": body.goal_relevance,
        },
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
    return concept_from_row(row)


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concept(concept_id: str, conn: UserConn) -> None:
    """Delete a Concept (its Questions cascade); 404 if it isn't the user's."""
    result = await conn.execute(
        text("DELETE FROM concepts WHERE id = :id RETURNING id"), {"id": concept_id}
    )
    if result.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")


@router.post("/materials/{material_id}/confirm", response_model=list[Concept])
async def confirm_material(material_id: str, conn: UserConn) -> list[Concept]:
    """Approve the Material's remaining Concepts: mark them all confirmed."""
    found = await conn.execute(
        text("SELECT id FROM materials WHERE id = :id"), {"id": material_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    rows = await conn.execute(
        text(
            "UPDATE concepts SET confirmed = true "
            f"WHERE material_id = :material_id RETURNING {CONCEPT_COLUMNS}"
        ),
        {"material_id": material_id},
    )
    return [concept_from_row(r) for r in rows]
