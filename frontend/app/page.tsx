"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Concept, Topic } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

/** One proposed Topic from the extraction stream, edited in place before confirming. */
type Proposal = {
  name: string;
  goal: string;
  concept_ids: string[];
};

/** Reuse the current session or sign a throwaway demo user up (same demo auth everywhere). */
async function getToken(): Promise<string> {
  const { data } = await supabase.auth.getSession();
  if (data.session) return data.session.access_token;
  const email = `demo_${crypto.randomUUID()}@example.com`;
  const { data: signup, error } = await supabase.auth.signUp({
    email,
    password: "password123",
  });
  if (error || !signup.session) {
    throw new Error(`Auth failed: ${error?.message ?? "no session"}`);
  }
  return signup.session.access_token;
}

/** Global Home: the single paste box (ADR-0005). Extraction routes each Concept
 * into an existing Topic; what fits nowhere lands in the inbox below. */
export default function Home() {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [routed, setRouted] = useState<Concept[]>([]);
  const [inbox, setInbox] = useState<Concept[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [pendingMoves, setPendingMoves] = useState<Record<string, string>>({});
  const [savingMoves, setSavingMoves] = useState(false);

  async function loadTopics() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setTopics(await res.json());
  }

  async function loadInbox() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/unclassified`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setInbox(await res.json());
  }

  async function loadRouted() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/classified`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setRouted(await res.json());
  }

  useEffect(() => {
    loadTopics().catch((e) => setStatus(String(e)));
    loadInbox().catch(() => {});
    loadRouted().catch(() => {});
  }, []);

  /** Paste → extract (streamed) → auto-confirm; then refresh the inbox. */
  async function pasteMaterial(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setStatus("Pasting…");
    const token = await getToken();
    const res = await fetch(`${API_URL}/materials`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
    });
    if (!res.ok) {
      const body = await res.json();
      setStatus(typeof body.detail === "string" ? body.detail : `Paste failed (${res.status})`);
      return;
    }
    const material = await res.json();
    setContent("");

    const extract = await fetch(`${API_URL}/materials/${material.id}/extract`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!extract.ok || !extract.body) {
      setStatus(`Extraction failed (${extract.status})`);
      return;
    }
    const reader = extract.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let gotResult = false;
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === "progress") {
            setStatus(`Working… (${event.stage})`);
          } else if (event.type === "error") {
            setStatus(`Extraction failed: ${event.message} — try pasting again`);
            return;
          } else if (event.type === "result") {
            gotResult = true;
            setRouted(event.concepts);
            setProposals(
              (event.proposals ?? []).map(
                (p: { name: string; concept_ids: string[] }) => ({ ...p, goal: "" }),
              ),
            );
          }
        }
      }
    } catch {
      setStatus("Extraction failed: connection lost — try pasting again");
      return;
    }
    if (!gotResult) {
      setStatus("Extraction failed — try pasting again");
      return;
    }
    // No per-Concept approval at paste time (story 13): confirm right away.
    await fetch(`${API_URL}/materials/${material.id}/confirm`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    setStatus("Routed — see where each concept landed below");
    await loadInbox();
  }

  /** Confirm one proposed Topic: one atomic backend call creates it (with its
   * optional Goal) and files + scores its Concepts; a double submit is a no-op. */
  async function confirmProposal(index: number) {
    const proposal = proposals[index];
    if (!proposal.name.trim() || confirming) return;
    setConfirming(true);
    setStatus(`Creating topic "${proposal.name}"…`);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/topics/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: proposal.name.trim(),
          goal: proposal.goal.trim() || null,
          concept_ids: proposal.concept_ids,
        }),
      });
      if (!res.ok) {
        setStatus(`Topic creation failed (${res.status})`);
        return;
      }
      const topic: Topic = await res.json();
      setProposals((prev) => prev.filter((_, i) => i !== index));
      setRouted((prev) =>
        prev.map((c) =>
          proposal.concept_ids.includes(c.id) ? { ...c, topic_id: topic.id } : c,
        ),
      );
      setStatus(`Created "${topic.name}" and filed ${proposal.concept_ids.length} concept(s)`);
      await loadTopics();
      await loadInbox();
    } finally {
      setConfirming(false);
    }
  }

  /** Move one Concept out of a proposal: to the inbox, to another proposal
   * (local until that one is confirmed), or into an existing Topic (persisted). */
  async function moveProposalConcept(index: number, conceptId: string, dest: string) {
    if (dest.startsWith("topic:")) {
      await moveToTopic(conceptId, dest.slice("topic:".length));
    }
    setProposals((prev) =>
      prev
        .map((p, i) => {
          if (i === index) {
            return { ...p, concept_ids: p.concept_ids.filter((id) => id !== conceptId) };
          }
          if (dest === `proposal:${i}`) {
            return { ...p, concept_ids: [...p.concept_ids, conceptId] };
          }
          return p;
        })
        .filter((p) => p.concept_ids.length > 0),
    );
    if (dest === "inbox") await loadInbox();
  }

  /** Dismiss a proposal: its Concepts simply stay in the inbox. */
  function dismissProposal(index: number) {
    setProposals((prev) => prev.filter((_, i) => i !== index));
  }

  /** File an unclassified Concept into a Topic. */
  async function moveToTopic(conceptId: string, topicId: string) {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/${conceptId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ topic_id: topicId }),
    });
    if (!res.ok) {
      setStatus(`Move failed (${res.status})`);
      return;
    }
    setRouted((prev) => prev.map((c) => (c.id === conceptId ? { ...c, topic_id: topicId } : c)));
    await loadInbox();
  }

  const topicName = (topicId: string | null) =>
    topics.find((t) => t.id === topicId)?.name ?? "Inbox (unclassified)";

  /** Persist all pending topic reassignments picked on the landing page. */
  async function confirmPendingMoves() {
    setSavingMoves(true);
    try {
      for (const [conceptId, topicId] of Object.entries(pendingMoves)) {
        await moveToTopic(conceptId, topicId);
      }
      setPendingMoves({});
      setStatus("Topic changes saved");
    } finally {
      setSavingMoves(false);
    }
  }

  return (
    <div>
      <h1>Home</h1>
      <p>
        Paste what you just learned — concepts are extracted and filed into your{" "}
        <Link href="/topics">topics</Link> automatically.
      </p>
      <form onSubmit={pasteMaterial}>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste material text here"
          rows={8}
          style={{ width: "100%", padding: 8 }}
        />
        <button type="submit" style={{ padding: "8px 16px", marginTop: 8 }}>
          Paste material
        </button>
      </form>
      <p>{status}</p>
      {proposals.length > 0 && (
        <section className="card" style={{ borderColor: "var(--color-olive)" }}>
          <h2>Proposed new topics — confirm before anything is created</h2>
          {proposals.map((p, i) => (
            <div key={i} style={{ borderBottom: "1px solid #eee", padding: "8px 0" }}>
              <input
                value={p.name}
                onChange={(e) =>
                  setProposals((prev) =>
                    prev.map((q, j) => (j === i ? { ...q, name: e.target.value } : q)),
                  )
                }
                style={{ fontWeight: "bold", padding: 6, marginRight: 8 }}
              />
              <input
                value={p.goal}
                onChange={(e) =>
                  setProposals((prev) =>
                    prev.map((q, j) => (j === i ? { ...q, goal: e.target.value } : q)),
                  )
                }
                placeholder="Optional goal for this topic"
                style={{ padding: 6, width: "45%", marginRight: 8 }}
              />
              <button type="button" disabled={confirming} onClick={() => confirmProposal(i)}>
                {confirming ? "Creating…" : "Create topic"}
              </button>{" "}
              <button type="button" disabled={confirming} onClick={() => dismissProposal(i)}>
                Keep in inbox
              </button>
              <ul style={{ margin: "4px 0" }}>
                {p.concept_ids.map((cid) => (
                  <li key={cid} style={{ marginBottom: 2 }}>
                    {routed.find((c) => c.id === cid)?.name ?? "(unnamed concept)"}{" "}
                    <select
                      value=""
                      disabled={confirming}
                      onChange={(e) => {
                        if (e.target.value) moveProposalConcept(i, cid, e.target.value);
                      }}
                    >
                      <option value="" disabled>
                        Move to…
                      </option>
                      <option value="inbox">Inbox</option>
                      {proposals.map(
                        (q, j) =>
                          j !== i && (
                            <option key={j} value={`proposal:${j}`}>
                              Proposed: {q.name}
                            </option>
                          ),
                      )}
                      {topics.map((t) => (
                        <option key={t.id} value={`topic:${t.id}`}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
      {routed.length > 0 && (
        <section className="card">
          <h2>Where your concepts landed</h2>
          <ul>
            {routed.map((c) => (
              <li key={c.id} style={{ marginBottom: 4 }}>
                {c.name} →{" "}
                <select
                  value={pendingMoves[c.id] ?? c.topic_id ?? ""}
                  onChange={(e) => {
                    const topicId = e.target.value;
                    if (!topicId) return;
                    setPendingMoves((prev) =>
                      topicId === c.topic_id
                        ? Object.fromEntries(
                            Object.entries(prev).filter(([id]) => id !== c.id),
                          )
                        : { ...prev, [c.id]: topicId },
                    );
                  }}
                >
                  <option value="" disabled>
                    {topicName(c.topic_id)}
                  </option>
                  {topics.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </li>
            ))}
          </ul>
          {Object.keys(pendingMoves).length > 0 && (
            <button type="button" disabled={savingMoves} onClick={confirmPendingMoves}>
              {savingMoves ? "Saving…" : "Confirm topic changes"}
            </button>
          )}
        </section>
      )}
      <h2>Inbox</h2>
      {inbox.length === 0 ? (
        <p>Nothing unclassified — every concept has a topic.</p>
      ) : (
        <ul>
          {inbox.map((c) => (
            <li key={c.id} style={{ marginBottom: 4 }}>
              {c.name}{" "}
              <select
                defaultValue=""
                onChange={(e) => {
                  if (e.target.value) moveToTopic(c.id, e.target.value);
                }}
              >
                <option value="" disabled>
                  Move to topic…
                </option>
                {topics.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
      <p>
        <Link href="/topics">Go to topics</Link>
      </p>
    </div>
  );
}
