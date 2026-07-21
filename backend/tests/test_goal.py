"""Goal per Topic: each Topic carries an optional Goal that drives Phase-2
relevance scoring and scheduling (ADR-0006). The LLM relevance call is the one
stubbed seam; routes, persistence, and RLS run real.
"""

from sqlalchemy import text

from app.db import engine


async def make_topic(client, auth, name="AI engineering") -> str:
    created = await client.post("/topics", json={"name": name}, headers=auth)
    return created.json()["id"]


async def test_patch_topic_sets_goal(client, make_user):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)

    resp = await client.patch(
        f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth
    )
    assert resp.status_code == 200
    assert resp.json()["goal"] == "build RAG apps"

    listed = await client.get("/topics", headers=auth)
    assert listed.json()[0]["goal"] == "build RAG apps"


async def test_new_topic_has_no_goal(client, make_user):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)

    listed = await client.get("/topics", headers=auth)
    topic = next(t for t in listed.json() if t["id"] == topic_id)
    assert topic["goal"] is None


def extraction_stub(names: list[str]):
    """Canned extraction output: one Concept per name."""
    from app.llm import ExtractedConcept

    return [
        ExtractedConcept(
            name=name,
            explanation=f"{name} explained.",
            source_snippet=f"{name} snippet.",
            goal_relevance="supporting",
            confidence=0.9,
            flashcard_prompt=f"What is {name}?",
            written_prompt=f"Explain {name}.",
            analogy=f"Analogy for {name}.",
            technical_explanation=f"Technical explanation of {name}.",
        )
        for name in names
    ]


async def extract_concepts_into(client, auth, topic_id, names, monkeypatch):
    """Create a Material and run extraction with a stubbed LLM."""

    async def fake_extract(material_content, goal):
        return extraction_stub(names)

    monkeypatch.setattr("app.extraction.llm_extract_concepts", fake_extract)
    created = await client.post(
        f"/topics/{topic_id}/materials", json={"content": "raw notes"}, headers=auth
    )
    material_id = created.json()["id"]
    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)
    assert resp.status_code == 200


def stub_relevance(monkeypatch, by_name: dict[str, str]):
    """Stub the Phase-2 relevance seam; score each Concept by its name."""
    calls = []

    async def fake_score(goal, concepts):
        calls.append({"goal": goal, "names": [c["name"] for c in concepts]})
        return {c["id"]: by_name[c["name"]] for c in concepts}

    monkeypatch.setattr("app.topics.llm_score_relevance", fake_score)
    return calls


async def test_setting_goal_scores_and_schedules_concepts(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await extract_concepts_into(
        client, auth, topic_id, ["RAG", "Embeddings", "CSS trivia"], monkeypatch
    )
    calls = stub_relevance(
        monkeypatch,
        {"RAG": "core", "Embeddings": "supporting", "CSS trivia": "irrelevant"},
    )

    resp = await client.patch(
        f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth
    )
    assert resp.status_code == 200
    assert calls and calls[0]["goal"] == "build RAG apps"

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    by_name = {c["name"]: c for c in concepts}
    assert by_name["RAG"]["goal_relevance"] == "core"
    assert by_name["RAG"]["scheduled"] is True
    assert by_name["Embeddings"]["goal_relevance"] == "supporting"
    assert by_name["Embeddings"]["scheduled"] is True
    assert by_name["CSS trivia"]["goal_relevance"] == "irrelevant"
    assert by_name["CSS trivia"]["scheduled"] is False


async def test_no_goal_topic_extracts_unscored_and_schedules_nothing(
    client, make_user, monkeypatch
):
    """A Topic with no Goal stays browsable: relevance NULL, nothing scheduled."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await extract_concepts_into(client, auth, topic_id, ["RAG"], monkeypatch)

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concepts[0]["goal_relevance"] is None
    assert concepts[0]["scheduled"] is False

    await client.post(f"/materials/{concepts[0]['material_id']}/confirm", headers=auth)
    due = (await client.get(f"/topics/{topic_id}/due", headers=auth)).json()
    assert due == []


async def test_clearing_goal_unscores_and_unschedules(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await extract_concepts_into(client, auth, topic_id, ["RAG"], monkeypatch)
    stub_relevance(monkeypatch, {"RAG": "core"})
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)

    resp = await client.patch(f"/topics/{topic_id}", json={"goal": None}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["goal"] is None

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concepts[0]["goal_relevance"] is None
    assert concepts[0]["scheduled"] is False


async def test_relevance_override_wins_and_drives_scheduling(
    client, make_user, monkeypatch
):
    """The user's override on the Topic page beats the AI score (story 14)."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await extract_concepts_into(client, auth, topic_id, ["RAG"], monkeypatch)
    stub_relevance(monkeypatch, {"RAG": "irrelevant"})
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)

    concept_id = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()[0][
        "id"
    ]
    resp = await client.patch(
        f"/concepts/{concept_id}", json={"goal_relevance": "core"}, headers=auth
    )
    assert resp.status_code == 200
    assert resp.json()["goal_relevance"] == "core"
    assert resp.json()["scheduled"] is True

    resp = await client.patch(
        f"/concepts/{concept_id}", json={"goal_relevance": "irrelevant"}, headers=auth
    )
    assert resp.json()["scheduled"] is False


async def test_resaving_same_goal_is_noop_and_keeps_override(
    client, make_user, monkeypatch
):
    """PATCHing the identical Goal must not rescore or clobber a user override
    (issue #50 regression: Save Goal pressed again without changes)."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await extract_concepts_into(client, auth, topic_id, ["RAG"], monkeypatch)
    calls = stub_relevance(monkeypatch, {"RAG": "core"})
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)
    assert len(calls) == 1

    concept_id = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()[0][
        "id"
    ]
    await client.patch(
        f"/concepts/{concept_id}", json={"goal_relevance": "irrelevant"}, headers=auth
    )

    resp = await client.patch(
        f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth
    )
    assert resp.status_code == 200
    assert resp.json()["goal"] == "build RAG apps"
    assert len(calls) == 1  # scoring seam not called a second time

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concepts[0]["goal_relevance"] == "irrelevant"
    assert concepts[0]["scheduled"] is False


async def test_clear_then_undo_restores_goal_and_rescores(client, make_user, monkeypatch):
    """Issue #78: the frontend's Undo-after-clear is just a second PATCH with
    the previous Goal value — confirm the existing endpoint round-trips that
    correctly (clear unschedules everything, Undo restores and rescores)."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await extract_concepts_into(client, auth, topic_id, ["RAG"], monkeypatch)
    calls = stub_relevance(monkeypatch, {"RAG": "core"})
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)
    assert len(calls) == 1

    cleared = await client.patch(f"/topics/{topic_id}", json={"goal": None}, headers=auth)
    assert cleared.status_code == 200
    assert cleared.json()["goal"] is None
    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concepts[0]["goal_relevance"] is None
    assert concepts[0]["scheduled"] is False

    undone = await client.patch(
        f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth
    )
    assert undone.status_code == 200
    assert undone.json()["goal"] == "build RAG apps"
    assert len(calls) == 2  # rescored again on Undo

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concepts[0]["goal_relevance"] == "core"
    assert concepts[0]["scheduled"] is True


async def test_user_level_goal_is_gone(client, make_user):
    """The global /goal endpoints and the goals table no longer exist (ADR-0006)."""
    _, auth = await make_user()

    assert (await client.get("/goal", headers=auth)).status_code == 404
    assert (
        await client.put("/goal", json={"content": "x"}, headers=auth)
    ).status_code in (404, 405)

    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'goals'"
                )
            )
        ).all()
    assert rows == []
