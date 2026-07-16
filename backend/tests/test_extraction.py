"""Extraction API: a Material becomes persisted Concepts and Questions.

The LLM call is the one stubbed seam; route, persistence, and RLS run real.
"""

import json

from app.llm import ExtractedConcept

STUB_CONCEPTS = [
    ExtractedConcept(
        name="Ser vs estar",
        explanation="Spanish has two verbs for 'to be': ser for essence, estar for state.",
        source_snippet="Ser vs estar: ser is for essence.",
        goal_relevance="core",
        confidence=0.9,
        flashcard_prompt="Which Spanish 'to be' verb is used for essence?",
        written_prompt="Explain the difference between ser and estar.",
    ),
]


async def make_topic(client, auth, name="Spanish") -> str:
    created = await client.post("/topics", json={"name": name}, headers=auth)
    return created.json()["id"]


async def make_material(client, auth, topic_id, content="Ser vs estar: ser is for essence.") -> str:
    created = await client.post(
        f"/topics/{topic_id}/materials", json={"content": content}, headers=auth
    )
    return created.json()["id"]


def stub_llm(monkeypatch, concepts=None):
    """Replace the LLM seam with a canned answer; capture the call's arguments."""
    calls = []

    async def fake_extract(material_content, goal):
        calls.append({"material_content": material_content, "goal": goal})
        return concepts if concepts is not None else STUB_CONCEPTS

    monkeypatch.setattr("app.extraction.llm_extract_concepts", fake_extract)
    return calls


def events_of(response_text: str) -> list[dict]:
    return [json.loads(line) for line in response_text.strip().splitlines()]


async def test_extract_persists_concepts_and_returns_them(client, make_user, monkeypatch):
    stub_llm(monkeypatch)
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)
    assert resp.status_code == 200

    result = events_of(resp.text)[-1]
    assert result["type"] == "result"
    [concept] = result["concepts"]
    assert concept["id"]
    assert concept["name"] == "Ser vs estar"
    assert concept["explanation"].startswith("Spanish has two verbs")
    assert concept["source_snippet"] == "Ser vs estar: ser is for essence."
    # No Goal set here, so "core" is capped to "supporting" (issue #26).
    assert concept["goal_relevance"] == "supporting"
    assert concept["confidence"] == 0.9

    # Persisted: the topic's concept list shows the same row.
    listed = await client.get(f"/topics/{topic_id}/concepts", headers=auth)
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [concept["id"]]


async def test_each_concept_gets_flashcard_and_written_questions(client, make_user, monkeypatch):
    stub_llm(monkeypatch)
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    by_kind = {q["kind"]: q["prompt"] for q in concept["questions"]}
    assert by_kind == {
        "flashcard": "Which Spanish 'to be' verb is used for essence?",
        "written": "Explain the difference between ser and estar.",
    }


async def test_extraction_streams_progress_before_result(client, make_user, monkeypatch):
    stub_llm(monkeypatch)
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)

    events = events_of(resp.text)
    assert len(events) >= 2
    assert all(e["type"] == "progress" for e in events[:-1])
    assert events[-1]["type"] == "result"


async def test_llm_failure_streams_an_error_event(client, make_user, monkeypatch):
    async def failing_extract(material_content, goal):
        raise RuntimeError("LLM call failed")

    monkeypatch.setattr("app.extraction.llm_extract_concepts", failing_extract)
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)

    assert resp.status_code == 200
    events = events_of(resp.text)
    assert events[-1]["type"] == "error"
    assert "LLM call failed" in events[-1]["message"]
    # Nothing was persisted for the failed extraction.
    assert (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json() == []


async def test_failed_save_rolls_back_partial_inserts(client, make_user, monkeypatch):
    two_concepts = STUB_CONCEPTS + [
        STUB_CONCEPTS[0].model_copy(update={"name": "Estar for states"})
    ]
    stub_llm(monkeypatch, concepts=two_concepts)

    from app import extraction

    real_insert = extraction.insert_concept
    calls = {"n": 0}

    async def insert_then_fail(conn, material, extracted):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("insert failed")
        return await real_insert(conn, material, extracted)

    monkeypatch.setattr("app.extraction.insert_concept", insert_then_fail)
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)

    assert events_of(resp.text)[-1]["type"] == "error"
    # The first concept's insert was rolled back, not committed.
    assert (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json() == []


async def test_no_goal_caps_relevance_at_supporting(client, make_user, monkeypatch):
    """With no Goal set, relevance can't be judged, so a 'core' Concept is capped
    to 'supporting' and left unscheduled (issue #26)."""
    stub_llm(monkeypatch)  # STUB_CONCEPTS has one 'core' concept
    _, auth = await make_user()  # no PUT /goal
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concept["goal_relevance"] == "supporting"
    assert concept["scheduled"] is False


async def test_with_goal_keeps_core_relevance(client, make_user, monkeypatch):
    """With a Goal set, a 'core' Concept stays 'core' and is scheduled (issue #26)."""
    stub_llm(monkeypatch)
    _, auth = await make_user()
    await client.put("/goal", json={"content": "Pass the DELE B2 exam"}, headers=auth)
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id)

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert concept["goal_relevance"] == "core"
    assert concept["scheduled"] is True


async def test_goal_is_passed_to_the_llm(client, make_user, monkeypatch):
    calls = stub_llm(monkeypatch)
    _, auth = await make_user()
    await client.put("/goal", json={"content": "Pass the DELE B2 exam"}, headers=auth)
    topic_id = await make_topic(client, auth)
    material_id = await make_material(client, auth, topic_id, content="Ser is for essence.")

    await client.post(f"/materials/{material_id}/extract", headers=auth)

    assert calls == [{"material_content": "Ser is for essence.", "goal": "Pass the DELE B2 exam"}]


async def test_rls_extract_and_concepts_hidden_across_users(client, make_user, monkeypatch):
    stub_llm(monkeypatch)
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    topic_id = await make_topic(client, auth_a)
    material_id = await make_material(client, auth_a, topic_id)

    # B cannot extract A's material, nor see A's topic concepts.
    assert (
        await client.post(f"/materials/{material_id}/extract", headers=auth_b)
    ).status_code == 404
    assert (await client.get(f"/topics/{topic_id}/concepts", headers=auth_b)).status_code == 404

    # A extracts; B still sees nothing, A sees the concept and its questions.
    await client.post(f"/materials/{material_id}/extract", headers=auth_a)
    assert (await client.get(f"/topics/{topic_id}/concepts", headers=auth_b)).status_code == 404
    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth_a)).json()
    assert concept["name"] == "Ser vs estar"
    assert len(concept["questions"]) == 2
