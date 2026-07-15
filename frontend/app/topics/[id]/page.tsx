"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Material } from "@/types";

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

/** Topic Page: paste Materials now; mastery and the Concept Map arrive in later slices. */
export default function TopicPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("Loading…");

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
  }, []);

  /** Call the extraction endpoint and render each streamed NDJSON progress event. */
  async function extractMaterial(materialId: string, token: string) {
    const res = await fetch(`${API_URL}/materials/${materialId}/extract`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok || !res.body) {
      setStatus(`Extraction failed (${res.status})`);
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
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
          setStatus(`Extracting… (${event.stage})`);
        } else if (event.type === "result") {
          setStatus(`Extracted ${event.concepts.length} concept(s)`);
        }
      }
    }
  }

  async function pasteMaterial(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setStatus("Pasting…");
    const token = await getToken();
    const res = await fetch(`${API_URL}/topics/${id}/materials`, {
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
    setContent("");
    const material = await res.json();
    await extractMaterial(material.id, token);
    await loadMaterials();
  }

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "40px auto", padding: 16 }}>
      <h1>Topic</h1>
      <p>Topic id: {id}</p>
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
      <ul>
        {materials.map((m) => (
          <li key={m.id}>
            {m.content.slice(0, 80)}
            {m.content.length > 80 ? "…" : ""} —{" "}
            {new Date(m.created_at).toLocaleDateString()}
          </li>
        ))}
      </ul>
      <Link href="/topics">Back to topics</Link>
    </main>
  );
}
