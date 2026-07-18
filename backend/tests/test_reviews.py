"""Review flow: due list, flashcard grading with a stubbed LLM, rescheduling."""

from app.llm import GradeResult

from tests.test_confirmation import concept_of
from tests.test_extraction import make_material, make_topic, stub_llm

STUB_GRADE = GradeResult(
    verdict="pass",
    correct_points=["Named ser for essence"],
    missing_points=["Did not mention estar"],
    misconceptions=[],
)


def stub_grading(monkeypatch, grade: GradeResult | None = None):
    """Replace the grading LLM seam with a canned verdict; capture call arguments."""
    calls = []

    async def fake_grade(explanation, source_snippet, question_prompt, answer):
        calls.append(
            {
                "explanation": explanation,
                "source_snippet": source_snippet,
                "question_prompt": question_prompt,
                "answer": answer,
            }
        )
        return grade if grade is not None else STUB_GRADE

    monkeypatch.setattr("app.reviews.llm_grade_answer", fake_grade)
    return calls


async def confirmed_scheduled_concept(client, auth, monkeypatch) -> tuple[str, dict]:
    """Extract one core Concept and confirm it; return (topic_id, concept)."""
    stub_llm(monkeypatch, concepts=[concept_of("core", "Core idea")])
    # The Topic needs a Goal for extraction-time relevance to be kept (ADR-0006).
    topic_id = await make_topic(client, auth)
    await client.patch(f"/topics/{topic_id}", json={"goal": "Learn the idea"}, headers=auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    await client.post(f"/materials/{material_id}/confirm", headers=auth)
    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    return topic_id, concept


async def test_due_list_shows_only_confirmed_scheduled_concepts(client, make_user, monkeypatch):
    _, auth = await make_user()
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "Core idea"), concept_of("irrelevant", "Irrelevant idea")],
    )
    topic_id = await make_topic(client, auth)
    await client.patch(f"/topics/{topic_id}", json={"goal": "Learn the idea"}, headers=auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)

    # Nothing is due before confirming.
    assert (await client.get(f"/topics/{topic_id}/due", headers=auth)).json() == []

    await client.post(f"/materials/{material_id}/confirm", headers=auth)
    due = (await client.get(f"/topics/{topic_id}/due", headers=auth)).json()
    # Only the scheduled (core) concept is due; it carries its flashcard Question.
    [entry] = due
    assert entry["name"] == "Core idea"
    [flashcard] = [q for q in entry["questions"] if q["kind"] == "flashcard"]
    assert flashcard["prompt"] == "Flashcard for Core idea?"


async def test_answer_returns_verdict_feedback_and_next_due(client, make_user, monkeypatch):
    stub_grading(monkeypatch)
    _, auth = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)
    [flashcard] = [q for q in concept["questions"] if q["kind"] == "flashcard"]

    answered = await client.post(
        f"/questions/{flashcard['id']}/answer",
        json={"answer": "Ser is used for essence."},
        headers=auth,
    )
    assert answered.status_code == 200
    body = answered.json()
    assert body["verdict"] == "pass"
    assert body["feedback"]["correct_points"] == ["Named ser for essence"]
    assert body["feedback"]["missing_points"] == ["Did not mention estar"]
    assert body["feedback"]["misconceptions"] == []
    assert body["next_due_at"] > body["created_at"]  # pass -> +3d, visible to the user

    # The concept is rescheduled into the future, so it leaves the due list.
    assert (await client.get(f"/topics/{topic_id}/due", headers=auth)).json() == []

    # The attempt persisted as a Review row.
    [review] = (await client.get(f"/concepts/{concept['id']}/reviews", headers=auth)).json()
    assert review["answer"] == "Ser is used for essence."
    assert review["verdict"] == "pass"
    assert review["feedback"]["missing_points"] == ["Did not mention estar"]
    assert review["created_at"]


async def test_fail_verdict_keeps_concept_due(client, make_user, monkeypatch):
    stub_grading(
        monkeypatch,
        grade=GradeResult(
            verdict="fail",
            correct_points=[],
            missing_points=["Everything"],
            misconceptions=["Estar is not only for locations"],
        ),
    )
    _, auth = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)
    [flashcard] = [q for q in concept["questions"] if q["kind"] == "flashcard"]

    answered = await client.post(
        f"/questions/{flashcard['id']}/answer", json={"answer": "No idea"}, headers=auth
    )
    assert answered.json()["verdict"] == "fail"
    # fail -> +0d: still due immediately.
    assert [c["id"] for c in (await client.get(f"/topics/{topic_id}/due", headers=auth)).json()] == [
        concept["id"]
    ]


async def test_grading_uses_only_explanation_snippet_and_answer(client, make_user, monkeypatch):
    calls = stub_grading(monkeypatch)
    _, auth = await make_user()
    _, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)
    [flashcard] = [q for q in concept["questions"] if q["kind"] == "flashcard"]

    await client.post(
        f"/questions/{flashcard['id']}/answer", json={"answer": "My answer"}, headers=auth
    )
    assert calls == [
        {
            "explanation": "Explanation of Core idea.",
            "source_snippet": "Snippet for Core idea.",
            "question_prompt": "Flashcard for Core idea?",
            "answer": "My answer",
        }
    ]


async def test_written_question_is_graded_the_same_way(client, make_user, monkeypatch):
    stub_grading(monkeypatch)
    _, auth = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth, monkeypatch)
    [written] = [q for q in concept["questions"] if q["kind"] == "written"]

    answered = await client.post(
        f"/questions/{written['id']}/answer",
        json={"answer": "In my own words: ser expresses essence."},
        headers=auth,
    )
    assert answered.status_code == 200
    body = answered.json()
    assert body["verdict"] == "pass"
    assert body["feedback"]["correct_points"] == ["Named ser for essence"]
    # The written attempt persists and reschedules like a flashcard one.
    assert (await client.get(f"/topics/{topic_id}/due", headers=auth)).json() == []


async def test_rls_blocks_answering_and_reading_other_users_reviews(
    client, make_user, monkeypatch
):
    stub_grading(monkeypatch)
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    topic_id, concept = await confirmed_scheduled_concept(client, auth_a, monkeypatch)
    [flashcard] = [q for q in concept["questions"] if q["kind"] == "flashcard"]

    assert (
        await client.post(
            f"/questions/{flashcard['id']}/answer", json={"answer": "hack"}, headers=auth_b
        )
    ).status_code == 404
    assert (await client.get(f"/topics/{topic_id}/due", headers=auth_b)).status_code == 404
    assert (
        await client.get(f"/concepts/{concept['id']}/reviews", headers=auth_b)
    ).status_code == 404
