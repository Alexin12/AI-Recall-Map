"""End-to-end tracer bullet: HTTP -> auth -> Postgres, and the RLS boundary."""


async def test_ping_roundtrip(client, make_user):
    _, auth = await make_user()

    created = await client.post("/pings", json={"message": "hello"}, headers=auth)
    assert created.status_code == 201
    assert created.json()["message"] == "hello"

    listed = await client.get("/pings", headers=auth)
    assert listed.status_code == 200
    assert [p["message"] for p in listed.json()] == ["hello"]


async def test_rls_hides_other_users_rows(client, make_user):
    _, auth_a = await make_user()
    _, auth_b = await make_user()

    await client.post("/pings", json={"message": "A's secret"}, headers=auth_a)

    # User B cannot see A's row; user A still sees their own.
    assert (await client.get("/pings", headers=auth_b)).json() == []
    assert [p["message"] for p in (await client.get("/pings", headers=auth_a)).json()] == [
        "A's secret"
    ]


async def test_unauthenticated_is_rejected(client):
    assert (await client.get("/pings")).status_code == 401
