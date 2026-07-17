"""Proposed Topics + Confirmation actions (ADR-0005): leftovers are clustered
into a few high-level proposed Topics that the user confirms — the model never
auto-commits a Topic. The extraction / router / proposal LLM calls are stubbed.
"""

from tests.test_confirmation import concept_of
from tests.test_extraction import make_topic, stub_llm
from tests.test_routing import paste_and_extract, stub_router


def stub_proposals(monkeypatch, groups: dict[str, list[str]]):
    """Stub the proposal seam: cluster orphan Concept names into proposed Topics."""
    calls = []

    async def fake_propose(concepts):
        calls.append([c["name"] for c in concepts])
        name_to_group = {n: g for g, names in groups.items() for n in names}
        out: dict[str, list[int]] = {}
        for i, c in enumerate(concepts):
            out.setdefault(name_to_group[c["name"]], []).append(i)
        return [{"name": g, "indexes": idxs} for g, idxs in out.items()]

    monkeypatch.setattr("app.extraction.llm_propose_topics", fake_propose)
    return calls


async def test_first_paste_proposes_topics_without_committing_them(
    client, make_user, monkeypatch
):
    _, auth = await make_user()  # no Topics at all
    stub_llm(
        monkeypatch,
        concepts=[
            concept_of("core", "Chunking"),
            concept_of("core", "Embeddings"),
            concept_of("core", "Flexbox"),
        ],
    )
    stub_router(monkeypatch, {"Chunking": None, "Embeddings": None, "Flexbox": None})
    stub_proposals(monkeypatch, {"RAG": ["Chunking", "Embeddings"], "CSS": ["Flexbox"]})

    _, events = await paste_and_extract(client, auth)

    result = events[-1]
    assert result["type"] == "result"
    proposals = result["proposals"]
    by_name = {p["name"]: p for p in proposals}
    assert set(by_name) == {"RAG", "CSS"}
    concept_names = {c["id"]: c["name"] for c in result["concepts"]}
    assert [concept_names[cid] for cid in by_name["RAG"]["concept_ids"]] == [
        "Chunking",
        "Embeddings",
    ]
    # Nothing was committed: no Topics exist, all Concepts sit in the inbox.
    assert (await client.get("/topics", headers=auth)).json() == []
    inbox = (await client.get("/concepts/unclassified", headers=auth)).json()
    assert len(inbox) == 3


async def test_confirming_a_proposal_creates_topic_with_goal_and_files_concepts(
    client, make_user, monkeypatch
):
    """Confirmation: create the proposed Topic (with an optional Goal) and move
    its Concepts in; a Goal set on the confirmation step scores them (story 10)."""
    _, auth = await make_user()
    stub_llm(monkeypatch, concepts=[concept_of("core", "Chunking")])
    stub_router(monkeypatch, {"Chunking": None})
    stub_proposals(monkeypatch, {"RAG": ["Chunking"]})
    _, events = await paste_and_extract(client, auth)
    [proposal] = events[-1]["proposals"]

    async def fake_score(goal, concepts):
        assert goal == "build RAG apps"
        return {c["id"]: "core" for c in concepts}

    monkeypatch.setattr("app.confirmation.llm_score_relevance", fake_score)

    created = await client.post(
        "/topics", json={"name": "RAG", "goal": "build RAG apps"}, headers=auth
    )
    assert created.status_code == 201
    assert created.json()["goal"] == "build RAG apps"
    topic_id = created.json()["id"]
    for concept_id in proposal["concept_ids"]:
        moved = await client.patch(
            f"/concepts/{concept_id}", json={"topic_id": topic_id}, headers=auth
        )
        assert moved.status_code == 200

    [chunking] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert chunking["goal_relevance"] == "core"
    assert chunking["scheduled"] is True
    assert (await client.get("/concepts/unclassified", headers=auth)).json() == []


async def test_dropping_a_concept_to_the_inbox(client, make_user, monkeypatch):
    """An explicit null topic_id unfiles the Concept: back to the inbox, unscored."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, "RAG")
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)
    stub_llm(monkeypatch, concepts=[concept_of("core", "Chunking")])
    stub_router(monkeypatch, {"Chunking": topic_id})

    async def fake_score(goal, concepts):
        return {c["id"]: "core" for c in concepts}

    monkeypatch.setattr("app.extraction.llm_score_relevance", fake_score)
    await paste_and_extract(client, auth)
    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()

    dropped = await client.patch(
        f"/concepts/{concept['id']}", json={"topic_id": None}, headers=auth
    )
    assert dropped.status_code == 200
    assert dropped.json()["topic_id"] is None
    assert dropped.json()["goal_relevance"] is None
    assert dropped.json()["scheduled"] is False
    [inboxed] = (await client.get("/concepts/unclassified", headers=auth)).json()
    assert inboxed["id"] == concept["id"]
