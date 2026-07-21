"""All Concepts: one purpose-built, Topic-scoped listing contract (issue #77)."""

from app.llm import ExtractedConcept

from tests.test_extraction import make_topic


def concept_of(name: str, relevance: str = "supporting") -> ExtractedConcept:
    return ExtractedConcept(
        name=name,
        explanation=f"Explanation of {name}.",
        source_snippet=f"Snippet for {name}.",
        goal_relevance=relevance,
        confidence=0.8,
        flashcard_prompt=f"Flashcard for {name}?",
        written_prompt=f"Explain {name}.",
        analogy=f"{name} is like something familiar.",
        technical_explanation=f"{name} explained technically.",
    )


async def extract_and_confirm(client, auth, topic_id, concepts, monkeypatch):
    """Extract the given canned Concepts into topic_id and confirm them all."""

    async def fake_extract(material_content, goal):
        return concepts

    monkeypatch.setattr("app.extraction.llm_extract_concepts", fake_extract)
    created = await client.post(
        f"/topics/{topic_id}/materials", json={"content": "notes"}, headers=auth
    )
    material_id = created.json()["id"]
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    await client.post(f"/materials/{material_id}/confirm", headers=auth)
    listed = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    return {c["name"]: c for c in listed}


async def answer_written_question(client, auth, concept_id, answer, verdict, monkeypatch):
    """Answer the Concept's written Question with a stubbed grade, producing a Review."""
    from app.llm import GradeResult

    async def fake_grade(explanation, source_snippet, question_prompt, ans):
        return GradeResult(verdict=verdict, correct_points=[], missing_points=[], misconceptions=[])

    monkeypatch.setattr("app.reviews.llm_grade_answer", fake_grade)
    detail = (await client.get(f"/concepts/{concept_id}", headers=auth)).json()
    written = next(q for q in detail["questions"] if q["kind"] == "written")
    resp = await client.post(
        f"/questions/{written['id']}/answer", json={"answer": answer}, headers=auth
    )
    assert resp.status_code == 200
    return resp.json()


async def test_single_request_returns_full_contract_fields(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, "RAG systems")
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)
    by_name = await extract_and_confirm(client, auth, topic_id, [concept_of("RAG", "core")], monkeypatch)
    concept_id = by_name["RAG"]["id"]
    await answer_written_question(client, auth, concept_id, "it retrieves then generates", "pass", monkeypatch)

    resp = await client.get(f"/topics/{topic_id}/all-concepts", headers=auth)
    assert resp.status_code == 200
    [row] = resp.json()
    assert row["name"] == "RAG"
    assert row["goal_relevance"] == "core"
    assert row["topic_id"] == topic_id
    assert row["topic_name"] == "RAG systems"
    assert row["last_verdict"] == "pass"
    assert row["last_reviewed_at"] is not None
    assert row["next_due_date"] is not None
    assert row["written_question"] == "Explain RAG."
    assert row["written_answer"] == "it retrieves then generates"


async def test_next_due_hidden_when_topic_has_no_goal(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, "Browsing only")
    await extract_and_confirm(client, auth, topic_id, [concept_of("Loose fact")], monkeypatch)

    [row] = (await client.get(f"/topics/{topic_id}/all-concepts", headers=auth)).json()
    assert row["goal_relevance"] is None
    assert row["next_due_date"] is None


async def test_next_due_hidden_when_unscheduled(client, make_user, monkeypatch):
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, "Mixed relevance")
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)
    await extract_and_confirm(
        client, auth, topic_id, [concept_of("Irrelevant thing", "irrelevant")], monkeypatch
    )

    [row] = (await client.get(f"/topics/{topic_id}/all-concepts", headers=auth)).json()
    assert row["goal_relevance"] == "irrelevant"
    assert row["next_due_date"] is None


async def test_ordering_due_now_then_next_due_then_relevance_then_name(client, make_user, monkeypatch):
    """Deliberately grade each Concept to a distinct schedule state (rather than
    relying on default next_due_at, which every fresh Concept shares) so the
    due-now / nearest-next-due / unscheduled buckets are unambiguous."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, "Ordering")
    await client.patch(f"/topics/{topic_id}", json={"goal": "learn things"}, headers=auth)
    by_name = await extract_and_confirm(
        client,
        auth,
        topic_id,
        [concept_of("Zebra", "core"), concept_of("Apple", "supporting"), concept_of("Mango", "irrelevant")],
        monkeypatch,
    )
    # Zebra: "fail" -> next_due_at = now() (due right now).
    await answer_written_question(client, auth, by_name["Zebra"]["id"], "wrong", "fail", monkeypatch)
    # Apple: "pass" -> next_due_at = now() + 3 days (scheduled, but not due yet).
    await answer_written_question(client, auth, by_name["Apple"]["id"], "close enough", "pass", monkeypatch)
    # Mango: irrelevant -> unscheduled, never due, next-due hidden.

    rows = (await client.get(f"/topics/{topic_id}/all-concepts", headers=auth)).json()
    names = [r["name"] for r in rows]
    assert names == ["Zebra", "Apple", "Mango"]


async def test_unknown_topic_is_404(client, make_user):
    _, auth = await make_user()
    resp = await client.get(
        "/topics/00000000-0000-0000-0000-000000000000/all-concepts", headers=auth
    )
    assert resp.status_code == 404
