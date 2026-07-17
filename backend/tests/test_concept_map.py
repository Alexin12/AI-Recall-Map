"""Concept Map: nodes and relationship rows for a Topic, ready for React Flow."""

from sqlalchemy import text

from app.db import engine

from tests.test_confirmation import concept_of
from tests.test_extraction import make_material, make_topic, stub_llm


async def extract_two(client, auth, monkeypatch) -> str:
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "First idea"), concept_of("supporting", "Second idea")],
    )
    topic_id = await make_topic(client, auth)
    await client.patch(f"/topics/{topic_id}", json={"goal": "Learn the idea"}, headers=auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    return topic_id


async def test_map_returns_concept_nodes_and_relationship_rows(
    client, make_user, monkeypatch
):
    _, auth = await make_user()
    topic_id = await extract_two(client, auth, monkeypatch)

    resp = await client.get(f"/topics/{topic_id}/map", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert {n["name"] for n in body["nodes"]} == {"First idea", "Second idea"}
    for node in body["nodes"]:
        assert node["id"]
        assert node["goal_relevance"] in ("core", "supporting")
    assert body["relationships"] == []


async def test_map_includes_relationship_rows(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await extract_two(client, auth, monkeypatch)
    nodes = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()["nodes"]
    by_name = {n["name"]: n["id"] for n in nodes}

    # No API creates relationships in M1; seed one plain Postgres row (ADR-0002).
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO concept_relationships "
                "(user_id, topic_id, from_concept_id, to_concept_id, kind) "
                "SELECT user_id, topic_id, :from_id, :to_id, 'related' "
                "FROM concepts WHERE id = :from_id"
            ),
            {"from_id": by_name["First idea"], "to_id": by_name["Second idea"]},
        )

    body = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()
    [rel] = body["relationships"]
    assert rel["from_concept_id"] == by_name["First idea"]
    assert rel["to_concept_id"] == by_name["Second idea"]
    assert rel["kind"] == "related"


async def test_rls_hides_other_users_map(client, make_user, monkeypatch):
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    topic_id = await extract_two(client, auth_a, monkeypatch)

    assert (await client.get(f"/topics/{topic_id}/map", headers=auth_b)).status_code == 404
