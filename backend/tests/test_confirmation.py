"""Confirmation API: approve, edit, delete, and toggle-schedule extracted Concepts."""

from app.llm import ExtractedConcept

from tests.test_extraction import make_material, make_topic, stub_llm


def concept_of(relevance: str, name: str) -> ExtractedConcept:
    return ExtractedConcept(
        name=name,
        explanation=f"Explanation of {name}.",
        source_snippet=f"Snippet for {name}.",
        goal_relevance=relevance,
        confidence=0.8,
        flashcard_prompt=f"Flashcard for {name}?",
        written_prompt=f"Explain {name}.",
        analogy=f"Analogy for {name}.",
        technical_explanation=f"Technical explanation of {name}.",
    )


async def extract_three(client, auth, monkeypatch) -> str:
    """Extract one core, one supporting, one irrelevant Concept; return topic_id."""
    stub_llm(
        monkeypatch,
        concepts=[
            concept_of("core", "Core idea"),
            concept_of("supporting", "Supporting idea"),
            concept_of("irrelevant", "Irrelevant idea"),
        ],
    )
    # The Topic needs a Goal for extraction-time relevance to be kept (ADR-0006).
    topic_id = await make_topic(client, auth)
    await client.patch(f"/topics/{topic_id}", json={"goal": "Learn the idea"}, headers=auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    return topic_id


async def test_scheduling_defaults_by_relevance(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await extract_three(client, auth, monkeypatch)

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    defaults = {c["goal_relevance"]: c["scheduled"] for c in concepts}
    assert defaults == {"core": True, "supporting": True, "irrelevant": False}
    assert all(c["confirmed"] is False for c in concepts)


async def test_edit_concept_name_and_explanation(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await extract_three(client, auth, monkeypatch)
    [core] = [
        c
        for c in (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
        if c["goal_relevance"] == "core"
    ]

    edited = await client.patch(
        f"/concepts/{core['id']}",
        json={"name": "Renamed idea", "explanation": "A better explanation."},
        headers=auth,
    )
    assert edited.status_code == 200
    body = edited.json()
    assert body["name"] == "Renamed idea"
    assert body["explanation"] == "A better explanation."
    assert body["scheduled"] is True  # untouched fields keep their values


async def test_toggle_scheduling(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await extract_three(client, auth, monkeypatch)
    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    [irrelevant] = [c for c in concepts if c["goal_relevance"] == "irrelevant"]

    toggled = await client.patch(
        f"/concepts/{irrelevant['id']}", json={"scheduled": True}, headers=auth
    )
    assert toggled.status_code == 200
    assert toggled.json()["scheduled"] is True
    assert toggled.json()["name"] == "Irrelevant idea"  # name untouched


async def test_delete_concept_removes_it_and_its_questions(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await extract_three(client, auth, monkeypatch)
    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    [irrelevant] = [c for c in concepts if c["goal_relevance"] == "irrelevant"]

    deleted = await client.delete(f"/concepts/{irrelevant['id']}", headers=auth)
    assert deleted.status_code == 204

    remaining = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert {c["goal_relevance"] for c in remaining} == {"core", "supporting"}


async def test_confirm_marks_remaining_concepts_confirmed(client, make_user, monkeypatch):
    _, auth = await make_user()
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "Core idea"), concept_of("supporting", "Supporting idea")],
    )
    topic_id = await make_topic(client, auth)
    await client.patch(f"/topics/{topic_id}", json={"goal": "Learn the idea"}, headers=auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)

    confirmed = await client.post(f"/materials/{material_id}/confirm", headers=auth)
    assert confirmed.status_code == 200

    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert all(c["confirmed"] is True for c in concepts)
    # Due-eligible = confirmed AND scheduled: core and supporting both review.
    assert {c["name"]: c["scheduled"] for c in concepts} == {
        "Core idea": True,
        "Supporting idea": True,
    }


async def test_rls_blocks_editing_and_deleting_other_users_concepts(
    client, make_user, monkeypatch
):
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    topic_id = await extract_three(client, auth_a, monkeypatch)
    [core] = [
        c
        for c in (await client.get(f"/topics/{topic_id}/concepts", headers=auth_a)).json()
        if c["goal_relevance"] == "core"
    ]

    assert (
        await client.patch(f"/concepts/{core['id']}", json={"name": "hacked"}, headers=auth_b)
    ).status_code == 404
    assert (await client.delete(f"/concepts/{core['id']}", headers=auth_b)).status_code == 404
    # A's concept is unchanged.
    [unchanged] = [
        c
        for c in (await client.get(f"/topics/{topic_id}/concepts", headers=auth_a)).json()
        if c["goal_relevance"] == "core"
    ]
    assert unchanged["name"] == "Core idea"
