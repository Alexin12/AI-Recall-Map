"""The LLM seam: one function that turns a Material's text into Concepts.

This is the single boundary tests stub; everything downstream is real code.
"""

from typing import Literal

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.prompts.extraction_v1 import EXTRACTION_SYSTEM_PROMPT_V1


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


async def extract_concepts(material_content: str, goal: str | None) -> list[ExtractedConcept]:
    """Call the LLM with Structured Outputs; return the extracted Concepts."""
    client = AsyncAnthropic()
    goal_line = f"The user's learning Goal: {goal}" if goal else "The user has not set a Goal."
    response = await client.messages.parse(
        model="claude-opus-4-8",
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
