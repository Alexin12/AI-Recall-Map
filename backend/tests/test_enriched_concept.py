"""AI-enriched Concept format (ADR-0008): the fixed six-field template on
Concept detail — keyword, analogy, technical_explanation, code_snippet,
core_claim, source_excerpt — plus AI-supplemented flagging.
"""

from app.llm import ExtractedConcept
from app.prompts.extraction_v1 import EXTRACTION_SYSTEM_PROMPT_V1

from tests.test_extraction import make_material, make_topic, stub_llm
from tests.test_reviews import confirmed_scheduled_concept


async def test_concept_detail_exposes_six_field_template(client, make_user, monkeypatch):
    """Concept detail carries all six fields; keyword/source_excerpt anchor the
    existing name/source_snippet (ADR-0008)."""
    _, auth = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)

    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["keyword"] == "Core idea"
    assert detail["analogy"] == "Analogy for Core idea."
    assert detail["technical_explanation"] == "Technical explanation of Core idea."
    assert detail["code_snippet"] == "none"
    assert detail["core_claim"] is None
    assert detail["source_excerpt"] == "Snippet for Core idea."


def test_prompt_forbids_inventing_code():
    """code_snippet is extract-only: the prompt must forbid fabricating or
    completing code and must name the "none" sentinel (ADR-0008)."""
    prompt = EXTRACTION_SYSTEM_PROMPT_V1
    assert "never invent" in prompt.lower()
    assert '"none"' in prompt


async def test_code_snippet_carries_a_real_material_quote_when_present(
    client, make_user, monkeypatch
):
    """When the Material has code, code_snippet is exactly the extracted text."""
    code_concept = ExtractedConcept(
        name="List comprehension",
        explanation="A concise way to build lists in Python.",
        source_snippet="squares = [x * x for x in range(10)]",
        goal_relevance="core",
        confidence=0.9,
        flashcard_prompt="What does a list comprehension build?",
        written_prompt="Explain list comprehensions.",
        analogy="It's like a factory line that builds a list in one pass.",
        technical_explanation=(
            "A list comprehension iterates and maps in a single readable expression."
        ),
        code_snippet="squares = [x * x for x in range(10)]",
    )
    stub_llm(monkeypatch, concepts=[code_concept])
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concept["code_snippet"] == "squares = [x * x for x in range(10)]"


async def test_code_snippet_absent_is_the_literal_none_sentinel(client, make_user, monkeypatch):
    """No code in the Material: code_snippet is "none", not blank or omitted."""
    _, auth = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)

    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["code_snippet"] == "none"


async def test_generated_fields_are_flagged_ai_supplemented(client, make_user, monkeypatch):
    """Fields the model generated (not found in the Material) are named in
    ai_supplemented_fields; code_snippet is never included there (ADR-0008)."""
    generated_concept = ExtractedConcept(
        name="Generated concept",
        explanation="A concept whose Material had no analogy or core claim.",
        source_snippet="Raw Material sentence this Concept comes from.",
        goal_relevance="core",
        confidence=0.9,
        flashcard_prompt="What is this concept?",
        written_prompt="Explain this concept.",
        analogy="An invented analogy since the Material had none.",
        technical_explanation="A generated technical explanation.",
        core_claim="A generated core claim.",
        ai_supplemented_fields=["analogy", "core_claim"],
    )
    stub_llm(monkeypatch, concepts=[generated_concept])
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["ai_supplemented_fields"] == ["analogy", "core_claim"]
    assert "code_snippet" not in detail["ai_supplemented_fields"]


async def test_source_excerpt_anchors_material_span(client, make_user, monkeypatch):
    """source_excerpt always mirrors the extracted source_snippet quote, even
    when other fields on the same Concept were AI-supplemented."""
    _, auth = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)

    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["source_excerpt"] == detail["source_snippet"] == "Snippet for Core idea."


# Reserved FastAPI eval sample (M3 PRD, issue #73 / #69): a small, deterministic
# regression case guarding the whole enriched-extraction pipeline end to end,
# following the extraction_granularity.py precedent of a fixed Material sample
# paired with its canonical expected extraction, run through stub_llm.
FASTAPI_EVAL_MATERIAL = """\
FastAPI is a modern, high-performance Python web framework for building APIs,
built on standard Python type hints. It uses Starlette for the web parts and
Pydantic for data validation and serialization. A path operation is defined
with a decorator:

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}

Type-hinted parameters are automatically validated, parsed, and documented in
the interactive OpenAPI docs, without any extra boilerplate.
"""

FASTAPI_EVAL_CONCEPT = ExtractedConcept(
    name="FastAPI path operations",
    explanation=(
        "FastAPI turns a decorated, type-hinted Python function into a validated,"
        " documented API endpoint."
    ),
    source_snippet=(
        '@app.get("/items/{item_id}")\ndef read_item(item_id: int):\n'
        '    return {"item_id": item_id}'
    ),
    goal_relevance="core",
    confidence=0.9,
    flashcard_prompt="How does FastAPI turn a Python function into an API endpoint?",
    written_prompt="Explain how FastAPI validates and documents a path operation automatically.",
    analogy=(
        "A path operation is like a reception desk clerk: the type hints are the"
        " checklist of what a visitor must bring."
    ),
    technical_explanation=(
        "FastAPI derives request validation, parsing, and OpenAPI docs from a"
        " function's type-hinted parameters and its route decorator."
    ),
    code_snippet=(
        '@app.get("/items/{item_id}")\ndef read_item(item_id: int):\n'
        '    return {"item_id": item_id}'
    ),
    core_claim="Type hints alone give FastAPI validation, parsing, and docs for free.",
)


async def test_fastapi_eval_sample_regression(client, make_user, monkeypatch):
    """The reserved FastAPI eval sample: a fixed Material paragraph run through
    extraction, asserting all six fields come back sensibly and grounded."""
    stub_llm(monkeypatch, concepts=[FASTAPI_EVAL_CONCEPT])
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, name="FastAPI")
    material_id = await make_material(client, auth, topic_id, content=FASTAPI_EVAL_MATERIAL)

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()

    assert detail["keyword"] == "FastAPI path operations"
    assert detail["analogy"]
    assert "type" in detail["technical_explanation"].lower()
    assert detail["code_snippet"].startswith('@app.get("/items/{item_id}")')
    assert detail["core_claim"]
    assert detail["source_excerpt"] == FASTAPI_EVAL_CONCEPT.source_snippet
    assert detail["ai_supplemented_fields"] == []
