"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import { supabase } from "@/lib/supabaseClient";
import type { Concept, ConceptMap as ConceptMapData, Material } from "@/types";
import ConceptMap from "./ConceptMap";

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
  const [pending, setPending] = useState<Concept[]>([]);
  const [pendingMaterialId, setPendingMaterialId] = useState<string | null>(null);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [map, setMap] = useState<ConceptMapData | null>(null);

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
            setStatus(`Extracting… (${event.stage})`);
          } else if (event.type === "error") {
            setStatus(`Extraction failed: ${event.message} — try pasting again`);
            return;
          } else if (event.type === "result") {
            gotResult = true;
            setStatus(`Extracted ${event.concepts.length} concept(s) — review them below`);
            setPending(event.concepts);
            setPendingMaterialId(materialId);
          }
        }
      }
    } catch {
      setStatus("Extraction failed: connection lost — try pasting again");
      return;
    }
    // A stream that closes without a result event is a failure too (issue #30).
    if (!gotResult) setStatus("Extraction failed — try pasting again");
  }

  /** PATCH one field of a pending Concept and mirror the server's row locally. */
  async function editConcept(conceptId: string, patch: Partial<Concept>) {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/${conceptId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(patch),
    });
    if (!res.ok) {
      setStatus(`Edit failed (${res.status})`);
      return;
    }
    const updated: Concept = await res.json();
    setPending((prev) => prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c)));
  }

  async function deleteConcept(conceptId: string) {
    const token = await getToken();
    const res = await fetch(`${API_URL}/concepts/${conceptId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setStatus(`Delete failed (${res.status})`);
      return;
    }
    setPending((prev) => prev.filter((c) => c.id !== conceptId));
  }

  async function confirmConcepts() {
    if (!pendingMaterialId) return;
    const token = await getToken();
    const res = await fetch(`${API_URL}/materials/${pendingMaterialId}/confirm`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      setStatus(`Confirm failed (${res.status})`);
      return;
    }
    const confirmed: Concept[] = await res.json();
    setPending([]);
    setPendingMaterialId(null);
    setStatus(`Confirmed ${confirmed.length} concept(s)`);
    await loadConcepts();
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
    // Refresh the material list first: extractMaterial owns the status line
    // from here on, so its success/failure message must not be overwritten.
    await loadMaterials();
    await extractMaterial(material.id, token);
    // Show whatever extraction persisted even if the result event was missed.
    await loadConcepts();
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
      {pending.length > 0 && (
        <section style={{ border: "1px solid #ccc", padding: 12, marginBottom: 16 }}>
          <h2>Confirm extracted concepts</h2>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {pending.map((c) => (
              <li key={c.id} style={{ borderBottom: "1px solid #eee", padding: "8px 0" }}>
                <input
                  defaultValue={c.name}
                  onBlur={(e) => {
                    if (e.target.value !== c.name) editConcept(c.id, { name: e.target.value });
                  }}
                  style={{ fontWeight: "bold", width: "100%", marginBottom: 4 }}
                />
                <textarea
                  defaultValue={c.explanation}
                  rows={2}
                  onBlur={(e) => {
                    if (e.target.value !== c.explanation)
                      editConcept(c.id, { explanation: e.target.value });
                  }}
                  style={{ width: "100%", marginBottom: 4 }}
                />
                <small>
                  “{c.source_snippet}” — {c.goal_relevance}, confidence{" "}
                  {Math.round(c.confidence * 100)}%
                </small>
                <div>
                  <label>
                    <input
                      type="checkbox"
                      checked={c.scheduled}
                      onChange={(e) => editConcept(c.id, { scheduled: e.target.checked })}
                    />{" "}
                    Schedule for review
                  </label>{" "}
                  <button type="button" onClick={() => deleteConcept(c.id)}>
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <button type="button" onClick={confirmConcepts} style={{ padding: "8px 16px" }}>
            Confirm concepts
          </button>
        </section>
      )}
      <ul>
        {materials.map((m) => (
          <li key={m.id}>
            {m.content.slice(0, 80)}
            {m.content.length > 80 ? "…" : ""} —{" "}
            {new Date(m.created_at).toLocaleDateString()}
          </li>
        ))}
      </ul>
      {map && map.nodes.length > 0 && (
        <>
          <h2>Concept Map</h2>
          <ConceptMap map={map} />
        </>
      )}
      {concepts.length > 0 && (
        <>
          <h2>Concepts</h2>
          <ul>
            {concepts.map((c) => (
              <li key={c.id}>
                <Link href={`/concepts/${c.id}`}>{c.name}</Link> — {c.goal_relevance}
                {c.confirmed ? "" : " (unconfirmed)"}
              </li>
            ))}
          </ul>
        </>
      )}
      <p>
        <Link href={`/topics/${id}/review`}>Start review</Link>
      </p>
      <Link href="/topics">Back to topics</Link>
    </main>
  );
}
