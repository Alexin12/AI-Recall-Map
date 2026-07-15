"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Concept, Review } from "@/types";

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

/** Review Page: answer the flashcard Question of each due Concept, one at a time. */
export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [due, setDue] = useState<Concept[]>([]);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<Review | null>(null);
  const [status, setStatus] = useState("Loading…");
  const [mode, setMode] = useState<"flashcard" | "written">("flashcard");

  async function loadDue() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics/${id}/due`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setStatus(`Could not load due list (${res.status})`);
      return;
    }
    const rows: Concept[] = await res.json();
    setDue(rows);
    setStatus(rows.length ? `${rows.length} concept(s) due` : "Nothing due — all caught up!");
  }

  useEffect(() => {
    loadDue().catch((e) => setStatus(String(e)));
  }, []);

  const current = due[0];
  const question = current?.questions.find((q) => q.kind === mode);

  async function submitAnswer(e: React.FormEvent) {
    e.preventDefault();
    if (!question || !answer.trim()) return;
    setStatus("Grading…");
    const token = await getToken();
    const res = await fetch(`${API_URL}/questions/${question.id}/answer`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ answer }),
    });
    if (!res.ok) {
      setStatus(`Grading failed (${res.status})`);
      return;
    }
    const review: Review = await res.json();
    setResult(review);
    setStatus(`Verdict: ${review.verdict} — next due ${new Date(review.next_due_at).toLocaleDateString()}`);
  }

  /** One click replaces the AI verdict; scheduling follows the final verdict. */
  async function overrideVerdict(verdict: Review["verdict"]) {
    if (!result) return;
    const token = await getToken();
    const res = await fetch(`${API_URL}/reviews/${result.id}/override`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ verdict }),
    });
    if (!res.ok) {
      setStatus(`Override failed (${res.status})`);
      return;
    }
    const updated: Review = await res.json();
    setResult(updated);
    setStatus(
      `Verdict overridden to ${updated.verdict} — next due ${new Date(updated.next_due_at).toLocaleDateString()}`,
    );
  }

  async function nextConcept() {
    setResult(null);
    setAnswer("");
    await loadDue();
  }

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      <h1>Review</h1>
      <p>{status}</p>
      {current && !result && (
        <p>
          <label>
            <input
              type="radio"
              checked={mode === "flashcard"}
              onChange={() => setMode("flashcard")}
            />{" "}
            Flashcard
          </label>{" "}
          <label>
            <input type="radio" checked={mode === "written"} onChange={() => setMode("written")} />{" "}
            Written explanation
          </label>
        </p>
      )}
      {current && question && !result && (
        <form onSubmit={submitAnswer}>
          <h2>{current.name}</h2>
          <p>{question.prompt}</p>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer"
            rows={4}
            style={{ width: "100%", padding: 8 }}
          />
          <button type="submit" style={{ padding: "8px 16px", marginTop: 8 }}>
            Submit answer
          </button>
        </form>
      )}
      {result && (
        <section style={{ border: "1px solid #ccc", padding: 12 }}>
          <h2>
            Verdict: {result.verdict}
            {result.verdict_overridden ? ` (AI said ${result.ai_verdict})` : ""}
          </h2>
          <p>Next due: {new Date(result.next_due_at).toLocaleString()}</p>
          <p>
            Disagree?{" "}
            {(["fail", "partial", "pass", "strong"] as const)
              .filter((v) => v !== result.verdict)
              .map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => overrideVerdict(v)}
                  style={{ marginRight: 4 }}
                >
                  {v}
                </button>
              ))}
          </p>
          {result.feedback.correct_points.length > 0 && (
            <>
              <h3>Correct</h3>
              <ul>{result.feedback.correct_points.map((p) => <li key={p}>{p}</li>)}</ul>
            </>
          )}
          {result.feedback.missing_points.length > 0 && (
            <>
              <h3>Missing</h3>
              <ul>{result.feedback.missing_points.map((p) => <li key={p}>{p}</li>)}</ul>
            </>
          )}
          {result.feedback.misconceptions.length > 0 && (
            <>
              <h3>Watch out</h3>
              <ul>{result.feedback.misconceptions.map((p) => <li key={p}>{p}</li>)}</ul>
            </>
          )}
          <button type="button" onClick={nextConcept} style={{ padding: "8px 16px" }}>
            Next
          </button>
        </section>
      )}
      <p>
        <Link href={`/topics/${id}`}>Back to topic</Link>
      </p>
    </main>
  );
}
