"""Proposed Topics + Confirmation actions (ADR-0005): leftovers are clustered
into a few high-level proposed Topics that the user confirms — the model never
auto-commits a Topic. The extraction / router / proposal LLM calls are stubbed.
"""

from app.prompts.proposal_v1 import PROPOSAL_SYSTEM_PROMPT_V1

from tests.test_confirmation import concept_of
from tests.test_extraction import make_topic, stub_llm
from tests.test_routing import paste_and_extract, stub_router


def test_proposal_prompt_teaches_broad_sibling_domain_grouping():
    """Prompt coverage (issue #60): the sibling-domain example and the rule
    that broad grouping must not merge unrelated subjects are both spelled out."""
    prompt = PROPOSAL_SYSTEM_PROMPT_V1
    assert "Korean" in prompt and "Chinese" in prompt
    assert "Language Learning" in prompt
    assert "subfield" in prompt.lower()
    assert "unrelated" in prompt.lower()


def stub_proposals(monkeypatch, groups: dict[str, list[str]]):
    """Stub the proposal seam: cluster orphan Concept names into proposed Topics."""
    calls = []

    async def fake_propose(topics, concepts):
        calls.append(
            {"topics": [t["name"] for t in topics], "names": [c["name"] for c in concepts]}
        )
        name_to_group = {n: g for g, names in groups.items() for n in names}
        out: dict[str, list[int]] = {}
        for i, c in enumerate(concepts):
            out.setdefault(name_to_group[c["name"]], []).append(i)
        return [{"name": g, "indexes": idxs} for g, idxs in out.items()]

    monkeypatch.setattr("app.extraction.llm_propose_topics", fake_propose)
    return calls


async def test_mixed_sibling_domains_propose_one_broad_topic(
    client, make_user, monkeypatch
):
    """A Korean-learning + Chinese-learning Material yields one broad
    'Language Learning' proposal covering both Concepts, marked as new
    (topic_id None) since no matching Topic exists yet (issue #60)."""
    _, auth = await make_user()
    stub_llm(
        monkeypatch,
        concepts=[
            concept_of("core", "Korean particles"),
            concept_of("core", "Chinese tones"),
        ],
    )
    stub_router(monkeypatch, {"Korean particles": None, "Chinese tones": None})
    stub_proposals(
        monkeypatch,
        {"Language Learning": ["Korean particles", "Chinese tones"]},
    )

    _, events = await paste_and_extract(client, auth)

    [proposal] = events[-1]["proposals"]
    assert proposal["name"] == "Language Learning"
    assert proposal["topic_id"] is None
    assert len(proposal["concept_ids"]) == 2


async def test_existing_broad_topic_is_reused_in_proposals(client, make_user, monkeypatch):
    """The proposer sees the user's existing Topics; a proposal matching one is
    a reuse — its topic_id points at that Topic instead of minting a new one."""
    _, auth = await make_user()
    lang_topic = await make_topic(client, auth, "Language Learning")
    stub_llm(monkeypatch, concepts=[concept_of("core", "Korean particles")])
    stub_router(monkeypatch, {"Korean particles": None})
    calls = stub_proposals(monkeypatch, {"Language Learning": ["Korean particles"]})

    _, events = await paste_and_extract(client, auth)

    assert calls[0]["topics"] == ["Language Learning"]
    [proposal] = events[-1]["proposals"]
    assert proposal["name"] == "Language Learning"
    assert proposal["topic_id"] == lang_topic


async def test_broad_grouping_keeps_unrelated_subjects_apart(
    client, make_user, monkeypatch
):
    """Sibling language subfields share one bucket, but an unrelated subject
    (bookkeeping) stays its own proposal — broad, not merged (issue #60)."""
    _, auth = await make_user()
    stub_llm(
        monkeypatch,
        concepts=[
            concept_of("core", "Korean particles"),
            concept_of("core", "Chinese tones"),
            concept_of("core", "Double-entry bookkeeping"),
        ],
    )
    stub_router(
        monkeypatch,
        {"Korean particles": None, "Chinese tones": None, "Double-entry bookkeeping": None},
    )
    stub_proposals(
        monkeypatch,
        {
            "Language Learning": ["Korean particles", "Chinese tones"],
            "Accounting": ["Double-entry bookkeeping"],
        },
    )

    _, events = await paste_and_extract(client, auth)

    by_name = {p["name"]: p for p in events[-1]["proposals"]}
    assert set(by_name) == {"Language Learning", "Accounting"}
    assert len(by_name["Language Learning"]["concept_ids"]) == 2
    assert len(by_name["Accounting"]["concept_ids"]) == 1


async def test_user_can_rename_or_split_a_broad_proposal_at_confirmation(
    client, make_user, monkeypatch
):
    """A broad proposal is only a suggestion: the user can split it into
    Topics of their own naming and file each Concept where they choose."""
    _, auth = await make_user()
    stub_llm(
        monkeypatch,
        concepts=[
            concept_of("core", "Korean particles"),
            concept_of("core", "Chinese tones"),
        ],
    )
    stub_router(monkeypatch, {"Korean particles": None, "Chinese tones": None})
    stub_proposals(
        monkeypatch,
        {"Language Learning": ["Korean particles", "Chinese tones"]},
    )
    _, events = await paste_and_extract(client, auth)
    [proposal] = events[-1]["proposals"]
    concept_names = {c["id"]: c["name"] for c in events[-1]["concepts"]}

    # Split: two user-named Topics instead of the proposed single bucket.
    korean = (await client.post("/topics", json={"name": "Korean"}, headers=auth)).json()
    chinese = (await client.post("/topics", json={"name": "Chinese"}, headers=auth)).json()
    target = {"Korean particles": korean["id"], "Chinese tones": chinese["id"]}
    for concept_id in proposal["concept_ids"]:
        moved = await client.patch(
            f"/concepts/{concept_id}",
            json={"topic_id": target[concept_names[concept_id]]},
            headers=auth,
        )
        assert moved.status_code == 200

    [in_korean] = (await client.get(f"/topics/{korean['id']}/concepts", headers=auth)).json()
    assert in_korean["name"] == "Korean particles"
    [in_chinese] = (await client.get(f"/topics/{chinese['id']}/concepts", headers=auth)).json()
    assert in_chinese["name"] == "Chinese tones"
    assert (await client.get("/concepts/unclassified", headers=auth)).json() == []


async def test_first_paste_proposes_topics_without_committing_them(
    client, make_user, monkeypatch
):
    _, auth = await make_user()  # no Topics at all
    stub_llm(
        monkeypatch,
        concepts=[
            concept_of("core", "Chunking"),
            concept_of("core", "Embeddings"),
            concept_of("core", "Flexbox"),
        ],
    )
    stub_router(monkeypatch, {"Chunking": None, "Embeddings": None, "Flexbox": None})
    stub_proposals(monkeypatch, {"RAG": ["Chunking", "Embeddings"], "CSS": ["Flexbox"]})

    _, events = await paste_and_extract(client, auth)

    result = events[-1]
    assert result["type"] == "result"
    proposals = result["proposals"]
    by_name = {p["name"]: p for p in proposals}
    assert set(by_name) == {"RAG", "CSS"}
    concept_names = {c["id"]: c["name"] for c in result["concepts"]}
    assert [concept_names[cid] for cid in by_name["RAG"]["concept_ids"]] == [
        "Chunking",
        "Embeddings",
    ]
    # Nothing was committed: no Topics exist, all Concepts sit in the inbox.
    assert (await client.get("/topics", headers=auth)).json() == []
    inbox = (await client.get("/concepts/unclassified", headers=auth)).json()
    assert len(inbox) == 3


async def test_confirming_a_proposal_creates_topic_with_goal_and_files_concepts(
    client, make_user, monkeypatch
):
    """Confirmation: create the proposed Topic (with an optional Goal) and move
    its Concepts in; a Goal set on the confirmation step scores them (story 10)."""
    _, auth = await make_user()
    stub_llm(monkeypatch, concepts=[concept_of("core", "Chunking")])
    stub_router(monkeypatch, {"Chunking": None})
    stub_proposals(monkeypatch, {"RAG": ["Chunking"]})
    _, events = await paste_and_extract(client, auth)
    [proposal] = events[-1]["proposals"]

    async def fake_score(goal, concepts):
        assert goal == "build RAG apps"
        return {c["id"]: "core" for c in concepts}

    monkeypatch.setattr("app.confirmation.llm_score_relevance", fake_score)

    created = await client.post(
        "/topics", json={"name": "RAG", "goal": "build RAG apps"}, headers=auth
    )
    assert created.status_code == 201
    assert created.json()["goal"] == "build RAG apps"
    topic_id = created.json()["id"]
    for concept_id in proposal["concept_ids"]:
        moved = await client.patch(
            f"/concepts/{concept_id}", json={"topic_id": topic_id}, headers=auth
        )
        assert moved.status_code == 200

    [chunking] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()
    assert chunking["goal_relevance"] == "core"
    assert chunking["scheduled"] is True
    assert (await client.get("/concepts/unclassified", headers=auth)).json() == []


async def test_double_submitting_a_confirmation_creates_one_topic(
    client, make_user, monkeypatch
):
    """POST /topics/confirm twice with the same payload (issue #52 double-click):
    exactly one Topic, Concepts filed and scored exactly once."""
    _, auth = await make_user()
    stub_llm(
        monkeypatch,
        concepts=[concept_of("core", "Chunking"), concept_of("core", "Embeddings")],
    )
    stub_router(monkeypatch, {"Chunking": None, "Embeddings": None})
    stub_proposals(monkeypatch, {"RAG": ["Chunking", "Embeddings"]})
    _, events = await paste_and_extract(client, auth)
    [proposal] = events[-1]["proposals"]

    score_calls = []

    async def fake_score(goal, concepts):
        score_calls.append(goal)
        return {c["id"]: "core" for c in concepts}

    monkeypatch.setattr("app.confirmation.llm_score_relevance", fake_score)
    payload = {
        "name": "RAG",
        "goal": "build RAG apps",
        "concept_ids": proposal["concept_ids"],
    }

    first = await client.post("/topics/confirm", json=payload, headers=auth)
    second = await client.post("/topics/confirm", json=payload, headers=auth)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    topics = (await client.get("/topics", headers=auth)).json()
    assert len(topics) == 1
    assert topics[0]["goal"] == "build RAG apps"
    assert score_calls == ["build RAG apps"]  # scored once, not per submit

    filed = (await client.get(f"/topics/{topics[0]['id']}/concepts", headers=auth)).json()
    assert {c["name"] for c in filed} == {"Chunking", "Embeddings"}
    assert all(c["goal_relevance"] == "core" and c["scheduled"] for c in filed)
    assert (await client.get("/concepts/unclassified", headers=auth)).json() == []


async def test_dropping_a_concept_to_the_inbox(client, make_user, monkeypatch):
    """An explicit null topic_id unfiles the Concept: back to the inbox, unscored."""
    _, auth = await make_user()
    topic_id = await make_topic(client, auth, "RAG")
    await client.patch(f"/topics/{topic_id}", json={"goal": "build RAG apps"}, headers=auth)
    stub_llm(monkeypatch, concepts=[concept_of("core", "Chunking")])
    stub_router(monkeypatch, {"Chunking": topic_id})

    async def fake_score(goal, concepts):
        return {c["id"]: "core" for c in concepts}

    monkeypatch.setattr("app.extraction.llm_score_relevance", fake_score)
    await paste_and_extract(client, auth)
    [concept] = (await client.get(f"/topics/{topic_id}/concepts", headers=auth)).json()

    dropped = await client.patch(
        f"/concepts/{concept['id']}", json={"topic_id": None}, headers=auth
    )
    assert dropped.status_code == 200
    assert dropped.json()["topic_id"] is None
    assert dropped.json()["goal_relevance"] is None
    assert dropped.json()["scheduled"] is False
    [inboxed] = (await client.get("/concepts/unclassified", headers=auth)).json()
    assert inboxed["id"] == concept["id"]
