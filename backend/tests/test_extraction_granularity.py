"""Extraction granularity (issue #59): few key Concepts, details in explanations.

The extraction prompt is the product here: these tests pin its granularity
rules, plus a regression case for an example-heavy instructional article.
"""

import json

from app.llm import ExtractedConcept
from app.prompts.extraction_v1 import EXTRACTION_SYSTEM_PROMPT_V1

# Regression sample (issue #59): an instructional article whose two sections
# name many tools. The useful structure is two key Concepts, not one per tool.
MANDARIN_SAMPLE = """\
How I Learned Mandarin in One Year

Essential Study Tools
Install Pleco for dictionary lookups. Drill vocabulary with Anki flashcards.
Read graded stories in DuChinese. Check stroke order in Hanping.

Language Practice & Immersion
Post journal entries on LangCorrect for native corrections. Watch Mandarin
YouTube channels daily. Book weekly iTalki tutoring sessions.
"""

TOOL_NAMES = ["Pleco", "Anki", "DuChinese", "LangCorrect"]

# The canonical expected extraction for MANDARIN_SAMPLE under the granularity
# rules: two key Concepts whose explanations carry the tools as examples.
MANDARIN_KEY_CONCEPTS = [
    ExtractedConcept(
        name="Essential Study Tools",
        explanation=(
            "A small toolkit covers daily study: Pleco for dictionary lookups, "
            "Anki for spaced-repetition flashcards, DuChinese for graded "
            "reading, and Hanping for stroke order."
        ),
        source_snippet="Essential Study Tools",
        goal_relevance="supporting",
        confidence=0.9,
        flashcard_prompt="Which app handles spaced-repetition vocabulary drills?",
        written_prompt="Describe the core Mandarin study toolkit and each tool's job.",
    ),
    ExtractedConcept(
        name="Language Practice & Immersion",
        explanation=(
            "Active practice and immersion drive fluency: journaling on "
            "LangCorrect for native corrections, daily Mandarin YouTube "
            "watching, and weekly iTalki tutoring."
        ),
        source_snippet="Language Practice & Immersion",
        goal_relevance="supporting",
        confidence=0.9,
        flashcard_prompt="Name one way to get native corrections on your writing.",
        written_prompt="Explain how practice and immersion complement tool-based study.",
    ),
]


def stub_llm(monkeypatch, concepts):
    async def fake_extract(material_content, goal):
        return concepts

    monkeypatch.setattr("app.extraction.llm_extract_concepts", fake_extract)


async def extract_into_topic(client, auth, concepts, monkeypatch) -> str:
    """Create a Topic + the Mandarin Material, extract with a stubbed LLM."""
    stub_llm(monkeypatch, concepts)
    topic_id = (await client.post("/topics", json={"name": "Mandarin"}, headers=auth)).json()["id"]
    material_id = (
        await client.post(
            f"/topics/{topic_id}/materials", json={"content": MANDARIN_SAMPLE}, headers=auth
        )
    ).json()["id"]
    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)
    result = [json.loads(line) for line in resp.text.strip().splitlines()][-1]
    assert result["type"] == "result"
    return topic_id


def test_prompt_asks_for_smallest_set_of_key_concepts():
    """Concept count must track major ideas, not the number of details."""
    prompt = EXTRACTION_SYSTEM_PROMPT_V1.lower()
    assert "smallest useful set" in prompt
    assert "headings" in prompt
    assert "major ideas" in prompt
    assert "not to its number of details" in prompt


def test_prompt_keeps_examples_and_products_inside_explanations():
    """Bullets, named products, links, examples: explanation content, not Concepts."""
    prompt = EXTRACTION_SYSTEM_PROMPT_V1.lower()
    for detail in ["bullet", "named product", "link", "example", "citation"]:
        assert detail in prompt
    assert "inside the explanation" in prompt
    assert "standalone concept" in prompt


async def test_mandarin_sample_yields_two_key_concepts(client, make_user, monkeypatch):
    """The example-heavy Mandarin article persists two key Concepts, with the
    tools kept as examples inside their explanations, never as Concept names."""
    _, auth = await make_user()
    topic_id = await extract_into_topic(client, auth, MANDARIN_KEY_CONCEPTS, monkeypatch)

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert sorted(c["name"] for c in concepts) == [
        "Essential Study Tools",
        "Language Practice & Immersion",
    ]
    explanations = " ".join(c["explanation"] for c in concepts)
    for tool in TOOL_NAMES:
        assert tool in explanations
        assert all(tool not in c["name"] for c in concepts)


async def test_supporting_detail_nests_below_key_concepts(client, make_user, monkeypatch):
    """A genuinely teachable detail hangs under its key Concept in the Concept
    Map; the top-level list stays at the two key Concepts (ADR-0007)."""
    detail = ExtractedConcept(
        name="Graded Reading Routine",
        explanation="Daily graded reading in DuChinese builds vocabulary in context.",
        source_snippet="Read graded stories in DuChinese.",
        goal_relevance="supporting",
        confidence=0.8,
        flashcard_prompt="What does daily graded reading build?",
        written_prompt="Explain how a graded reading routine fits the toolkit.",
        parent_name="Essential Study Tools",
    )
    _, auth = await make_user()
    topic_id = await extract_into_topic(
        client, auth, MANDARIN_KEY_CONCEPTS + [detail], monkeypatch
    )

    tree = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["tree"]
    assert sorted(node["name"] for node in tree) == [
        "Essential Study Tools",
        "Language Practice & Immersion",
    ]
    [tools_root] = [n for n in tree if n["name"] == "Essential Study Tools"]
    assert [child["name"] for child in tools_root["children"]] == ["Graded Reading Routine"]
