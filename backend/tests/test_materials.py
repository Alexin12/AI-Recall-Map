"""Material API: paste text into a Topic, size-limited, scoped by RLS."""


async def make_topic(client, auth, name="Spanish") -> str:
    created = await client.post("/topics", json={"name": name}, headers=auth)
    return created.json()["id"]


def extraction_stub(names: list[str]):
    """Canned extraction output: one Concept per name (mirrors test_goal.py)."""
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
            analogy=f"{name} is like something familiar.",
            technical_explanation=f"{name} explained technically.",
        )
        for name in names
    ]


async def paste_and_extract(client, auth, topic_id, content, names, monkeypatch):
    """Paste a Material and run extraction with a stubbed LLM; returns the Material id."""

    async def fake_extract(material_content, goal):
        return extraction_stub(names)

    monkeypatch.setattr("app.extraction.llm_extract_concepts", fake_extract)
    created = await client.post(
        f"/topics/{topic_id}/materials", json={"content": content}, headers=auth
    )
    material_id = created.json()["id"]
    resp = await client.post(f"/materials/{material_id}/extract", headers=auth)
    assert resp.status_code == 200
    return material_id


async def test_paste_material_into_topic(client, make_user):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)

    created = await client.post(
        f"/topics/{topic_id}/materials",
        json={"content": "Ser vs estar: ser is for essence."},
        headers=auth,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["id"]
    assert body["topic_id"] == topic_id
    assert body["content"] == "Ser vs estar: ser is for essence."


async def test_paste_over_limit_is_rejected_with_limit_in_message(client, make_user):
    from app.materials import MATERIAL_MAX_CHARS

    _, auth = await make_user()
    topic_id = await make_topic(client, auth)

    rejected = await client.post(
        f"/topics/{topic_id}/materials",
        json={"content": "x" * (MATERIAL_MAX_CHARS + 1)},
        headers=auth,
    )
    assert rejected.status_code == 413
    detail = rejected.json()["detail"]
    assert str(MATERIAL_MAX_CHARS) in detail
    assert "split" in detail.lower()


async def test_list_materials_of_topic(client, make_user):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)

    await client.post(
        f"/topics/{topic_id}/materials", json={"content": "first paste"}, headers=auth
    )
    await client.post(
        f"/topics/{topic_id}/materials", json={"content": "second paste"}, headers=auth
    )

    listed = await client.get(f"/topics/{topic_id}/materials", headers=auth)
    assert listed.status_code == 200
    assert [m["content"] for m in listed.json()] == ["first paste", "second paste"]


async def test_rls_hides_other_users_materials(client, make_user):
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    topic_id = await make_topic(client, auth_a)

    await client.post(
        f"/topics/{topic_id}/materials", json={"content": "A's material"}, headers=auth_a
    )

    # A's Topic is invisible to B, so B gets 404; A still sees their Material.
    assert (
        await client.get(f"/topics/{topic_id}/materials", headers=auth_b)
    ).status_code == 404
    assert [
        m["content"]
        for m in (await client.get(f"/topics/{topic_id}/materials", headers=auth_a)).json()
    ] == ["A's material"]


async def test_paste_into_other_users_topic_is_404(client, make_user):
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    topic_id = await make_topic(client, auth_a)

    pasted = await client.post(
        f"/topics/{topic_id}/materials", json={"content": "B's paste"}, headers=auth_b
    )
    assert pasted.status_code == 404


async def test_material_list_shows_concept_tags(client, make_user, monkeypatch):
    """Issue #29: the Material list carries each Material's extracted Concept
    names as tags, instead of the caller having to truncate raw content."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth)
    await paste_and_extract(
        client, auth, topic_id, "RAG notes", ["RAG", "Embeddings"], monkeypatch
    )
    await client.post(
        f"/topics/{topic_id}/materials", json={"content": "no concepts yet"}, headers=auth
    )

    listed = await client.get(f"/topics/{topic_id}/materials", headers=auth)
    assert listed.status_code == 200
    by_content = {m["content"]: m for m in listed.json()}
    assert set(by_content["RAG notes"]["concept_names"]) == {"RAG", "Embeddings"}
    assert by_content["no concepts yet"]["concept_names"] == []
