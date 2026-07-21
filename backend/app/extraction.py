"""Extraction endpoints: turn a Material into persisted Concepts and Questions.

Extraction runs in-request and streams NDJSON progress over the HTTP response
(ADR-0004: no background queue). The LLM call lives in app.llm; this module
owns the route, persistence, and response shape.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn
from app.llm import extract_concepts as llm_extract_concepts
from app.llm import propose_topics as llm_propose_topics
from app.llm import route_concepts as llm_route_concepts
from app.llm import score_relevance as llm_score_relevance

router = APIRouter()
logger = logging.getLogger(__name__)


class Question(BaseModel):
    """One way to test a Concept: a flashcard or written-explanation prompt."""

    id: str
    concept_id: str
    kind: str
    prompt: str


class Concept(BaseModel):
    """One persisted Concept with its Questions."""

    id: str
    topic_id: str | None
    material_id: str
    name: str
    explanation: str
    source_snippet: str
    goal_relevance: str | None
    confidence: float
    scheduled: bool
    confirmed: bool
    created_at: datetime
    # AI-enriched format (ADR-0008): a fixed six-field template layered on
    # top of name/explanation/source_snippet. analogy and technical_explanation
    # are always required; code_snippet is extract-only ("none" when absent);
    # core_claim is optional; ai_supplemented_fields flags any of
    # {analogy, technical_explanation, core_claim} the model generated rather
    # than found in the Material.
    analogy: str
    technical_explanation: str
    code_snippet: str
    core_claim: str | None
    ai_supplemented_fields: list[str] = []
    questions: list[Question] = []


async def require_own_material(material_id: str, conn):
    """Return the Material row, or 404 if it isn't visible to this user (RLS)."""
    found = await conn.execute(
        text("SELECT id, topic_id, content FROM materials WHERE id = :id"),
        {"id": material_id},
    )
    row = found.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    return row


async def fetch_topic_goal(conn, topic_id) -> str | None:
    """Return the Topic's Goal (ADR-0006: Goal lives on the Topic), or None."""
    if topic_id is None:
        return None
    result = await conn.execute(
        text("SELECT goal FROM topics WHERE id = :id"), {"id": str(topic_id)}
    )
    row = result.first()
    return row.goal if row else None


async def insert_concept(
    conn, material, extracted, goal: str | None, topic_id: str | None = None
) -> Concept:
    """Persist one extracted Concept plus its flashcard and written Questions.

    topic_id overrides the Material's own Topic for the routed flow (ADR-0005);
    None there means unclassified (the inbox).
    """
    if topic_id is None and material.topic_id is not None:
        topic_id = str(material.topic_id)
    row = (
        await conn.execute(
            text(
                "INSERT INTO concepts (topic_id, material_id, name, explanation, "
                "source_snippet, goal_relevance, confidence, scheduled, analogy, "
                "technical_explanation, code_snippet, core_claim, ai_supplemented_fields) "
                "VALUES (:topic_id, :material_id, :name, :explanation, "
                ":source_snippet, :goal_relevance, :confidence, :scheduled, :analogy, "
                ":technical_explanation, :code_snippet, :core_claim, :ai_supplemented_fields) "
                "RETURNING id, topic_id, material_id, name, explanation, "
                "source_snippet, goal_relevance, confidence, scheduled, confirmed, created_at, "
                "analogy, technical_explanation, code_snippet, core_claim, ai_supplemented_fields"
            ),
            {
                "topic_id": topic_id,
                "material_id": str(material.id),
                "name": extracted.name,
                "explanation": extracted.explanation,
                "source_snippet": extracted.source_snippet,
                # No Goal on the Topic means relevance is unknowable: leave it
                # NULL and schedule nothing (ADR-0006).
                "goal_relevance": extracted.goal_relevance if goal else None,
                "confidence": extracted.confidence,
                "scheduled": bool(goal) and extracted.goal_relevance in ("core", "supporting"),
                "analogy": extracted.analogy,
                "technical_explanation": extracted.technical_explanation,
                "code_snippet": extracted.code_snippet,
                "core_claim": extracted.core_claim,
                "ai_supplemented_fields": extracted.ai_supplemented_fields,
            },
        )
    ).one()
    questions = []
    for kind, prompt in [
        ("flashcard", extracted.flashcard_prompt),
        ("written", extracted.written_prompt),
    ]:
        q = (
            await conn.execute(
                text(
                    "INSERT INTO questions (concept_id, kind, prompt) "
                    "VALUES (:concept_id, :kind, :prompt) "
                    "RETURNING id, concept_id, kind, prompt"
                ),
                {"concept_id": str(row.id), "kind": kind, "prompt": prompt},
            )
        ).one()
        questions.append(
            Question(id=str(q.id), concept_id=str(q.concept_id), kind=q.kind, prompt=q.prompt)
        )
    return Concept(
        id=str(row.id),
        topic_id=str(row.topic_id) if row.topic_id else None,
        material_id=str(row.material_id),
        name=row.name,
        explanation=row.explanation,
        source_snippet=row.source_snippet,
        goal_relevance=row.goal_relevance,
        confidence=row.confidence,
        scheduled=row.scheduled,
        confirmed=row.confirmed,
        created_at=row.created_at,
        analogy=row.analogy,
        technical_explanation=row.technical_explanation,
        code_snippet=row.code_snippet,
        core_claim=row.core_claim,
        ai_supplemented_fields=list(row.ai_supplemented_fields),
        questions=questions,
    )


async def link_parents(conn, extracted, concepts: list[Concept]) -> None:
    """Persist the hierarchy (ADR-0007): resolve each Concept's parent_name to
    its sibling from the same extraction; unknown or self parents stay roots."""
    ids_by_name = {c.name: c.id for c in concepts}
    for e, c in zip(extracted, concepts):
        parent_id = ids_by_name.get(e.parent_name) if e.parent_name else None
        if parent_id == c.id:
            parent_id = None
        if parent_id is None and e.second_parent_name is None:
            continue
        await conn.execute(
            text(
                "UPDATE concepts SET parent_concept_id = :parent_id, "
                "second_parent_name = :second WHERE id = :id"
            ),
            {"id": c.id, "parent_id": parent_id, "second": e.second_parent_name},
        )


async def score_routed_concepts(conn, topics: list[dict], concepts: list[Concept]) -> None:
    """Phase 2 for the routed flow (ADR-0006): score the just-routed Concepts of
    each Goal-carrying Topic and schedule core/supporting; mirror onto the models."""
    goals = {t["id"]: t["goal"] for t in topics if t["goal"]}
    by_topic: dict[str, list[Concept]] = {}
    for c in concepts:
        if c.topic_id in goals:
            by_topic.setdefault(c.topic_id, []).append(c)
    for topic_id, topic_concepts in by_topic.items():
        scores = await llm_score_relevance(
            goals[topic_id],
            [{"id": c.id, "name": c.name, "explanation": c.explanation} for c in topic_concepts],
        )
        for c in topic_concepts:
            relevance = scores.get(c.id)
            if relevance is None:
                continue
            c.goal_relevance = relevance
            c.scheduled = relevance in ("core", "supporting")
            await conn.execute(
                text(
                    "UPDATE concepts SET goal_relevance = :relevance, "
                    "scheduled = :scheduled WHERE id = :id"
                ),
                {"id": c.id, "relevance": relevance, "scheduled": c.scheduled},
            )


@router.post("/materials/{material_id}/extract")
async def extract_material(material_id: str, conn: UserConn) -> StreamingResponse:
    """Extract Concepts from a Material, streaming NDJSON progress then the result."""
    material = await require_own_material(material_id, conn)
    goal = await fetch_topic_goal(conn, material.topic_id)

    async def stream():
        def event(payload: dict) -> str:
            return json.dumps(payload) + "\n"

        # HTTP 200 is already sent once streaming starts, so failures must be
        # reported as an in-stream event — an unhandled exception would just
        # close the stream and leave the client waiting (issue #30).
        yield event({"type": "progress", "stage": "extracting"})
        try:
            extracted = await llm_extract_concepts(material.content, goal)
            if material.topic_id is None:
                # Routed flow (ADR-0005): attribute each Concept to an existing
                # Topic; what fits nowhere stays unclassified (the inbox).
                yield event({"type": "progress", "stage": "routing"})
                topic_rows = await conn.execute(
                    text("SELECT id, name, goal FROM topics ORDER BY created_at")
                )
                topics = [
                    {"id": str(t.id), "name": t.name, "goal": t.goal} for t in topic_rows
                ]
                routes = await llm_route_concepts(
                    topics,
                    [{"name": e.name, "explanation": e.explanation} for e in extracted],
                )
                yield event({"type": "progress", "stage": "saving", "count": len(extracted)})
                concepts = [
                    await insert_concept(conn, material, e, goal=None, topic_id=route)
                    for e, route in zip(extracted, routes)
                ]
                await link_parents(conn, extracted, concepts)
                await score_routed_concepts(conn, topics, concepts)
                # Orphans are clustered into a few broad proposed Topics —
                # proposals only; the user confirms before anything is created.
                orphans = [c for c in concepts if c.topic_id is None]
                proposals = []
                if orphans:
                    yield event({"type": "progress", "stage": "proposing"})
                    grouped = await llm_propose_topics(
                        topics,
                        [{"name": c.name, "explanation": c.explanation} for c in orphans],
                    )
                    # A proposal whose name matches an existing Topic is a
                    # reuse of that Topic, not a new one (issue #60).
                    id_by_name = {t["name"].lower(): t["id"] for t in topics}
                    proposals = [
                        {
                            "name": g["name"],
                            "topic_id": id_by_name.get(g["name"].lower()),
                            "concept_ids": [orphans[i].id for i in g["indexes"]],
                        }
                        for g in grouped
                    ]
                yield event(
                    {
                        "type": "result",
                        "concepts": [c.model_dump(mode="json") for c in concepts],
                        "proposals": proposals,
                    }
                )
                return
            yield event({"type": "progress", "stage": "saving", "count": len(extracted)})
            concepts = [await insert_concept(conn, material, e, goal) for e in extracted]
            await link_parents(conn, extracted, concepts)
            yield event(
                {"type": "result", "concepts": [c.model_dump(mode="json") for c in concepts]}
            )
        except Exception as exc:
            logger.exception("Extraction failed for material %s", material_id)
            # Catching the error keeps the request "successful", so roll back
            # explicitly or a partial batch of inserts would be committed.
            await conn.rollback()
            yield event({"type": "error", "message": str(exc)})

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.get("/topics/{topic_id}/concepts", response_model=list[Concept])
async def list_concepts(topic_id: str, conn: UserConn) -> list[Concept]:
    """Return the Topic's Concepts with their Questions (404 if not the user's Topic)."""
    found = await conn.execute(
        text("SELECT id FROM topics WHERE id = :id"), {"id": topic_id}
    )
    if found.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")
    rows = await conn.execute(
        text(
            "SELECT id, topic_id, material_id, name, explanation, source_snippet, "
            "goal_relevance, confidence, scheduled, confirmed, created_at, analogy, "
            "technical_explanation, code_snippet, core_claim, ai_supplemented_fields "
            "FROM concepts WHERE topic_id = :topic_id ORDER BY created_at"
        ),
        {"topic_id": topic_id},
    )
    concepts = [
        Concept(
            id=str(r.id),
            topic_id=str(r.topic_id),
            material_id=str(r.material_id),
            name=r.name,
            explanation=r.explanation,
            source_snippet=r.source_snippet,
            goal_relevance=r.goal_relevance,
            confidence=r.confidence,
            scheduled=r.scheduled,
            confirmed=r.confirmed,
            created_at=r.created_at,
            analogy=r.analogy,
            technical_explanation=r.technical_explanation,
            code_snippet=r.code_snippet,
            core_claim=r.core_claim,
            ai_supplemented_fields=list(r.ai_supplemented_fields),
        )
        for r in rows
    ]
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
