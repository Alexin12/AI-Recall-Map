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
    topic_id: str
    material_id: str
    name: str
    explanation: str
    source_snippet: str
    goal_relevance: str
    confidence: float
    scheduled: bool
    confirmed: bool
    created_at: datetime
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


async def fetch_goal(conn) -> str | None:
    """Return the user's Goal content, or None if not set."""
    result = await conn.execute(text("SELECT content FROM goals"))
    row = result.first()
    return row.content if row else None


async def insert_concept(conn, material, extracted) -> Concept:
    """Persist one extracted Concept plus its flashcard and written Questions."""
    row = (
        await conn.execute(
            text(
                "INSERT INTO concepts (topic_id, material_id, name, explanation, "
                "source_snippet, goal_relevance, confidence, scheduled) "
                "VALUES (:topic_id, :material_id, :name, :explanation, "
                ":source_snippet, :goal_relevance, :confidence, :scheduled) "
                "RETURNING id, topic_id, material_id, name, explanation, "
                "source_snippet, goal_relevance, confidence, scheduled, confirmed, created_at"
            ),
            {
                "topic_id": str(material.topic_id),
                "material_id": str(material.id),
                "name": extracted.name,
                "explanation": extracted.explanation,
                "source_snippet": extracted.source_snippet,
                "goal_relevance": extracted.goal_relevance,
                "confidence": extracted.confidence,
                # Scheduling default: core Concepts enter review, others stay browsable.
                "scheduled": extracted.goal_relevance == "core",
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
        questions=questions,
    )


@router.post("/materials/{material_id}/extract")
async def extract_material(material_id: str, conn: UserConn) -> StreamingResponse:
    """Extract Concepts from a Material, streaming NDJSON progress then the result."""
    material = await require_own_material(material_id, conn)
    goal = await fetch_goal(conn)

    async def stream():
        def event(payload: dict) -> str:
            return json.dumps(payload) + "\n"

        # HTTP 200 is already sent once streaming starts, so failures must be
        # reported as an in-stream event — an unhandled exception would just
        # close the stream and leave the client waiting (issue #30).
        yield event({"type": "progress", "stage": "extracting"})
        try:
            extracted = await llm_extract_concepts(material.content, goal)
            # No Goal means relevance can't be judged, so cap "core" at
            # "supporting" — otherwise every Material's own content reads as
            # core and floods review (issue #26).
            if goal is None:
                extracted = [
                    e.model_copy(update={"goal_relevance": "supporting"})
                    if e.goal_relevance == "core"
                    else e
                    for e in extracted
                ]
            yield event({"type": "progress", "stage": "saving", "count": len(extracted)})
            concepts = [await insert_concept(conn, material, e) for e in extracted]
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
            "goal_relevance, confidence, scheduled, confirmed, created_at FROM concepts "
            "WHERE topic_id = :topic_id ORDER BY created_at"
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
