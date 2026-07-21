"""The LLM seam: one function that turns a Material's text into Concepts.

This is the single boundary tests stub; everything downstream is real code.
"""

import os
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.prompts.extraction_v1 import EXTRACTION_SYSTEM_PROMPT_V1
from app.prompts.grading_v1 import GRADING_SYSTEM_PROMPT_V1
from app.prompts.relevance_v1 import RELEVANCE_SYSTEM_PROMPT_V1
from app.prompts.proposal_v1 import PROPOSAL_SYSTEM_PROMPT_V1
from app.prompts.router_v1 import ROUTER_SYSTEM_PROMPT_V1

OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"


def _client() -> AsyncOpenAI:
    """OpenRouter speaks the OpenAI Chat Completions API, not Anthropic's."""
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )


class ExtractedConcept(BaseModel):
    """One Concept the LLM extracted from a Material, plus its two Questions."""

    name: str
    explanation: str
    source_snippet: str
    goal_relevance: Literal["irrelevant", "supporting", "core"]
    confidence: float
    flashcard_prompt: str
    written_prompt: str
    # Hierarchy (ADR-0007): the name of this Concept's primary parent within
    # the same extraction (None = root), plus a display-only second parent.
    parent_name: str | None = None
    second_parent_name: str | None = None
    # AI-enriched format (ADR-0008): a layered breakdown of the explanation.
    # analogy and technical_explanation are always required; code_snippet is
    # extract-only ("none" when the Material has no code, never invented);
    # core_claim is optional. ai_supplemented_fields names any of
    # {analogy, technical_explanation, core_claim} the model generated
    # because the Material didn't already contain it.
    analogy: str
    technical_explanation: str
    code_snippet: str = "none"
    core_claim: str | None = None
    ai_supplemented_fields: list[str] = []


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
    response = await _client().beta.chat.completions.parse(
        model=OPENROUTER_MODEL,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": GRADING_SYSTEM_PROMPT_V1},
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
        response_format=GradeResult,
    )
    return response.choices[0].message.parsed


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
    listing = "\n".join(
        f"- id: {c['id']}\n  name: {c['name']}\n  explanation: {c['explanation']}"
        for c in concepts
    )
    response = await _client().beta.chat.completions.parse(
        model=OPENROUTER_MODEL,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": RELEVANCE_SYSTEM_PROMPT_V1},
            {
                "role": "user",
                "content": f"The Topic's Goal: {goal}\n\nConcepts:\n{listing}",
            }
        ],
        response_format=RelevanceResult,
    )
    return {s.id: s.goal_relevance for s in response.choices[0].message.parsed.scores}


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
    topic_listing = "\n".join(
        f"- id: {t['id']}\n  name: {t['name']}\n  goal: {t.get('goal') or 'none'}"
        for t in topics
    )
    concept_listing = "\n".join(
        f"- index: {i}\n  name: {c['name']}\n  explanation: {c['explanation']}"
        for i, c in enumerate(concepts)
    )
    response = await _client().beta.chat.completions.parse(
        model=OPENROUTER_MODEL,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT_V1},
            {
                "role": "user",
                "content": (
                    f"Existing Topics:\n{topic_listing or '(none)'}\n\n"
                    f"Concepts:\n{concept_listing}"
                ),
            }
        ],
        response_format=RoutingResult,
    )
    known = {t["id"] for t in topics}
    by_index = {d.index: d.topic_id for d in response.choices[0].message.parsed.decisions}
    return [
        by_index.get(i) if by_index.get(i) in known else None
        for i in range(len(concepts))
    ]


class ProposedTopic(BaseModel):
    """One proposed broad Topic and the leftover Concept indexes it covers."""

    name: str
    indexes: list[int]


class ProposalResult(BaseModel):
    """Structured-output envelope for the Topic-proposal call."""

    proposals: list[ProposedTopic]


async def propose_topics(topics: list[dict], concepts: list[dict]) -> list[dict]:
    """Cluster orphan Concepts into a few broad proposed Topics (ADR-0005).

    `topics` items carry the user's existing Topic names so a broad one can be
    reused by exact name; `concepts` items carry name, explanation. Returns
    [{name, indexes}] — proposals only; nothing is committed until the user
    confirms.
    """
    topic_listing = "\n".join(f"- {t['name']}" for t in topics)
    listing = "\n".join(
        f"- index: {i}\n  name: {c['name']}\n  explanation: {c['explanation']}"
        for i, c in enumerate(concepts)
    )
    response = await _client().beta.chat.completions.parse(
        model=OPENROUTER_MODEL,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": PROPOSAL_SYSTEM_PROMPT_V1},
            {
                "role": "user",
                "content": (
                    f"Existing Topics:\n{topic_listing or '(none)'}\n\n"
                    f"Leftover Concepts:\n{listing}"
                ),
            }
        ],
        response_format=ProposalResult,
    )
    return [
        {"name": p.name, "indexes": p.indexes}
        for p in response.choices[0].message.parsed.proposals
    ]


async def extract_concepts(material_content: str, goal: str | None) -> list[ExtractedConcept]:
    """Call the LLM with Structured Outputs; return the extracted Concepts."""
    goal_line = f"The user's learning Goal: {goal}" if goal else "The user has not set a Goal."
    response = await _client().beta.chat.completions.parse(
        model=OPENROUTER_MODEL,
        max_tokens=16000,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT_V1},
            {
                "role": "user",
                "content": f"{goal_line}\n\nMaterial:\n{material_content}",
            }
        ],
        response_format=ExtractionResult,
    )
    return response.choices[0].message.parsed.concepts
