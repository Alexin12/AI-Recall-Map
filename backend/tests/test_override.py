"""Verdict override: one click replaces the AI verdict; scheduling follows it."""

from tests.test_reviews import confirmed_scheduled_concept, stub_grading


async def answer_flashcard(client, auth, concept, answer="My answer") -> dict:
    [flashcard] = [q for q in concept["questions"] if q["kind"] == "flashcard"]
    resp = await client.post(
        f"/questions/{flashcard['id']}/answer", json={"answer": answer}, headers=auth
    )
    return resp.json()


async def test_override_stores_both_verdicts_and_reschedules(client, make_user, monkeypatch):
    stub_grading(monkeypatch)  # AI verdict: pass (+3d)
    _, auth = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)
    review = await answer_flashcard(client, auth, concept)

    overridden = await client.post(
        f"/reviews/{review['id']}/override", json={"verdict": "strong"}, headers=auth
    )
    assert overridden.status_code == 200
    body = overridden.json()
    assert body["verdict"] == "strong"  # final verdict, what the Scheduler reads
    assert body["ai_verdict"] == "pass"
    assert body["verdict_overridden"] is True
    assert body["next_due_at"] > review["next_due_at"]  # strong (+7d) > pass (+3d)

    # The stored review reflects the override.
    [stored] = (await client.get(f"/concepts/{concept['id']}/reviews", headers=auth)).json()
    assert stored["verdict"] == "strong"
    assert stored["ai_verdict"] == "pass"
    assert stored["verdict_overridden"] is True


async def test_override_to_fail_puts_concept_back_on_due_list(client, make_user, monkeypatch):
    stub_grading(monkeypatch)  # AI verdict: pass -> concept leaves the due list
    _, auth = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)
    review = await answer_flashcard(client, auth, concept)
    assert (await client.get(f"/topics/{topic_id}/due", headers=auth)).json() == []

    await client.post(f"/reviews/{review['id']}/override", json={"verdict": "fail"}, headers=auth)

    due = (await client.get(f"/topics/{topic_id}/due", headers=auth)).json()
    assert [c["id"] for c in due] == [concept["id"]]


async def test_rls_blocks_overriding_other_users_review(client, make_user, monkeypatch):
    stub_grading(monkeypatch)
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth_a, monkeypatch)
    review = await answer_flashcard(client, auth_a, concept)

    assert (
        await client.post(
            f"/reviews/{review['id']}/override", json={"verdict": "strong"}, headers=auth_b
        )
    ).status_code == 404
