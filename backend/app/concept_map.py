"""Concept Map endpoint: a Topic's Concepts and relationship rows (ADR-0002)."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn

router = APIRouter()


class MapNode(BaseModel):
    """One Concept as a map node."""

    id: str
    name: str
    goal_relevance: str
    scheduled: bool
    confirmed: bool


class Relationship(BaseModel):
    """One relationship row between two Concepts (plain Postgres row, ADR-0002)."""

    id: str
    from_concept_id: str
    to_concept_id: str
    kind: str


class ConceptMap(BaseModel):
    """Everything the frontend needs to render the Topic's Concept Map."""

    nodes: list[MapNode]
    relationships: list[Relationship]


@router.get("/topics/{topic_id}/map", response_model=ConceptMap)
async def concept_map(topic_id: str, conn: UserConn) -> ConceptMap:
    """The Topic's Concepts and relationships (404 if not the user's Topic)."""
    found = await conn.execute(
        text("SELECT id FROM topics WHERE id = :id"), {"id": topic_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    node_rows = await conn.execute(
        text(
            "SELECT id, name, goal_relevance, scheduled, confirmed FROM concepts "
            "WHERE topic_id = :topic_id ORDER BY created_at"
        ),
        {"topic_id": topic_id},
    )
    rel_rows = await conn.execute(
        text(
            "SELECT id, from_concept_id, to_concept_id, kind FROM concept_relationships "
            "WHERE topic_id = :topic_id ORDER BY created_at"
        ),
        {"topic_id": topic_id},
    )
    return ConceptMap(
        nodes=[
            MapNode(
                id=str(r.id),
                name=r.name,
                goal_relevance=r.goal_relevance,
                scheduled=r.scheduled,
                confirmed=r.confirmed,
            )
            for r in node_rows
        ],
        relationships=[
            Relationship(
                id=str(r.id),
                from_concept_id=str(r.from_concept_id),
                to_concept_id=str(r.to_concept_id),
                kind=r.kind,
            )
            for r in rel_rows
        ],
    )
