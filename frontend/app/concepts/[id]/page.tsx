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
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      {status && <p>{status}</p>}
      {concept && (
        <>
          <h1>{concept.name}</h1>
          <p>
            Mastery: <strong>{concept.mastery}</strong> ·{" "}
            {concept.due ? "Due now" : `Next due ${new Date(concept.next_due_at).toLocaleDateString()}`}{" "}
            · {concept.goal_relevance}, confidence {Math.round(concept.confidence * 100)}%
          </p>
          <p>{concept.explanation}</p>
          <blockquote style={{ borderLeft: "3px solid #ccc", paddingLeft: 8 }}>
            {concept.source_snippet}
          </blockquote>
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
                <strong>{r.verdict}</strong>
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
    </main>
  );
}
