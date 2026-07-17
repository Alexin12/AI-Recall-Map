"""Concept Map endpoint: a Topic's Concepts as a hierarchy tree (ADR-0007)."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn

router = APIRouter()


class TreeNode(BaseModel):
    """One Concept as a tree node, expandable down to its children."""

    id: str
    name: str
    display_label: str
    goal_relevance: str | None
    scheduled: bool
    confirmed: bool
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
