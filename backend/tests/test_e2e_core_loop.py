"""End-to-end core loop: paste -> extract -> confirm -> review -> override -> map.

One test walks the entire M1 loop through the public API, LLM seams stubbed.
"""

from app.llm import GradeResult

from tests.test_confirmation import concept_of
from tests.test_extraction import events_of, stub_llm
from tests.test_reviews import stub_grading


async def test_full_core_loop(client, make_user, monkeypatch):
    _, auth = await make_user()

    # 1. Set a Goal and create a Topic.
    await client.put("/goal", json={"content": "Learn Spanish for travel"}, headers=auth)
    topic_id = (await client.post("/topics", json={"name": "Spanish"}, headers=auth)).json()["id"]

    # 2. Paste a Material.
    material = (
        await client.post(
            f"/topics/{topic_id}/materials",
            json={"content": "Ser is for essence; estar is for states."},
            headers=auth,
        )
    ).json()

    # 3. Extraction streams progress and persists Concepts + Questions.
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "Ser vs estar"), concept_of("irrelevant", "Trivia")],
    )
    extract = await client.post(f"/materials/{material['id']}/extract", headers=auth)
    events = events_of(extract.text)
    assert events[0]["type"] == "progress"
    assert events[-1]["type"] == "result"
    assert len(events[-1]["concepts"]) == 2

    # 4. Confirmation: drop the irrelevant Concept, confirm the rest.
    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    [core] = [c for c in concepts if c["goal_relevance"] == "core"]
    [irrelevant] = [c for c in concepts if c["goal_relevance"] == "irrelevant"]
    assert (await client.delete(f"/concepts/{irrelevant['id']}", headers=auth)).status_code == 204
    await client.post(f"/materials/{material['id']}/confirm", headers=auth)

    # 5. The confirmed core Concept is due; answer its flashcard (verdict: pass).
    stub_grading(monkeypatch)
    [due] = (await client.get(f"/topics/{topic_id}/due", headers=auth)).json()
    assert due["id"] == core["id"]
    [flashcard] = [q for q in due["questions"] if q["kind"] == "flashcard"]
    review = (
        await client.post(
            f"/questions/{flashcard['id']}/answer",
            json={"answer": "Ser expresses essence."},
            headers=auth,
        )
    ).json()
    assert review["verdict"] == "pass"
    assert (await client.get(f"/topics/{topic_id}/due", headers=auth)).json() == []

    # 6. Override the verdict to fail: the Concept returns to the due list.
    overridden = (
        await client.post(
            f"/reviews/{review['id']}/override", json={"verdict": "fail"}, headers=auth
        )
    ).json()
    assert overridden["verdict_overridden"] is True
    assert [c["id"] for c in (await client.get(f"/topics/{topic_id}/due", headers=auth)).json()] == [
        core["id"]
    ]

    # 7. Concept detail reflects the history and derived mastery.
    detail = (await client.get(f"/concepts/{core['id']}", headers=auth)).json()
    assert detail["mastery"] == "weak"  # latest final verdict is fail
    assert detail["due"] is True
    assert len(detail["reviews"]) == 1

    # 8. The Concept Map shows the surviving Concept as a node.
    map_body = (await client.get(f"/topics/{topic_id}/map", headers=auth)).json()
    assert [n["name"] for n in map_body["nodes"]] == ["Ser vs estar"]
    assert map_body["relationships"] == []
