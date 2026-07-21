"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Concept, ConceptMap as ConceptMapData, Material, TreeNode } from "@/types";
import ConceptMap from "./ConceptMap";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

/** Guidance only (issue #78) — never gates saving, never calls a model. */
const EXAMPLE_GOALS = [
  "build RAG apps for production",
  "pass the AWS Solutions Architect exam",
  "understand distributed systems for interviews",
  "learn conversational Spanish",
  "master data structures & algorithms",
];

/** Tally weak/learning/strong Mastery States across the tree; never-reviewed is reported separately. */
function tallyMastery(
  nodes: TreeNode[],
  counts = { weak: 0, learning: 0, strong: 0, neverReviewed: 0 },
) {
  for (const node of nodes) {
    if (node.mastery === "never-reviewed") counts.neverReviewed++;
    else counts[node.mastery]++;
    tallyMastery(node.children, counts);
  }
  return counts;
}

/** Reuse the current session or sign a throwaway demo user up (same demo auth as the home page). */
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

/** Topic Page: paste Materials now; mastery and the Concept Tree arrive in later slices. */
export default function TopicPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [status, setStatus] = useState("Loading…");
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [due, setDue] = useState<Concept[]>([]);
  const [map, setMap] = useState<ConceptMapData | null>(null);
  const [goal, setGoal] = useState<string | null>(null);
  const [topicName, setTopicName] = useState("");
  const [goalDraft, setGoalDraft] = useState("");
  const [showRelevance, setShowRelevance] = useState(true);
  const [clearConfirming, setClearConfirming] = useState(false);
  const [undoGoal, setUndoGoal] = useState<string | null>(null);

  async function loadGoal() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const topics: { id: string; name: string; goal: string | null }[] = await res.json();
    const topic = topics.find((t) => t.id === id);
    setGoal(topic?.goal ?? null);
    setGoalDraft(topic?.goal ?? "");
    setTopicName(topic?.name ?? "");
  }

  /** Set or clear this Topic's Goal; the backend rescores relevance (Phase 2). */
  async function saveGoal(next: string | null) {
    setStatus(next ? "Saving Goal and scoring relevance…" : "Clearing Goal…");
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ goal: next }),
    });
    if (!res.ok) {
      setStatus(`Goal save failed (${res.status})`);
      return;
    }
    const topic: { goal: string | null } = await res.json();
    setGoal(topic.goal);
    setGoalDraft(topic.goal ?? "");
    setStatus(topic.goal ? "Goal saved — relevance rescored" : "Goal cleared");
    await loadConcepts();
    await loadDue();
  }

  /** Inline "are you sure?" confirm for Clear Goal, plus Undo restoring the prior value. */
  async function confirmClear() {
    const previous = goal;
    setClearConfirming(false);
    await saveGoal(null);
    setUndoGoal(previous);
  }

  async function undoClear() {
    if (!undoGoal) return;
    const restored = undoGoal;
    setUndoGoal(null);
    await saveGoal(restored);
  }

  async function loadConcepts() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics/${id}/concepts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setConcepts(await res.json());
    const mapRes = await fetch(`${API_URL}/topics/${id}/map`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (mapRes.ok) setMap(await mapRes.json());
  }

  /** Scheduled Concepts of this Topic that are due for review right now. */
  async function loadDue() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics/${id}/due`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setDue(await res.json());
  }

  async function loadMaterials() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics/${id}/materials`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setStatus(`Could not load materials (${res.status})`);
      return;
    }
    const rows: Material[] = await res.json();
    setMaterials(rows);
    setStatus(`${rows.length} material(s)`);
  }

  useEffect(() => {
    loadMaterials().catch((e) => setStatus(String(e)));
    loadConcepts().catch(() => {});
    loadDue().catch(() => {});
    loadGoal().catch(() => {});
  }, []);

  /** Override a Concept's relevance (the user's final say, story 14). */
  async function overrideRelevance(
    conceptId: string,
    relevance: "irrelevant" | "supporting" | "core",
  ) {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/${conceptId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ goal_relevance: relevance }),
    });
    if (!res.ok) {
      setStatus(`Relevance override failed (${res.status})`);
      return;
    }
    const updated: Concept = await res.json();
    setConcepts((prev) => prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c)));
    await loadDue();
  }

  return (
    <div>
      <h1>{topicName || "Topic"}</h1>
      <section
        className="card"
        style={goal ? undefined : { borderColor: "var(--color-olive)", background: "var(--color-sand)" }}
      >
        <strong>Topic Goal</strong>
        {!goal && (
          <p style={{ margin: "4px 0" }}>
            No Goal set — this Topic stays browsable but nothing is scored or scheduled
            for review. Set a Goal to get relevance-based review.
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (goalDraft.trim()) {
              setUndoGoal(null);
              saveGoal(goalDraft.trim());
            }
          }}
        >
          <input
            value={goalDraft}
            onChange={(e) => setGoalDraft(e.target.value)}
            placeholder="e.g. build RAG apps for production"
            style={{ width: "70%", padding: 8, marginRight: 8 }}
          />
          <button
            type="submit"
            disabled={!goalDraft.trim() || goalDraft.trim() === goal}
            style={{ padding: "8px 16px" }}
          >
            Save Goal
          </button>{" "}
          {goal && !clearConfirming && (
            <button type="button" onClick={() => setClearConfirming(true)}>
              Clear Goal
            </button>
          )}
          {clearConfirming && (
            <span>
              Clear this Goal? Concepts will stop being scored and scheduled.{" "}
              <button type="button" onClick={confirmClear}>
                Yes, clear
              </button>{" "}
              <button type="button" onClick={() => setClearConfirming(false)}>
                Cancel
              </button>
            </span>
          )}
        </form>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          Examples:{" "}
          {EXAMPLE_GOALS.map((example, i) => (
            <span key={example}>
              <button type="button" onClick={() => setGoalDraft(example)} style={{ padding: "1px 8px" }}>
                {example}
              </button>
              {i < EXAMPLE_GOALS.length - 1 ? " " : ""}
            </span>
          ))}
        </p>
        {undoGoal && (
          <p>
            Goal cleared.{" "}
            <button type="button" onClick={undoClear}>
              Undo
            </button>
          </p>
        )}
      </section>
      <p>
        Paste new material on the <Link href="/">Global Home</Link> — it routes concepts
        into your topics automatically.
      </p>
      <p>{status}</p>
      {map && map.tree.length > 0 && (
        <>
          <h2>Mastery overview</h2>
          {(() => {
            const t = tallyMastery(map.tree);
            return (
              <p>
                <span className="badge badge-mastery-weak">weak {t.weak}</span>{" "}
                <span className="badge badge-mastery-learning">learning {t.learning}</span>{" "}
                <span className="badge badge-mastery-strong">strong {t.strong}</span>{" "}
                {t.neverReviewed > 0 && `· ${t.neverReviewed} not yet reviewed`}
              </p>
            );
          })()}
        </>
      )}
      <h2>Materials</h2>
      <ul>
        {materials.map((m) => (
          <li key={m.id}>
            {m.concept_names.length > 0 ? (
              m.concept_names.map((name) => (
                <span key={name} className="tag" style={{ marginRight: 4 }}>
                  {name}
                </span>
              ))
            ) : (
              <span style={{ color: "var(--color-text-muted)" }}>no concepts extracted yet</span>
            )}{" "}
            — {new Date(m.created_at).toLocaleDateString()}
          </li>
        ))}
      </ul>
      {map && map.tree.length > 0 && (
        <>
          <h2>Concept Tree</h2>
          <ConceptMap map={map} topicName={topicName} />
        </>
      )}
      {concepts.length > 0 && (
        <>
          <h2>
            Concepts — <Link href={`/topics/${id}/all-concepts`}>All Concepts</Link>
          </h2>
          <label style={{ fontSize: 14 }}>
            <input
              type="checkbox"
              checked={showRelevance}
              onChange={(e) => setShowRelevance(e.target.checked)}
            />{" "}
            Show relevance column
          </label>
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
                <th style={{ padding: 4 }}>Concept</th>
                {showRelevance && <th style={{ padding: 4 }}>Relevance (your override wins)</th>}
                <th style={{ padding: 4 }}>Review</th>
              </tr>
            </thead>
            <tbody>
              {concepts.map((c) => (
                <tr key={c.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: 4 }}>
                    <Link href={`/concepts/${c.id}`}>{c.name}</Link>
                    {c.confirmed ? "" : " (unconfirmed)"}
                  </td>
                  {showRelevance && (
                    <td style={{ padding: 4 }}>
                      <select
                        value={c.goal_relevance ?? ""}
                        disabled={!goal}
                        onChange={(e) =>
                          overrideRelevance(
                            c.id,
                            e.target.value as "irrelevant" | "supporting" | "core",
                          )
                        }
                      >
                        <option value="" disabled>
                          {goal ? "unscored" : "no Goal"}
                        </option>
                        <option value="irrelevant">irrelevant</option>
                        <option value="supporting">supporting</option>
                        <option value="core">core</option>
                      </select>
                    </td>
                  )}
                  <td style={{ padding: 4 }}>{c.scheduled ? "scheduled" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <h2>Due for review</h2>
      {due.length > 0 ? (
        <>
          <p>{due.length} concept(s) due now:</p>
          <ul>
            {due.map((c) => (
              <li key={c.id}>
                <Link href={`/concepts/${c.id}`}>{c.name}</Link>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p>Nothing due right now — all caught up.</p>
      )}
      <p>
        <Link href={`/topics/${id}/review`}>Start review</Link>
      </p>
      <Link href="/topics">Back to topics</Link>
    </div>
  );
}
