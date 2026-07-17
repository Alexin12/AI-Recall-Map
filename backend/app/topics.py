"""Topic endpoints: a Topic groups everything a learner studies about one subject."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn
from app.llm import score_relevance as llm_score_relevance

router = APIRouter()


class TopicCreate(BaseModel):
    """Request body for creating a Topic."""

    name: str


class TopicEdit(BaseModel):
    """Partial edit of a Topic; a null goal clears it (ADR-0006)."""

    goal: str | None = None


class Topic(BaseModel):
    """A single Topic row owned by the authenticated user."""

    id: str
    name: str
    goal: str | None = None
    created_at: datetime


def topic_from_row(r) -> Topic:
    return Topic(id=str(r.id), name=r.name, goal=r.goal, created_at=r.created_at)


@router.get("/topics", response_model=list[Topic])
async def list_topics(conn: UserConn) -> list[Topic]:
    """Return the current user's Topics (RLS hides everyone else's)."""
    result = await conn.execute(
        text("SELECT id, name, goal, created_at FROM topics ORDER BY created_at")
    )
    return [topic_from_row(r) for r in result]


@router.post("/topics", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def create_topic(body: TopicCreate, conn: UserConn) -> Topic:
    """Insert a Topic owned by the current user (user_id defaults to auth.uid())."""
    result = await conn.execute(
        text(
            "INSERT INTO topics (name) VALUES (:name) "
            "RETURNING id, name, goal, created_at"
        ),
        {"name": body.name},
    )
    return topic_from_row(result.one())


@router.patch("/topics/{topic_id}", response_model=Topic)
async def edit_topic(topic_id: str, body: TopicEdit, conn: UserConn) -> Topic:
    """Set, change, or clear the Topic's Goal (404 if not the user's Topic)."""
    result = await conn.execute(
        text(
            "UPDATE topics SET goal = :goal WHERE id = :id "
            "RETURNING id, name, goal, created_at"
        ),
        {"id": topic_id, "goal": body.goal},
    )
    r = result.first()
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    if body.goal is not None:
        await rescore_topic(conn, topic_id, body.goal)
    else:
        # Clearing the Goal: relevance is unknowable again, so unscore and
        # unschedule everything (the Topic stays browsable, never due).
        await conn.execute(
            text(
                "UPDATE concepts SET goal_relevance = NULL, scheduled = false "
                "WHERE topic_id = :topic_id"
            ),
            {"topic_id": topic_id},
        )
    return topic_from_row(r)


async def rescore_topic(conn, topic_id: str, goal: str) -> None:
    """Phase 2 (ADR-0006): score the Topic's Concepts against its Goal and
    schedule the ones that matter (core/supporting); irrelevant stays browsable."""
    rows = await conn.execute(
        text("SELECT id, name, explanation FROM concepts WHERE topic_id = :topic_id"),
        {"topic_id": topic_id},
    )
    concepts = [
        {"id": str(r.id), "name": r.name, "explanation": r.explanation} for r in rows
    ]
    if not concepts:
        return
    scores = await llm_score_relevance(goal, concepts)
    for concept_id, relevance in scores.items():
        await conn.execute(
            text(
                "UPDATE concepts SET goal_relevance = :relevance, "
                "scheduled = :scheduled WHERE id = :id"
            ),
            {
                "id": concept_id,
                "relevance": relevance,
                "scheduled": relevance in ("core", "supporting"),
            },
        )
