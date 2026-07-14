"""Topic endpoints: a Topic groups everything a learner studies about one subject."""

from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn

router = APIRouter()


class TopicCreate(BaseModel):
    """Request body for creating a Topic."""

    name: str


class Topic(BaseModel):
    """A single Topic row owned by the authenticated user."""

    id: str
    name: str
    created_at: datetime


@router.get("/topics", response_model=list[Topic])
async def list_topics(conn: UserConn) -> list[Topic]:
    """Return the current user's Topics (RLS hides everyone else's)."""
    result = await conn.execute(
        text("SELECT id, name, created_at FROM topics ORDER BY created_at")
    )
    return [Topic(id=str(r.id), name=r.name, created_at=r.created_at) for r in result]


@router.post("/topics", response_model=Topic, status_code=status.HTTP_201_CREATED)
async def create_topic(body: TopicCreate, conn: UserConn) -> Topic:
    """Insert a Topic owned by the current user (user_id defaults to auth.uid())."""
    result = await conn.execute(
        text("INSERT INTO topics (name) VALUES (:name) RETURNING id, name, created_at"),
        {"name": body.name},
    )
    r = result.one()
    return Topic(id=str(r.id), name=r.name, created_at=r.created_at)
