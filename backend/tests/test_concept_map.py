"""Concept Map as a hierarchy tree (ADR-0007): parent pointers, not edge rows.

Extraction emits a primary parent per Concept (plus an optional display-only
second parent); the map endpoint returns the Topic's Concepts as a tree.
"""

from sqlalchemy import text

from app.db import engine
from app.llm import ExtractedConcept

from tests.test_extraction import make_material, make_topic, stub_llm
from tests.test_override import answer_flashcard
from tests.test_reviews import confirmed_scheduled_concept, stub_grading


def tree_concept(name: str, parent: str | None = None, second: str | None = None):
    return ExtractedConcept(
        name=name,
        explanation=f"Explanation of {name}.",
        source_snippet=f"Snippet for {name}.",
        goal_relevance="supporting",
        confidence=0.9,
        flashcard_prompt=f"Flashcard for {name}?",
        written_prompt=f"Explain {name}.",
        parent_name=parent,
        second_parent_name=second,
    )


async def extract_tree(client, auth, monkeypatch, concepts) -> str:
    stub_llm(monkeypatch, concepts=concepts)
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    return topic_id


async def test_map_returns_tree_from_parent_pointers(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await extract_tree(
        client,
        auth,
        monkeypatch,
        [
            tree_concept("RAG"),
            tree_concept("Retrieval", parent="RAG"),
            tree_concept("Vector databases", parent="Retrieval"),
            tree_concept("Generation", parent="RAG"),
        ],
    )

    resp = await client.get(f"/topics/{topic_id}/map", headers=auth)
    assert resp.status_code == 200
    [root] = resp.json()["tree"]
    assert root["name"] == "RAG"
    children = {c["name"]: c for c in root["children"]}
    assert set(children) == {"Retrieval", "Generation"}
    [grandchild] = children["Retrieval"]["children"]
    assert grandchild["name"] == "Vector databases"
    assert grandchild["children"] == []


async def test_second_parent_shows_as_slash_label(client, make_user, monkeypatch):
    """A two-parent Concept hangs off its primary parent and carries a
    display-only slash label (ADR-0007); the Topic has no Goal yet stays browsable."""
    _, auth = await make_user()
    topic_id = await extract_tree(
        client,
        auth,
        monkeypatch,
        [
            tree_concept("Retrieval"),
            tree_concept("Semantic search", parent="Retrieval", second="Embeddings"),
        ],
    )

    [root] = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["tree"]
    assert root["display_label"] == "Retrieval"
    [child] = root["children"]
    assert child["display_label"] == "Semantic search / Embeddings"
    # Structure and review are independent: no Goal, still browsable, unscored.
    assert child["goal_relevance"] is None


async def test_map_nodes_carry_mastery_state(client, make_user, monkeypatch):
    """Each map node exposes its Mastery State; zero Reviews is never-reviewed,
    and a Review moves the node off never-reviewed via the real derivation."""
    stub_grading(monkeypatch)  # verdict: pass
    _, auth = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)

    [node] = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["tree"]
    assert node["mastery"] == "never-reviewed"

    await answer_flashcard(client, auth, concept)  # one pass -> learning
    [node] = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["tree"]
    assert node["mastery"] == "learning"


async def test_deleting_a_concept_reparents_children_to_roots(
    client, make_user, monkeypatch
):
    """Deleting a Concept removes it (Questions cascade); its children survive
    as new roots and the tree re-renders without it (story 19)."""
    _, auth = await make_user()
    topic_id = await extract_tree(
        client,
        auth,
        monkeypatch,
        [
            tree_concept("RAG"),
            tree_concept("Retrieval", parent="RAG"),
            tree_concept("Vector databases", parent="Retrieval"),
        ],
    )
    [root] = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["tree"]
    [retrieval] = root["children"]

    deleted = await client.delete(f"/concepts/{retrieval['id']}", headers=auth)
    assert deleted.status_code == 204

    tree = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["tree"]
    assert {n["name"] for n in tree} == {"RAG", "Vector databases"}
    assert all(n["children"] == [] for n in tree)
    assert (await client.get(f"/concepts/{retrieval['id']}", headers=auth)).status_code == 404

    # The Questions cascade with their Concept (issue #53 follow-up): none left.
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT 1 FROM questions WHERE concept_id = :id"),
                {"id": retrieval["id"]},
            )
        ).all()
    assert rows == []
