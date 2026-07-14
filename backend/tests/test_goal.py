"""Goal endpoints: one editable Goal per user, RLS-scoped."""

from sqlalchemy import text

from app.db import engine


async def test_put_creates_goal(client, make_user):
    user_id, auth = await make_user()

    resp = await client.put(
        "/goal", json={"content": "become an AI engineer"}, headers=auth
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "become an AI engineer"
    assert {"id", "content", "created_at", "updated_at"} <= body.keys()

    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT content FROM goals WHERE user_id = :uid"),
                {"uid": user_id},
            )
        ).all()
    assert [r.content for r in rows] == ["become an AI engineer"]


async def test_put_edits_existing_goal_keeping_one_row(client, make_user):
    user_id, auth = await make_user()

    await client.put("/goal", json={"content": "first draft"}, headers=auth)
    resp = await client.put("/goal", json={"content": "revised goal"}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["content"] == "revised goal"

    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT content FROM goals WHERE user_id = :uid"),
                {"uid": user_id},
            )
        ).all()
    assert [r.content for r in rows] == ["revised goal"]


async def test_get_returns_goal_or_404(client, make_user):
    _, auth = await make_user()

    assert (await client.get("/goal", headers=auth)).status_code == 404

    await client.put("/goal", json={"content": "learn RAG"}, headers=auth)
    resp = await client.get("/goal", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["content"] == "learn RAG"


async def test_rls_hides_goal_across_users(client, make_user):
    _, auth_a = await make_user()
    _, auth_b = await make_user()

    await client.put("/goal", json={"content": "A's goal"}, headers=auth_a)

    # B sees no goal; B setting their own does not touch A's.
    assert (await client.get("/goal", headers=auth_b)).status_code == 404
    await client.put("/goal", json={"content": "B's goal"}, headers=auth_b)
    assert (await client.get("/goal", headers=auth_a)).json()["content"] == "A's goal"


async def test_unauthenticated_is_rejected(client):
    assert (await client.get("/goal")).status_code == 401
    assert (await client.put("/goal", json={"content": "x"})).status_code == 401
