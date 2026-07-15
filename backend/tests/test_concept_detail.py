"""Concept detail: one Concept with mastery, due state, questions, and history."""

from tests.test_override import answer_flashcard
from tests.test_reviews import confirmed_scheduled_concept, stub_grading


async def test_detail_shows_concept_mastery_due_state_and_history(
    client, make_user, monkeypatch
):
    stub_grading(monkeypatch)  # verdict: pass
    _, auth = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)

    # Before any review: weak and due.
    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["name"] == "Core idea"
    assert detail["explanation"] == "Explanation of Core idea."
    assert detail["source_snippet"] == "Snippet for Core idea."
    assert detail["mastery"] == "weak"
    assert detail["due"] is True
    assert {q["kind"] for q in detail["questions"]} == {"flashcard", "written"}
    assert detail["reviews"] == []

    # After one pass: learning, not due, history has the attempt.
    await answer_flashcard(client, auth, concept, answer="Ser is for essence.")
    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["mastery"] == "learning"
    assert detail["due"] is False
    [review] = detail["reviews"]
    assert review["answer"] == "Ser is for essence."
    assert review["verdict"] == "pass"
    assert review["feedback"]["missing_points"] == ["Did not mention estar"]
    assert review["created_at"]

    # After a second good attempt: strong.
    await answer_flashcard(client, auth, concept)
    detail = (await client.get(f"/concepts/{concept['id']}", headers=auth)).json()
    assert detail["mastery"] == "strong"
    assert len(detail["reviews"]) == 2


async def test_rls_hides_other_users_concept_detail(client, make_user, monkeypatch):
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth_a, monkeypatch)

    assert (await client.get(f"/concepts/{concept['id']}", headers=auth_b)).status_code == 404
