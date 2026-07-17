"""The LLM seam: one function that turns a Material's text into Concepts.

This is the single boundary tests stub; everything downstream is real code.
"""

from typing import Literal

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.prompts.extraction_v1 import EXTRACTION_SYSTEM_PROMPT_V1
from app.prompts.grading_v1 import GRADING_SYSTEM_PROMPT_V1
from app.prompts.relevance_v1 import RELEVANCE_SYSTEM_PROMPT_V1
from app.prompts.router_v1 import ROUTER_SYSTEM_PROMPT_V1


class ExtractedConcept(BaseModel):
    """One Concept the LLM extracted from a Material, plus its two Questions."""

    name: str
    explanation: str
    source_snippet: str
    goal_relevance: Literal["irrelevant", "supporting", "core"]
    confidence: float
    flashcard_prompt: str
    written_prompt: str


class ExtractionResult(BaseModel):
    """Structured-output envelope for the extraction call."""

    concepts: list[ExtractedConcept]


class GradeResult(BaseModel):
    """The four-tier Review Verdict plus structured feedback for one answer."""

    verdict: Literal["fail", "partial", "pass", "strong"]
    correct_points: list[str]
    missing_points: list[str]
    misconceptions: list[str]


async def grade_answer(
    explanation: str, source_snippet: str, question_prompt: str, answer: str
) -> GradeResult:
    """Grade one answer from the Concept's explanation + snippet only (ADR-0001)."""
    client = AsyncAnthropic()
    response = await client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=16000,
        system=GRADING_SYSTEM_PROMPT_V1,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Concept explanation:\n{explanation}\n\n"
                    f"Source snippet:\n{source_snippet}\n\n"
                    f"Question:\n{question_prompt}\n\n"
                    f"Learner's answer:\n{answer}"
                ),
            }
        ],
        output_format=GradeResult,
    )
    return response.parsed_output


class ScoredConcept(BaseModel):
    """One Concept's Phase-2 relevance verdict, keyed back by its id."""

    id: str
    goal_relevance: Literal["irrelevant", "supporting", "core"]


class RelevanceResult(BaseModel):
    """Structured-output envelope for the Phase-2 relevance call."""

    scores: list[ScoredConcept]


async def score_relevance(goal: str, concepts: list[dict]) -> dict[str, str]:
    """Score each Concept's relevance to the Topic's Goal (ADR-0006 Phase 2).

    `concepts` items carry id, name, explanation; returns {concept_id: relevance}.
    """
    client = AsyncAnthropic()
    listing = "\n".join(
        f"- id: {c['id']}\n  name: {c['name']}\n  explanation: {c['explanation']}"
        for c in concepts
    )
    response = await client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=16000,
        system=RELEVANCE_SYSTEM_PROMPT_V1,
        messages=[
            {
                "role": "user",
                "content": f"The Topic's Goal: {goal}\n\nConcepts:\n{listing}",
            }
        ],
        output_format=RelevanceResult,
    )
    return {s.id: s.goal_relevance for s in response.parsed_output.scores}


class RoutedConcept(BaseModel):
    """The router's decision for one Concept, keyed back by its list index."""

    index: int
    topic_id: str | None


class RoutingResult(BaseModel):
    """Structured-output envelope for the router call."""

    decisions: list[RoutedConcept]


async def route_concepts(topics: list[dict], concepts: list[dict]) -> list[str | None]:
    """Attribute each Concept to an existing Topic or None = inbox (ADR-0005).

    `topics` items carry id, name, goal; `concepts` items carry name,
    explanation. Returns one topic_id-or-None per Concept, aligned by position.
    The router never mints Topics: unknown topic ids collapse to None.
    """
    client = AsyncAnthropic()
    topic_listing = "\n".join(
        f"- id: {t['id']}\n  name: {t['name']}\n  goal: {t.get('goal') or 'none'}"
        for t in topics
    )
    concept_listing = "\n".join(
        f"- index: {i}\n  name: {c['name']}\n  explanation: {c['explanation']}"
        for i, c in enumerate(concepts)
    )
    response = await client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=16000,
        system=ROUTER_SYSTEM_PROMPT_V1,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Existing Topics:\n{topic_listing or '(none)'}\n\n"
                    f"Concepts:\n{concept_listing}"
                ),
            }
        ],
        output_format=RoutingResult,
    )
    known = {t["id"] for t in topics}
    by_index = {d.index: d.topic_id for d in response.parsed_output.decisions}
    return [
        by_index.get(i) if by_index.get(i) in known else None
        for i in range(len(concepts))
    ]


async def extract_concepts(material_content: str, goal: str | None) -> list[ExtractedConcept]:
    """Call the LLM with Structured Outputs; return the extracted Concepts."""
    client = AsyncAnthropic()
    goal_line = f"The user's learning Goal: {goal}" if goal else "The user has not set a Goal."
    response = await client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=16000,
        system=EXTRACTION_SYSTEM_PROMPT_V1,
        messages=[
            {
                "role": "user",
                "content": f"{goal_line}\n\nMaterial:\n{material_content}",
            }
        ],
        output_format=ExtractionResult,
    )
    return response.parsed_output.concepts
