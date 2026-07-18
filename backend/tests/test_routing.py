"""Global Home paste + Concept-level routing + inbox (ADR-0005).

A Material pasted with no Topic is a raw unsorted input; extraction routes each
Concept into an existing Topic or leaves it unclassified (NULL topic_id = the
inbox). The extraction and router LLM calls are the stubbed seams.
"""

from tests.test_confirmation import concept_of
from tests.test_extraction import events_of, make_topic, stub_llm


def stub_router(monkeypatch, route_by_name: dict[str, str | None]):
    """Stub the routing seam: map each extracted Concept name to a topic_id or None."""
    calls = []

    async def fake_route(topics, concepts):
        calls.append({"topics": topics, "names": [c["name"] for c in concepts]})
        return [route_by_name[c["name"]] for c in concepts]

    monkeypatch.setattr("app.extraction.llm_route_concepts", fake_route)
    return calls


async def paste_and_extract(client, auth, content="mixed notes") -> tuple[str, list[dict]]:
    """Global paste + extract; return (material_id, streamed events)."""
    material = (
        await client.post("/materials", json={"content": content}, headers=auth)
    ).json()
    resp = await client.post(f"/materials/{material['id']}/extract", headers=auth)
    assert resp.status_code == 200
    return material["id"], events_of(resp.text)


async def test_paste_material_without_topic(client, make_user):
    _, auth = await make_user()

    resp = await client.post("/materials", json={"content": "raw notes"}, headers=auth)
    assert resp.status_code == 201
    body = resp.json()
    assert body["topic_id"] is None
    assert body["content"] == "raw notes"


async def test_routing_splits_one_material_across_topics(client, make_user, monkeypatch):
    _, auth = await make_user()
    rag_topic = await make_topic(client, auth, "RAG")
    css_topic = await make_topic(client, auth, "CSS")
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "Chunking"), concept_of("core", "Flexbox")],
    )
    calls = stub_router(monkeypatch, {"Chunking": rag_topic, "Flexbox": css_topic})

    _, events = await paste_and_extract(client, auth)
    assert events[-1]["type"] == "result"

    rag = (await client.get(f"/topics/{rag_topic}/concepts", headers=auth)).json()
    css = (await client.get(f"/topics/{css_topic}/concepts", headers=auth)).json()
    assert [c["name"] for c in rag] == ["Chunking"]
    assert [c["name"] for c in css] == ["Flexbox"]
    # The router saw the user's Topics and every extracted Concept.
    assert {t["name"] for t in calls[0]["topics"]} == {"RAG", "CSS"}
    assert calls[0]["names"] == ["Chunking", "Flexbox"]


async def test_orphan_concept_lands_in_inbox_not_a_minted_topic(
    client, make_user, monkeypatch
):
    """A Concept matching no Topic stays unclassified; the router mints nothing."""
    _, auth = await make_user()
    rag_topic = await make_topic(client, auth, "RAG")
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "Chunking"), concept_of("core", "Stoicism")],
    )
    stub_router(monkeypatch, {"Chunking": rag_topic, "Stoicism": None})

    await paste_and_extract(client, auth)

    inbox = await client.get("/concepts/unclassified", headers=auth)
    assert inbox.status_code == 200
    [orphan] = inbox.json()
    assert orphan["name"] == "Stoicism"
    assert orphan["topic_id"] is None
    # No new Topic was minted for the orphan.
    topics = (await client.get("/topics", headers=auth)).json()
    assert [t["name"] for t in topics] == ["RAG"]


async def test_routed_concepts_scored_only_in_goal_topics(client, make_user, monkeypatch):
    """Phase 2 runs for routed Concepts whose Topic has a Goal; others stay unscored."""
    _, auth = await make_user()
    rag_topic = await make_topic(client, auth, "RAG")
    await client.patch(f"/topics/{rag_topic}", json={"goal": "build RAG apps"}, headers=auth)
    css_topic = await make_topic(client, auth, "CSS")  # no Goal
    stub_llm(
        monkeypatch,
        concepts=[concept_of("supporting", "Chunking"), concept_of("supporting", "Flexbox")],
    )
    stub_router(monkeypatch, {"Chunking": rag_topic, "Flexbox": css_topic})

    async def fake_score(goal, concepts):
        assert goal == "build RAG apps"
        return {c["id"]: "core" for c in concepts}

    monkeypatch.setattr("app.extraction.llm_score_relevance", fake_score)

    await paste_and_extract(client, auth)

    [chunking] = (await client.get(f"/topics/{rag_topic}/concepts", headers=auth)).json()
    assert chunking["goal_relevance"] == "core"
    assert chunking["scheduled"] is True
    [flexbox] = (await client.get(f"/topics/{css_topic}/concepts", headers=auth)).json()
    assert flexbox["goal_relevance"] is None
    assert flexbox["scheduled"] is False


async def test_move_concept_from_inbox_and_between_topics(client, make_user, monkeypatch):
    """The user can file an unclassified Concept into a Topic and move it again;
    landing in a Goal-carrying Topic scores it, a Goal-less one unscores it."""
    _, auth = await make_user()
    rag_topic = await make_topic(client, auth, "RAG")
    await client.patch(f"/topics/{rag_topic}", json={"goal": "build RAG apps"}, headers=auth)
    css_topic = await make_topic(client, auth, "CSS")  # no Goal
    stub_llm(monkeypatch, concepts=[concept_of("core", "Stoicism")])
    stub_router(monkeypatch, {"Stoicism": None})
    await paste_and_extract(client, auth)
    [orphan] = (await client.get("/concepts/unclassified", headers=auth)).json()

    async def fake_score(goal, concepts):
        return {c["id"]: "supporting" for c in concepts}

    monkeypatch.setattr("app.confirmation.llm_score_relevance", fake_score)

    moved = await client.patch(
        f"/concepts/{orphan['id']}", json={"topic_id": rag_topic}, headers=auth
    )
    assert moved.status_code == 200
    assert moved.json()["topic_id"] == rag_topic
    assert moved.json()["goal_relevance"] == "supporting"
    assert moved.json()["scheduled"] is True
    assert (await client.get("/concepts/unclassified", headers=auth)).json() == []

    # Moving on to a Goal-less Topic unscores and unschedules it again.
    moved = await client.patch(
        f"/concepts/{orphan['id']}", json={"topic_id": css_topic}, headers=auth
    )
    assert moved.json()["topic_id"] == css_topic
    assert moved.json()["goal_relevance"] is None
    assert moved.json()["scheduled"] is False
