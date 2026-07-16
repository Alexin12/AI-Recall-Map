"""The LLM seam: one function that turns a Material's text into Concepts.

This is the single boundary tests stub; everything downstream is real code.
"""

from typing import Literal

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.prompts.extraction_v1 import EXTRACTION_SYSTEM_PROMPT_V1
from app.prompts.grading_v1 import GRADING_SYSTEM_PROMPT_V1


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
