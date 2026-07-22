"use client";

import { Fragment, use, useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { AllConceptsRow, Topic } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

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

/** All Concepts (issue #77): one purpose-built, urgency-ordered listing with inline edits. */
export default function AllConceptsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [rows, setRows] = useState<AllConceptsRow[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [status, setStatus] = useState("Loading…");
  const [expanded, setExpanded] = useState<string | null>(null);

  async function load() {
    const token = await getToken();
    const [rowsRes, topicsRes] = await Promise.all([
      fetch(`${API_URL}/topics/${id}/all-concepts`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      fetch(`${API_URL}/topics`, { headers: { Authorization: `Bearer ${token}` } }),
    ]);
    if (!rowsRes.ok) {
      setStatus(`Could not load Concepts (${rowsRes.status})`);
      return;
    }
    setRows(await rowsRes.json());
    if (topicsRes.ok) setTopics(await topicsRes.json());
    setStatus("");
  }

  useEffect(() => {
    load().catch((e) => setStatus(String(e)));
  }, [id]);

  /** Edit name, relevance, or Topic — the same PATCH /concepts/{id} the Inbox uses to move Concepts. */
  async function editConcept(conceptId: string, body: Record<string, unknown>) {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/${conceptId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      setStatus(`Edit failed (${res.status})`);
      return;
    }
    await load();
  }

  return (
    <div>
      <h1>All Concepts</h1>
      <p>
        <Link href={`/topics/${id}`}>Back to Topic</Link>
      </p>
      <p>{status}</p>
      {rows.length === 0 && !status && <p>No Concepts yet.</p>}
      {rows.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ padding: 4 }}>Name</th>
              <th style={{ padding: 4 }}>Relevance</th>
              <th style={{ padding: 4 }}>Topic</th>
              <th style={{ padding: 4 }}>Last reviewed</th>
              <th style={{ padding: 4 }}>Next due</th>
              <th style={{ padding: 4 }} />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Fragment key={row.id}>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td style={{ padding: 4 }}>
                    <input
                      defaultValue={row.name}
                      onBlur={(e) => {
                        if (e.target.value.trim() && e.target.value.trim() !== row.name) {
                          editConcept(row.id, { name: e.target.value.trim() });
                        }
                      }}
                      // Enter commits the rename (blur runs the save above); without this a
                      // text field only saves on focus loss, so Enter-then-reload lost the edit.
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.currentTarget.blur();
                      }}
                      style={{ width: "100%" }}
                    />
                  </td>
                  <td style={{ padding: 4 }}>
                    <select
                      value={row.goal_relevance ?? ""}
                      onChange={(e) => editConcept(row.id, { goal_relevance: e.target.value })}
                    >
                      <option value="" disabled>
                        unscored
                      </option>
                      <option value="irrelevant">irrelevant</option>
                      <option value="supporting">supporting</option>
                      <option value="core">core</option>
                    </select>
                  </td>
                  <td style={{ padding: 4 }}>
                    <select
                      value={row.topic_id}
                      onChange={(e) => editConcept(row.id, { topic_id: e.target.value })}
                    >
                      {topics.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td style={{ padding: 4 }}>
                    {row.last_verdict ? (
                      <>
                        <span className={`badge badge-verdict-${row.last_verdict}`}>
                          {row.last_verdict}
                        </span>{" "}
                        {row.last_reviewed_at && new Date(row.last_reviewed_at).toLocaleDateString()}
                      </>
                    ) : (
                      "never"
                    )}
                  </td>
                  <td style={{ padding: 4 }}>
                    {row.next_due_date ? new Date(row.next_due_date).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: 4 }}>
                    {row.written_question && (
                      <button
                        type="button"
                        onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                      >
                        {expanded === row.id ? "Hide" : "Q&A"}
                      </button>
                    )}
                  </td>
                </tr>
                {expanded === row.id && row.written_question && (
                  <tr>
                    <td colSpan={6} style={{ padding: "4px 4px 12px" }}>
                      <strong>Q:</strong> {row.written_question}
                      <br />
                      <strong>A:</strong> {row.written_answer ?? "not answered yet"}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
