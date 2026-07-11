"use client";

import { useMemo } from "react";
import {
  Background,
  BackgroundVariant,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Flame } from "lucide-react";
import type { GraphResponse, NodeFlag, NodeType } from "@/lib/types";
import { cn } from "@/lib/utils";

const KIND_LABEL: Record<NodeType, string> = {
  gstin: "GSTIN",
  pan: "PAN",
  company: "Company",
  din: "Director · DIN",
  address: "Registered address",
};

const FLAG_LABEL: Record<Exclude<NodeFlag, null>, string> = {
  struck_off: "STRUCK OFF",
  wilful_defaulter: "WILFUL DEFAULTER",
  director_of_struck_off: "DIR. OF STRUCK-OFF",
  non_genuine: "NON-GENUINE",
};

type EntityNodeData = {
  label: string;
  kind: NodeType;
  flag: NodeFlag;
};

function EntityNode({ data }: NodeProps<Node<EntityNodeData>>) {
  const flagged = data.flag !== null;
  return (
    <div className={cn("rf-node", flagged && "rf-node-flagged")}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <span className="rf-kind">{KIND_LABEL[data.kind]}</span>
      <span className="tnum block text-[11px] leading-snug">{data.label}</span>
      {flagged && (
        <span className="mt-1 inline-block rounded-sm border border-oxide/50 px-1 py-px font-mono text-[8.5px] font-semibold tracking-[0.1em] text-oxide">
          {FLAG_LABEL[data.flag as Exclude<NodeFlag, null>]}
        </span>
      )}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

/** Deterministic layered layout: identifiers → entities → directors, address below. */
const COLUMN_X: Record<NodeType, number> = {
  gstin: 0,
  pan: 300,
  company: 600,
  din: 910,
  address: 560,
};

function layout(graph: GraphResponse): { nodes: Node<EntityNodeData>[]; edges: Edge[] } {
  const rowsSeen: Partial<Record<NodeType, number>> = {};
  let maxY = 0;
  const placed: Node<EntityNodeData>[] = [];
  const addressNodes: GraphResponse["nodes"] = [];

  for (const n of graph.nodes) {
    if (n.type === "address") {
      addressNodes.push(n);
      continue;
    }
    const row = rowsSeen[n.type] ?? 0;
    rowsSeen[n.type] = row + 1;
    const y = 30 + row * 165;
    maxY = Math.max(maxY, y);
    placed.push({
      id: n.id,
      type: "entity",
      position: { x: COLUMN_X[n.type], y },
      data: { label: n.label, kind: n.type, flag: n.flag },
    });
  }
  addressNodes.forEach((n, i) => {
    placed.push({
      id: n.id,
      type: "entity",
      position: { x: COLUMN_X.address + i * 260, y: maxY + 170 },
      data: { label: n.label, kind: n.type, flag: n.flag },
    });
  });

  const flaggedIds = new Set(
    graph.nodes.filter((n) => n.flag !== null).map((n) => n.id)
  );
  const edges: Edge[] = graph.edges.map((e, i) => {
    const hot = flaggedIds.has(e.source) || flaggedIds.has(e.target);
    return {
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.relation,
      animated: hot,
      style: {
        stroke: hot ? "var(--oxide)" : "var(--ink-3)",
        strokeWidth: hot ? 1.6 : 1.1,
      },
      labelStyle: {
        fontFamily: "var(--font-plex-mono), monospace",
        fontSize: 9,
        fill: hot ? "var(--oxide)" : "var(--ink-2)",
      },
      labelBgStyle: { fill: "var(--paper)", fillOpacity: 0.9 },
    };
  });

  return { nodes: placed, edges };
}

export function EntityGraph({ graph }: { graph: GraphResponse }) {
  const { nodes, edges } = useMemo(() => layout(graph), [graph]);

  return (
    <div>
      {graph.phoenix_flag && (
        <div className="mb-3 flex items-start gap-2.5 rounded-md border border-oxide/40 bg-oxide/5 px-3 py-2.5">
          <Flame className="mt-0.5 size-4 shrink-0 text-oxide" aria-hidden />
          <div>
            <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-oxide">
              Phoenix pattern detected
            </div>
            <p className="mt-1 text-[12.5px] leading-snug text-ink-2">
              {graph.narrative}
            </p>
          </div>
        </div>
      )}
      <div className="h-[380px] overflow-hidden rounded-md border border-rule bg-paper">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          nodesConnectable={false}
          elementsSelectable={false}
          zoomOnScroll={false}
          preventScrolling={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={22}
            size={1}
            color="var(--rule)"
          />
        </ReactFlow>
      </div>
      {!graph.phoenix_flag && (
        <p className="mt-2.5 text-[12.5px] leading-snug text-ink-2">
          {graph.narrative}
        </p>
      )}
    </div>
  );
}
