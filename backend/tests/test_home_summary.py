"""Global Home summary contract: one request for everything the Home needs.

`recently_learned` is interpreted as "most recently reviewed" Concepts (the
most recent review's created_at, distinct Concepts, newest first) rather
than "most recently confirmed" — confirmation has no timestamp of its own
(only the Concept's original created_at, which is extraction time, not
confirm time), while a review's created_at is a real, meaningful "when did
the learner last engage with this" signal.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db import engine
from app.llm import GradeResult

from tests.test_confirmation import concept_of
from tests.test_extraction import make_material, make_topic, stub_llm
from tests.test_override import answer_flashcard
from tests.test_reviews import stub_grading


async def confirmed_topic(client, auth, monkeypatch, topic_name: str, concept_names: list[str]) -> tuple[str, list[dict]]:
    """Extract + confirm one Topic's Concepts, all core (so all scheduled)."""
    stub_llm(monkeypatch, concepts=[concept_of("core", n) for n in concept_names])
    topic_id = await make_topic(client, auth, topic_name)
    await client.patch(f"/topics/{topic_id}", json={"goal": f"Learn {topic_name}"}, headers=auth)
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    await client.post(f"/materials/{material_id}/confirm", headers=auth)
    concepts = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    return topic_id, concepts


async def set_next_due(concept_id: str, when: datetime) -> None:
    """Directly set next_due_at — not reachable via the fixed-offset scheduler API."""
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE concepts SET next_due_at = :due WHERE id = :id"),
            {"due": when, "id": concept_id},
        )


async def make_unclassified_concept(client, auth, monkeypatch) -> None:
    """One Concept the extractor couldn't route to any Topic (ADR-0005 inbox)."""
    stub_llm(monkeypatch, concepts=[concept_of("core", "Loose idea")])
    topic_id = await make_topic(client, auth, "Temp")
    material_id = await make_material(client, auth, topic_id)
    await client.post(f"/materials/{material_id}/extract", headers=auth)
    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    await client.patch(f"/concepts/{concept['id']}", json={"topic_id": None}, headers=auth)


async def test_home_summary_returns_all_five_pieces_in_one_request(
    client, make_user, monkeypatch
):
    _, auth = await make_user()

    # Topic A: four Concepts covering all four Mastery States.
    topic_a, concepts_a = await confirmed_topic(
        client, auth, monkeypatch, "Spanish", ["Never idea", "Weak idea", "Strong idea", "Learning idea"]
    )
    by_name_a = {c["name"]: c for c in concepts_a}
    never_c = by_name_a["Never idea"]
    weak_c = by_name_a["Weak idea"]
    strong_c = by_name_a["Strong idea"]
    learning_c = by_name_a["Learning idea"]

    # Topic B: one never-reviewed Concept, to prove per-Topic (not global) buckets.
    topic_b, concepts_b = await confirmed_topic(client, auth, monkeypatch, "French", ["French idea"])
    french_c = concepts_b[0]

    # An unclassified Concept for the Inbox count.
    await make_unclassified_concept(client, auth, monkeypatch)

    # Build review history: strong needs its two most recent verdicts good.
    stub_grading(monkeypatch, grade=GradeResult(verdict="pass", correct_points=[], missing_points=[], misconceptions=[]))
    await answer_flashcard(client, auth, strong_c)
    stub_grading(monkeypatch, grade=GradeResult(verdict="strong", correct_points=[], missing_points=[], misconceptions=[]))
    await answer_flashcard(client, auth, strong_c)
    stub_grading(monkeypatch, grade=GradeResult(verdict="fail", correct_points=[], missing_points=[], misconceptions=[]))
    await answer_flashcard(client, auth, weak_c)
    stub_grading(monkeypatch, grade=GradeResult(verdict="pass", correct_points=[], missing_points=[], misconceptions=[]))
    await answer_flashcard(client, auth, learning_c)

    # Place Concepts across "needing review now" and the next five days. Anchored
    # to the actual current time (not midnight) so "later today" reliably stays
    # later today regardless of what hour the test happens to run at.
    now = datetime.now(timezone.utc)
    today = now.date()
    await set_next_due(weak_c["id"], now - timedelta(minutes=30))  # overdue -> needs review
    await set_next_due(never_c["id"], now + timedelta(minutes=5))  # due later today (day 0)
    await set_next_due(french_c["id"], now + timedelta(minutes=10))  # also day 0
    await set_next_due(learning_c["id"], now + timedelta(days=2))  # day 2
    await set_next_due(strong_c["id"], now + timedelta(days=4))  # day 4

    resp = await client.get("/home/summary", headers=auth)
    assert resp.status_code == 200
    body = resp.json()

    # (1) Concepts needing review right now, across all Topics.
    assert body["review_due_count"] == 1  # only weak_c is overdue

    # (2) Next five days' due counts. Day 0 (today) buckets by calendar date,
    # so it includes both the already-overdue weak_c and the later-today ones.
    days = body["next_five_days"]
    assert len(days) == 5
    assert [d["date"] for d in days] == [str(today + timedelta(days=i)) for i in range(5)]
    assert [d["count"] for d in days] == [3, 0, 1, 0, 1]

    # (3) Recently learned: distinct reviewed Concepts, most recently reviewed first.
    recently_learned_names = [c["name"] for c in body["recently_learned"]]
    assert recently_learned_names == ["Learning idea", "Weak idea", "Strong idea"]

    # (4) Per-Topic four-state Mastery distribution.
    by_topic = {t["topic_id"]: t for t in body["topic_mastery"]}
    assert by_topic[topic_a]["topic_name"] == "Spanish"
    assert by_topic[topic_a]["counts"] == {
        "never-reviewed": 1,
        "weak": 1,
        "learning": 1,
        "strong": 1,
    }
    assert by_topic[topic_b]["topic_name"] == "French"
    assert by_topic[topic_b]["counts"] == {
        "never-reviewed": 1,
        "weak": 0,
        "learning": 0,
        "strong": 0,
    }

    # (5) Inbox count: unclassified Concepts, same definition as /concepts/unclassified.
    unclassified = await client.get("/concepts/unclassified", headers=auth)
    assert body["inbox_count"] == len(unclassified.json()) == 1


async def test_next_five_days_folds_multi_day_overdue_into_today(
    client, make_user, monkeypatch
):
    """A Concept overdue by several days must still count toward today's
    bucket, not vanish because it falls before the 5-day window's start."""
    _, auth = await make_user()
    topic_id, concepts = await confirmed_topic(client, auth, monkeypatch, "Spanish", ["Stale idea"])
    stale_c = concepts[0]

    now = datetime.now(timezone.utc)
    await set_next_due(stale_c["id"], now - timedelta(days=3))

    resp = await client.get("/home/summary", headers=auth)
    body = resp.json()
    assert body["review_due_count"] == 1
    assert body["next_five_days"][0]["count"] == 1
    assert sum(d["count"] for d in body["next_five_days"][1:]) == 0


async def test_home_summary_is_empty_for_a_new_user(client, make_user):
    _, auth = await make_user()

    resp = await client.get("/home/summary", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["review_due_count"] == 0
    assert [d["count"] for d in body["next_five_days"]] == [0, 0, 0, 0, 0]
    assert body["recently_learned"] == []
    assert body["topic_mastery"] == []
    assert body["inbox_count"] == 0


async def test_rls_hides_other_users_home_summary(client, make_user, monkeypatch):
    _, auth_a = await make_user()
    _, auth_b = await make_user()
    await confirmed_topic(client, auth_a, monkeypatch, "Spanish", ["Idea"])

    body_b = (await client.get("/home/summary", headers=auth_b)).json()
    assert body_b["review_due_count"] == 0
    assert body_b["topic_mastery"] == []
    assert body_b["inbox_count"] == 0
