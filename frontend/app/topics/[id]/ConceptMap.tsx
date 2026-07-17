"use client";

import { useRouter } from "next/navigation";
import { ReactFlow, Background, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ConceptMap as ConceptMapData } from "@/types";

const RELEVANCE_COLORS: Record<string, string> = {
  core: "#c8e6c9",
  supporting: "#fff9c4",
  irrelevant: "#eeeeee",
};

/** Read-only Concept Map: auto grid layout, no drag/edit; click opens the detail page. */
export default function ConceptMap({ map }: { map: ConceptMapData }) {
  const router = useRouter();
  const nodes: Node[] = map.nodes.map((n, i) => ({
    id: n.id,
    position: { x: (i % 3) * 220, y: Math.floor(i / 3) * 100 },
    data: { label: n.name },
    style: { background: RELEVANCE_COLORS[n.goal_relevance ?? ""] ?? "#fff" },
  }));
  const edges: Edge[] = map.relationships.map((r) => ({
    id: r.id,
    source: r.from_concept_id,
    target: r.to_concept_id,
    label: r.kind,
  }));

  return (
    <div style={{ height: 320, border: "1px solid #ccc" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        onNodeClick={(_, node) => router.push(`/concepts/${node.id}`)}
      >
        <Background />
      </ReactFlow>
    </div>
  );
}
