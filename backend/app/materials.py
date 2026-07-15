"""Material endpoints: a Material is one pasted source of text inside a Topic."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn

# Cap on pasted characters per Material. Extraction runs in-request (ADR-0004:
# no background queue), so this bounds per-request extraction latency.
MATERIAL_MAX_CHARS = 50_000

router = APIRouter()


class MaterialCreate(BaseModel):
    """Request body for pasting a Material into a Topic."""

    content: str


class Material(BaseModel):
    """A single Material row owned by the authenticated user."""

    id: str
    topic_id: str
    content: str
    created_at: datetime


async def require_own_topic(topic_id: str, conn) -> None:
    """404 unless the Topic exists and belongs to the user (RLS hides others')."""
    found = await conn.execute(
        text("SELECT id FROM topics WHERE id = :topic_id"), {"topic_id": topic_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")


@router.get("/topics/{topic_id}/materials", response_model=list[Material])
async def list_materials(topic_id: str, conn: UserConn) -> list[Material]:
    """Return the Materials pasted into this Topic (RLS hides everyone else's)."""
    await require_own_topic(topic_id, conn)
    result = await conn.execute(
        text(
            "SELECT id, topic_id, content, created_at FROM materials "
            "WHERE topic_id = :topic_id ORDER BY created_at"
        ),
        {"topic_id": topic_id},
    )
    return [
        Material(
            id=str(r.id), topic_id=str(r.topic_id), content=r.content, created_at=r.created_at
        )
        for r in result
    ]


@router.post(
    "/topics/{topic_id}/materials",
    response_model=Material,
    status_code=status.HTTP_201_CREATED,
)
async def create_material(topic_id: str, body: MaterialCreate, conn: UserConn) -> Material:
    """Insert a Material into the user's Topic (user_id defaults to auth.uid())."""
    await require_own_topic(topic_id, conn)
    if len(body.content) > MATERIAL_MAX_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Material is too large: {len(body.content)} characters, "
                f"the limit is {MATERIAL_MAX_CHARS}. Please split the material "
                "into smaller pieces and paste them separately."
            ),
        )
    result = await conn.execute(
        text(
            "INSERT INTO materials (topic_id, content) VALUES (:topic_id, :content) "
            "RETURNING id, topic_id, content, created_at"
        ),
        {"topic_id": topic_id, "content": body.content},
    )
    r = result.one()
    return Material(
        id=str(r.id), topic_id=str(r.topic_id), content=r.content, created_at=r.created_at
    )
