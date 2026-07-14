"use client";

import { useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
// Created a supabase client, and it include anno key 
// Use anno key to interact with Gotrue --> get JWT
import type { Ping } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export default function Home() {
  const [pings, setPings] = useState<Ping[]>([]);
  const [status, setStatus] = useState("");

  async function run() {
    // Demo auth: sign a throwaway user up so the tracer bullet is self-contained.
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
    const token = data.session.access_token;

    // The frontend only carries the token; ownership/RLS live in the backend.
    setStatus("Calling backend…");
    const auth = { Authorization: `Bearer ${token}` };
    await fetch(`${API_URL}/pings`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify({ message: `hello at ${new Date().toISOString()}` }),
    });
    const res = await fetch(`${API_URL}/pings`, { headers: auth });
    const rows: Ping[] = await res.json();
    setPings(rows);
    setStatus(`OK — ${rows.length} ping(s) scoped to this user`);
  }

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      <h1>AI Recall Map — walking skeleton</h1>
      <p>One click: sign up → POST a ping → GET your own pings (RLS-scoped) from the backend.</p>
      <button onClick={run} style={{ padding: "8px 16px" }}>
        Run tracer bullet
      </button>
      <p>{status}</p>
      <p>
        <Link href="/topics">Go to topics</Link>
      </p>
      <ul>
        {pings.map((p) => (
          <li key={p.id}>
            {p.message} <small>({p.created_at})</small>
          </li>
        ))}
      </ul>
    </main>
  );
}
