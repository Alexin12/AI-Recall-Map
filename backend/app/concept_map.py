"""Concept Map endpoint: a Topic's Concepts as a hierarchy tree (ADR-0007)."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn
from app.scheduler import mastery

router = APIRouter()


class TreeNode(BaseModel):
    """One Concept as a tree node, expandable down to its children."""

    id: str
    name: str
    display_label: str
    goal_relevance: str | None
    scheduled: bool
    confirmed: bool
    mastery: str
    children: list["TreeNode"] = []


class ConceptMap(BaseModel):
    """The Topic's Concept Map: root Concepts down to their details."""

    tree: list[TreeNode]


@router.get("/topics/{topic_id}/map", response_model=ConceptMap)
async def concept_map(topic_id: str, conn: UserConn) -> ConceptMap:
    """The Topic's Concepts as a tree of parent pointers (404 if not the user's)."""
    found = await conn.execute(
        text("SELECT id FROM topics WHERE id = :id"), {"id": topic_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    rows = (
        await conn.execute(
            text(
                "SELECT id, name, goal_relevance, scheduled, confirmed, "
                "parent_concept_id, second_parent_name FROM concepts "
                "WHERE topic_id = :topic_id ORDER BY created_at"
            ),
            {"topic_id": topic_id},
        )
    ).all()
    # All verdicts for the Topic in one query (newest first), grouped per Concept.
    verdict_rows = (
        await conn.execute(
            text(
                "SELECT r.concept_id, r.verdict FROM reviews r "
                "JOIN concepts c ON c.id = r.concept_id "
                "WHERE c.topic_id = :topic_id ORDER BY r.created_at DESC"
            ),
            {"topic_id": topic_id},
        )
    ).all()
    verdicts: dict[str, list[str]] = {}
    for v in verdict_rows:
        verdicts.setdefault(str(v.concept_id), []).append(v.verdict)
    nodes = {
        str(r.id): TreeNode(
            id=str(r.id),
            name=r.name,
            # A second parent is display-only (ADR-0007): a slash label keeps
            # the tree single-parent without losing the second relationship.
            display_label=(
                f"{r.name} / {r.second_parent_name}" if r.second_parent_name else r.name
            ),
            goal_relevance=r.goal_relevance,
            scheduled=r.scheduled,
            confirmed=r.confirmed,
            mastery=mastery(verdicts.get(str(r.id), [])),
            children=[],
        )
        for r in rows
    }
    roots: list[TreeNode] = []
    for r in rows:
        node = nodes[str(r.id)]
        parent = nodes.get(str(r.parent_concept_id)) if r.parent_concept_id else None
        # A parent outside this Topic (e.g. moved away) leaves the node a root.
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)
    return ConceptMap(tree=roots)
