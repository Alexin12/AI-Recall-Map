"use client";

import { useCallback, useEffect, useMemo, useState, type KeyboardEvent, type MouseEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  Handle,
  Position,
  useReactFlow,
  type Node,
  type Edge,
  type NodeProps,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ConceptMap as ConceptMapData, TreeNode } from "@/types";

const RING_SPACING = 150; // px between successive rings
const ROOT_ID = "__topic_root__";

type FlatNode = {
  id: string;
  label: string;
  depth: number; // 1 = top-level Concept ring, 2+ = sub-Concept
  mastery: TreeNode["mastery"];
  children: FlatNode[];
};

function toFlat(node: TreeNode, depth: number): FlatNode {
  return {
    id: node.id,
    label: node.display_label,
    depth,
    mastery: node.mastery,
    children: node.children.map((c) => toFlat(c, depth + 1)),
  };
}

/** Classic radial tree layout: each node's children share an angular sector
 * carved out of their own sector, so branches never overlap at any depth. */
function layoutRadial(roots: FlatNode[], expanded: Set<string>) {
  const positions = new Map<string, { x: number; y: number }>();
  positions.set(ROOT_ID, { x: 0, y: 0 });

  function place(nodes: FlatNode[], depth: number, angleStart: number, angleSpan: number) {
    if (nodes.length === 0) return;
    const slice = angleSpan / nodes.length;
    nodes.forEach((node, i) => {
      const angle = angleStart + slice * (i + 0.5) - Math.PI / 2;
      const radius = depth * RING_SPACING;
      positions.set(node.id, { x: radius * Math.cos(angle), y: radius * Math.sin(angle) });
      if (expanded.has(node.id) && node.children.length > 0) {
        place(node.children, depth + 1, angleStart + slice * i, slice);
      }
    });
  }

  place(roots, 1, 0, Math.PI * 2);
  return positions;
}

/** The first ring (top-level Concepts) is always visible; deeper rings show
 * only once their parent is expanded (map opens with just the first level). */
function collectVisible(nodes: FlatNode[], expanded: Set<string>, acc: FlatNode[] = []) {
  for (const node of nodes) {
    acc.push(node);
    if (expanded.has(node.id) && node.children.length > 0) {
      collectVisible(node.children, expanded, acc);
    }
  }
  return acc;
}

type ConceptNodeData = {
  label: string;
  depth: number; // 0 = central Topic node
  mastery: TreeNode["mastery"] | null;
  hasChildren: boolean;
  expanded: boolean;
  conceptId: string | null;
  onToggle: () => void;
};

/** One node of the radial tree: left-click expands/collapses, right-click (or
 * the keyboard-reachable open button) navigates to the Concept's detail page. */
function ConceptNode({ data }: NodeProps<Node<ConceptNodeData>>) {
  const router = useRouter();
  const isRoot = data.depth === 0;
  const masteryClass = data.depth >= 2 && data.mastery ? `badge-mastery-${data.mastery}` : null;

  const openDetail = useCallback(
    (event: MouseEvent | KeyboardEvent) => {
      event.stopPropagation();
      event.preventDefault();
      if (data.conceptId) router.push(`/concepts/${data.conceptId}`);
    },
    [data.conceptId, router],
  );

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (data.hasChildren) data.onToggle();
    }
  }

  return (
    <div
      role={isRoot ? undefined : "button"}
      tabIndex={isRoot ? -1 : 0}
      aria-expanded={data.hasChildren ? data.expanded : undefined}
      aria-label={
        isRoot
          ? data.label
          : `${data.label}${data.hasChildren ? (data.expanded ? ", expanded" : ", collapsed") : ""}`
      }
      onClick={() => !isRoot && data.hasChildren && data.onToggle()}
      onContextMenu={(e) => !isRoot && openDetail(e)}
      onKeyDown={isRoot ? undefined : handleKeyDown}
      className={masteryClass ? `badge ${masteryClass}` : undefined}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        whiteSpace: "nowrap",
        padding: masteryClass ? undefined : "5px 10px",
        borderRadius: isRoot ? 999 : masteryClass ? undefined : 8,
        border: masteryClass
          ? undefined
          : `2px solid ${isRoot ? "var(--color-deep-olive)" : "var(--color-olive)"}`,
        background: masteryClass ? undefined : isRoot ? "var(--color-deep-olive)" : "var(--color-sand)",
        color: masteryClass || isRoot ? "#fff" : "var(--color-text)",
        fontWeight: isRoot ? 700 : 400,
        fontSize: isRoot ? "var(--text-lg)" : "var(--text-sm)",
        cursor: !isRoot && data.hasChildren ? "pointer" : "default",
      }}
    >
      {!isRoot && <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />}
      <span>{data.label}</span>
      {data.hasChildren && <span aria-hidden>{data.expanded ? "▾" : "▸"}</span>}
      {data.conceptId && (
        <button
          type="button"
          onClick={openDetail}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && openDetail(e)}
          aria-label={`Open ${data.label} detail page`}
          title="Open detail (or right-click the node)"
          style={{
            border: "none",
            background: "transparent",
            color: "inherit",
            cursor: "pointer",
            padding: 0,
            fontSize: "0.85em",
            lineHeight: 1,
          }}
        >
          &#8599;
        </button>
      )}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes: NodeTypes = { concept: ConceptNode };

/** Re-fits the view whenever the visible node set changes (expand/collapse). */
function ConceptMapCanvas({
  nodes,
  edges,
  isFullscreen,
}: {
  nodes: Node[];
  edges: Edge[];
  isFullscreen: boolean;
}) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    fitView({ padding: 0.3, duration: 200 });
  }, [nodes, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      nodeOrigin={[0.5, 0.5]}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      nodesDraggable={false}
      nodesFocusable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      disableKeyboardA11y
      panOnDrag={isFullscreen}
      zoomOnScroll={isFullscreen}
      zoomOnPinch={isFullscreen}
      zoomOnDoubleClick={false}
      preventScrolling={isFullscreen}
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      {isFullscreen && <Controls showInteractive={false} />}
    </ReactFlow>
  );
}

/** The Topic's Concept Tree as a radial mind map (ADR-0007 data unchanged —
 * one primary parent per Concept, read-only, no map editing). */
export default function ConceptMap({ map, topicName }: { map: ConceptMapData; topicName: string }) {
  const roots = useMemo(() => map.tree.map((n) => toFlat(n, 1)), [map]);
  // Only the first level (top-level ring) opens expanded; deeper rings start collapsed.
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!isFullscreen) return;
    function onKeyDown(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape") setIsFullscreen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  const { nodes, edges } = useMemo(() => {
    const positions = layoutRadial(roots, expanded);
    const visible = collectVisible(roots, expanded);
    const visibleIds = new Set(visible.map((n) => n.id));

    const rootNode: Node<ConceptNodeData> = {
      id: ROOT_ID,
      type: "concept",
      position: positions.get(ROOT_ID)!,
      draggable: false,
      selectable: false,
      data: {
        label: topicName || "Topic",
        depth: 0,
        mastery: null,
        hasChildren: false,
        expanded: false,
        conceptId: null,
        onToggle: () => {},
      },
    };
    const conceptNodes: Node<ConceptNodeData>[] = visible.map((n) => ({
      id: n.id,
      type: "concept",
      position: positions.get(n.id)!,
      draggable: false,
      selectable: false,
      data: {
        label: n.label,
        depth: n.depth,
        mastery: n.mastery,
        hasChildren: n.children.length > 0,
        expanded: expanded.has(n.id),
        conceptId: n.id,
        onToggle: () => toggle(n.id),
      },
    }));

    const flowEdges: Edge[] = [];
    function addEdges(list: FlatNode[], parentId: string) {
      for (const node of list) {
        flowEdges.push({ id: `${parentId}->${node.id}`, source: parentId, target: node.id, type: "default" });
        if (visibleIds.has(node.id) && expanded.has(node.id)) addEdges(node.children, node.id);
      }
    }
    addEdges(roots, ROOT_ID);

    return { nodes: [rootNode, ...conceptNodes], edges: flowEdges };
  }, [roots, expanded, topicName, toggle]);

  return (
    <div>
      <div
        style={
          isFullscreen
            ? { position: "fixed", inset: 0, zIndex: 1000, background: "var(--color-bg)" }
            : {
                position: "relative",
                height: 420,
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius)",
                background: "var(--color-card)",
                overflow: "hidden",
              }
        }
      >
        <button
          type="button"
          onClick={() => setIsFullscreen((f) => !f)}
          style={{ position: "absolute", top: 8, right: 8, zIndex: 10 }}
        >
          {isFullscreen ? "Exit fullscreen" : "Fullscreen"}
        </button>
        <ReactFlowProvider>
          <ConceptMapCanvas nodes={nodes} edges={edges} isFullscreen={isFullscreen} />
        </ReactFlowProvider>
      </div>
      <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>
        Tab to a Concept and press Enter to expand or collapse it; right-click a Concept, or Tab to
        its &#8599; button and press Enter, to open its detail page.
      </p>
    </div>
  );
}
