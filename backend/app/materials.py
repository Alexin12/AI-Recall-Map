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
    """A single Material row; topic_id is NULL for a raw unsorted paste (ADR-0005).

    concept_names lists the names of Concepts extracted from this Material
    (issue #29) — display tags instead of truncated raw content."""

    id: str
    topic_id: str | None
    content: str
    created_at: datetime
    concept_names: list[str] = []


def material_from_row(r) -> Material:
    return Material(
        id=str(r.id),
        topic_id=str(r.topic_id) if r.topic_id else None,
        content=r.content,
        created_at=r.created_at,
        concept_names=list(getattr(r, "concept_names", None) or []),
    )


def require_material_size(content: str) -> None:
    """413 when a paste exceeds the in-request extraction cap (ADR-0004)."""
    if len(content) > MATERIAL_MAX_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Material is too large: {len(content)} characters, "
                f"the limit is {MATERIAL_MAX_CHARS}. Please split the material "
                "into smaller pieces and paste them separately."
            ),
        )


async def require_own_topic(topic_id: str, conn) -> None:
    """404 unless the Topic exists and belongs to the user (RLS hides others')."""
    found = await conn.execute(
        text("SELECT id FROM topics WHERE id = :topic_id"), {"topic_id": topic_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")


@router.get("/topics/{topic_id}/materials", response_model=list[Material])
async def list_materials(topic_id: str, conn: UserConn) -> list[Material]:
    """Return the Materials pasted into this Topic (RLS hides everyone else's),
    each carrying the names of the Concepts extracted from it (issue #29)."""
    await require_own_topic(topic_id, conn)
    result = await conn.execute(
        text(
            "SELECT m.id, m.topic_id, m.content, m.created_at, "
            "COALESCE(array_agg(c.name) FILTER (WHERE c.name IS NOT NULL), '{}') "
            "AS concept_names "
            "FROM materials m LEFT JOIN concepts c ON c.material_id = m.id "
            "WHERE m.topic_id = :topic_id "
            "GROUP BY m.id ORDER BY m.created_at"
        ),
        {"topic_id": topic_id},
    )
    return [
        Material(
            id=str(r.id),
            topic_id=str(r.topic_id),
            content=r.content,
            created_at=r.created_at,
            concept_names=list(r.concept_names),
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
    require_material_size(body.content)
    result = await conn.execute(
        text(
            "INSERT INTO materials (topic_id, content) VALUES (:topic_id, :content) "
            "RETURNING id, topic_id, content, created_at"
        ),
        {"topic_id": topic_id, "content": body.content},
    )
    return material_from_row(result.one())


@router.post("/materials", response_model=Material, status_code=status.HTTP_201_CREATED)
async def create_unsorted_material(body: MaterialCreate, conn: UserConn) -> Material:
    """Global Home paste: a raw Material with no Topic chosen up front (ADR-0005)."""
    require_material_size(body.content)
    result = await conn.execute(
        text(
            "INSERT INTO materials (content) VALUES (:content) "
            "RETURNING id, topic_id, content, created_at"
        ),
        {"content": body.content},
    )
    return material_from_row(result.one())
