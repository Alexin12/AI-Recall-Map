"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Topic } from "@/types";

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

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [name, setName] = useState("");
  const [status, setStatus] = useState("Loading…");

  async function loadTopics() {
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const rows: Topic[] = await res.json();
    setTopics(rows);
    setStatus(`${rows.length} topic(s)`);
  }

  useEffect(() => {
    loadTopics().catch((e) => setStatus(String(e)));
  }, []);

  async function createTopic(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setStatus("Creating…");
    const token = await getToken();
    await fetch(`${API_URL}/topics`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ name: name.trim() }),
    });
    setName("");
    await loadTopics();
  }

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      <h1>Topics</h1>
      <form onSubmit={createTopic}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New topic name"
          style={{ padding: 8, marginRight: 8 }}
        />
        <button type="submit" style={{ padding: "8px 16px" }}>
          Create topic
        </button>
      </form>
      <p>{status}</p>
      <ul>
        {topics.map((t) => (
          <li key={t.id}>
            <Link href={`/topics/${t.id}`}>{t.name}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
