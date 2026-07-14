"""Goal endpoints: each user has exactly one editable learning Goal."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn

router = APIRouter()


class GoalWrite(BaseModel):
    """Request body for setting or editing the Goal."""

    content: str


class Goal(BaseModel):
    """The current user's single Goal."""

    id: str
    content: str
    created_at: datetime
    updated_at: datetime


@router.get("/goal", response_model=Goal)
async def get_goal(conn: UserConn) -> Goal:
    """Return the current user's Goal, or 404 if it is not set yet."""
    result = await conn.execute(
        text("SELECT id, content, created_at, updated_at FROM goals")
    )
    r = result.one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Goal not set")
    return Goal(
        id=str(r.id), content=r.content, created_at=r.created_at, updated_at=r.updated_at
    )


@router.put("/goal", response_model=Goal)
async def put_goal(body: GoalWrite, conn: UserConn) -> Goal:
    """Create the user's Goal, or replace its content if it already exists."""
    result = await conn.execute(
        text(
            "INSERT INTO goals (content) VALUES (:content) "
            "ON CONFLICT (user_id) DO UPDATE "
            "SET content = excluded.content, updated_at = now() "
            "RETURNING id, content, created_at, updated_at"
        ),
        {"content": body.content},
    )
    r = result.one()
    return Goal(
        id=str(r.id), content=r.content, created_at=r.created_at, updated_at=r.updated_at
    )
