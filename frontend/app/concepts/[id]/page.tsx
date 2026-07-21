"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { ConceptDetail } from "@/types";

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

/** Concept detail page: everything about one Concept, including review history. */
export default function ConceptPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [concept, setConcept] = useState<ConceptDetail | null>(null);
  const [status, setStatus] = useState("Loading…");
  const [sourceOpen, setSourceOpen] = useState(false);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      const res = await fetch(`${API_URL}/concepts/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setStatus(`Could not load concept (${res.status})`);
        return;
      }
      setConcept(await res.json());
      setStatus("");
    })().catch((e) => setStatus(String(e)));
  }, [id]);

  return (
    <div>
      {status && <p>{status}</p>}
      {concept && (
        <>
          <h1>{concept.keyword}</h1>
          <p>
            Mastery: <span className={`badge badge-mastery-${concept.mastery}`}>{concept.mastery}</span> ·{" "}
            {concept.due ? "Due now" : `Next due ${new Date(concept.next_due_at).toLocaleDateString()}`}{" "}
            · {concept.goal_relevance ?? "unscored"}, confidence{" "}
            {Math.round(concept.confidence * 100)}%
          </p>
          <p>
            <strong>Analogy</strong>
            {concept.ai_supplemented_fields.includes("analogy") && (
              <>
                {" "}
                <span className="badge badge-ai-supplemented">AI-supplemented</span>
              </>
            )}
            <br />
            {concept.analogy}
          </p>
          <p>
            <strong>Technical explanation</strong>
            {concept.ai_supplemented_fields.includes("technical_explanation") && (
              <>
                {" "}
                <span className="badge badge-ai-supplemented">AI-supplemented</span>
              </>
            )}
            <br />
            {concept.technical_explanation}
          </p>
          {concept.code_snippet !== "none" && (
            <>
              <strong>Code</strong>
              <pre className="card" style={{ overflowX: "auto" }}>
                <code>{concept.code_snippet}</code>
              </pre>
            </>
          )}
          {concept.core_claim && (
            <p>
              <strong>Core claim</strong>
              {concept.ai_supplemented_fields.includes("core_claim") && (
                <>
                  {" "}
                  <span className="badge badge-ai-supplemented">AI-supplemented</span>
                </>
              )}
              <br />
              {concept.core_claim}
            </p>
          )}
          <p>
            <button type="button" onClick={() => setSourceOpen((open) => !open)}>
              {sourceOpen ? "Hide source" : "View source"}
            </button>
          </p>
          {sourceOpen && (
            <blockquote style={{ borderLeft: "3px solid var(--color-sand)", paddingLeft: 8, marginInlineStart: 0 }}>
              {concept.source_excerpt}
            </blockquote>
          )}
          <h2>Questions</h2>
          <ul>
            {concept.questions.map((q) => (
              <li key={q.id}>
                <em>{q.kind}</em>: {q.prompt}
              </li>
            ))}
          </ul>
          <h2>Review history</h2>
          {concept.reviews.length === 0 && <p>No reviews yet.</p>}
          <ul>
            {concept.reviews.map((r) => (
              <li key={r.id} style={{ marginBottom: 8 }}>
                <span className={`badge badge-verdict-${r.verdict}`}>{r.verdict}</span>
                {r.verdict_overridden ? ` (AI said ${r.ai_verdict})` : ""} —{" "}
                {new Date(r.created_at).toLocaleString()}
                <br />
                Answer: {r.answer}
                {r.feedback.missing_points.length > 0 && (
                  <>
                    <br />
                    Missing: {r.feedback.missing_points.join("; ")}
                  </>
                )}
              </li>
            ))}
          </ul>
          <Link href={`/topics/${concept.topic_id}`}>Back to topic</Link>
        </>
      )}
    </div>
  );
}
