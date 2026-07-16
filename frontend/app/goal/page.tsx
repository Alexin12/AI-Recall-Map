"use client";

import { useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Goal } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export default function GoalPage() {
  const [token, setToken] = useState("");
  const [content, setContent] = useState("");
  const [goal, setGoal] = useState<Goal | null>(null);
  const [status, setStatus] = useState("");

  // Demo auth: sign a throwaway user up, then load their Goal if one exists.
  async function signIn() {
    setStatus("Signing in…");
    const email = `demo_${crypto.randomUUID()}@example.com`;
    const { data, error } = await supabase.auth.signUp({
      email,
      password: "password123",
    });
    if (error || !data.session) {
      setStatus(`Auth failed: ${error?.message ?? "no session"}`);
      return;
    }
    setToken(data.session.access_token);
    const res = await fetch(`${API_URL}/goal`, {
      headers: { Authorization: `Bearer ${data.session.access_token}` },
    });
    if (res.ok) {
      const g: Goal = await res.json();
      setGoal(g);
      setContent(g.content);
    }
    setStatus("Signed in — set your Goal below.");
  }

  async function saveGoal() {
    if (!content.trim()) {
      setStatus("Goal cannot be empty.");
      return;
    }
    setStatus("Saving…");
    const res = await fetch(`${API_URL}/goal`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
    });
    if (!res.ok) {
      setStatus(`Save failed (${res.status})`);
      return;
    }
    const g: Goal = await res.json();
    setGoal(g);
    setStatus("Goal saved.");
  }

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      <h1>Your Goal</h1>
      <p>One learning Goal per user — set it once, edit it any time.</p>
      {!token ? (
        <button onClick={signIn} style={{ padding: "8px 16px" }}>
          Sign in (demo)
        </button>
      ) : (
        <>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={3}
            style={{ width: "100%", padding: 8 }}
            placeholder="e.g. become an AI engineer within a year"
          />
          <button onClick={saveGoal} style={{ padding: "8px 16px", marginTop: 8 }}>
            Save Goal
          </button>
        </>
      )}
      <p>{status}</p>
      {goal && (
        <p>
          Saved: {goal.content} <small>(updated {goal.updated_at})</small>
        </p>
      )}
      <p>
        <Link href="/topics">← Back to topics</Link>
      </p>
    </main>
  );
}
