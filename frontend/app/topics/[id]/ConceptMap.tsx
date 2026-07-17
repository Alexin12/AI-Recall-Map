"use client";

import { useState } from "react";
import Link from "next/link";

import type { ConceptMap as ConceptMapData, TreeNode } from "@/types";

const RELEVANCE_COLORS: Record<string, string> = {
  core: "#c8e6c9",
  supporting: "#fff9c4",
  irrelevant: "#eeeeee",
};

/** One expandable node: click the arrow to expand, the label to open the detail page. */
function TreeBranch({ node }: { node: TreeNode }) {
  const [open, setOpen] = useState(true);
  return (
    <li style={{ listStyle: "none", margin: "4px 0" }}>
      <span
        onClick={() => setOpen(!open)}
        style={{
          cursor: node.children.length ? "pointer" : "default",
          display: "inline-block",
          width: 16,
        }}
      >
        {node.children.length > 0 ? (open ? "▾" : "▸") : "·"}
      </span>
      <Link
        href={`/concepts/${node.id}`}
        style={{
          background: RELEVANCE_COLORS[node.goal_relevance ?? ""] ?? "#fff",
          padding: "2px 6px",
          borderRadius: 4,
        }}
      >
        {node.display_label}
      </Link>
      {open && node.children.length > 0 && (
        <ul style={{ paddingLeft: 20, margin: 0 }}>
          {node.children.map((c) => (
            <TreeBranch key={c.id} node={c} />
          ))}
        </ul>
      )}
    </li>
  );
}

/** The Topic's Concept Map as an expandable hierarchy tree (ADR-0007). */
export default function ConceptMap({ map }: { map: ConceptMapData }) {
  return (
    <ul style={{ padding: 0, border: "1px solid #ccc", borderRadius: 4, margin: 0, paddingBlock: 8, paddingInline: 8 }}>
      {map.tree.map((n) => (
        <TreeBranch key={n.id} node={n} />
      ))}
    </ul>
  );
}
