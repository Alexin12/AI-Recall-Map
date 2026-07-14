"""Topic API: create and list, scoped to the authenticated user by RLS."""


async def test_create_topic(client, make_user):
    _, auth = await make_user()

    created = await client.post("/topics", json={"name": "Spanish"}, headers=auth)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Spanish"
    assert body["id"]


async def test_list_topics(client, make_user):
    _, auth = await make_user()

    await client.post("/topics", json={"name": "Spanish"}, headers=auth)
    await client.post("/topics", json={"name": "Calculus"}, headers=auth)

    listed = await client.get("/topics", headers=auth)
    assert listed.status_code == 200
    assert [t["name"] for t in listed.json()] == ["Spanish", "Calculus"]


async def test_rls_hides_other_users_topics(client, make_user):
    _, auth_a = await make_user()
    _, auth_b = await make_user()

    await client.post("/topics", json={"name": "A's topic"}, headers=auth_a)

    # User B cannot see A's Topic; user A still sees their own.
    assert (await client.get("/topics", headers=auth_b)).json() == []
    assert [
        t["name"] for t in (await client.get("/topics", headers=auth_a)).json()
    ] == ["A's topic"]


async def test_unauthenticated_is_rejected(client):
    assert (await client.get("/topics")).status_code == 401
