import { useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphLink, GraphNode, GraphPayload, NodeCategory, RiskLevel } from "../../types/graph";

interface ActorGraphProps {
  graph: GraphPayload;
  selectedCategories: Set<NodeCategory>;
  onActorClick: (actorId: string) => void;
}

interface RenderNode extends GraphNode {
  x?: number;
  y?: number;
}

interface RenderLink extends Omit<GraphLink, "source" | "target"> {
  source: string | RenderNode;
  target: string | RenderNode;
}

interface RenderGraph {
  nodes: RenderNode[];
  links: RenderLink[];
}

const nodeColors: Record<NodeCategory, string> = {
  actor: "#d9480f",
  handle: "#2563eb",
  wallet: "#059669",
};

const riskRingColors: Record<RiskLevel, string> = {
  critical: "#7f1d1d",
  high: "#dc2626",
  medium: "#d97706",
  low: "#16a34a",
};

function getNodeRadius(node: RenderNode) {
  const confidenceBoost = node.confidence ? node.confidence * 5 : 3;
  const categoryBoost = node.category === "actor" ? 7 : node.category === "wallet" ? 5 : 4;

  return categoryBoost + confidenceBoost;
}

function getNodeByEndpoint(endpoint: string | RenderNode) {
  return typeof endpoint === "string" ? undefined : endpoint;
}

function getLinkOpacity(confidence?: number) {
  return Math.max(0.25, confidence ?? 0.5);
}

export function ActorGraph({ graph, selectedCategories, onActorClick }: ActorGraphProps) {
  const filteredGraph = useMemo<RenderGraph>(() => {
    const nodes = graph.nodes.filter((node) => selectedCategories.has(node.category));
    const visibleIds = new Set(nodes.map((node) => node.id));
    const links = graph.links.filter(
      (link) => visibleIds.has(link.source) && visibleIds.has(link.target),
    );

    return { nodes, links };
  }, [graph, selectedCategories]);

  return (
    <div className="graph-stage" aria-label="Interactive actor relationship graph">
      <ForceGraph2D
        graphData={filteredGraph}
        nodeId="id"
        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={(link) => 0.004 + ((link as RenderLink).confidence ?? 0.5) * 0.004}
        linkColor={(link) => `rgba(31, 41, 55, ${getLinkOpacity((link as RenderLink).confidence)})`}
        linkWidth={(link) => 1 + ((link as RenderLink).confidence ?? 0.5) * 2}
        linkCanvasObjectMode={() => "after"}
        linkCanvasObject={(link, ctx, globalScale) => {
          const renderLink = link as RenderLink;
          const source = getNodeByEndpoint(renderLink.source);
          const target = getNodeByEndpoint(renderLink.target);

          if (!source?.x || !source?.y || !target?.x || !target?.y) {
            return;
          }

          const fontSize = 11 / globalScale;
          const x = (source.x + target.x) / 2;
          const y = (source.y + target.y) / 2;

          ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
          ctx.fillStyle = "rgba(17, 24, 39, 0.78)";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(renderLink.relation, x, y);
        }}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const renderNode = node as RenderNode;
          const radius = getNodeRadius(renderNode);
          const fontSize = Math.max(9, 13 / globalScale);
          const x = renderNode.x ?? 0;
          const y = renderNode.y ?? 0;

          if (renderNode.risk) {
            ctx.beginPath();
            ctx.arc(x, y, radius + 4, 0, 2 * Math.PI, false);
            ctx.fillStyle = riskRingColors[renderNode.risk];
            ctx.globalAlpha = 0.2 + (renderNode.confidence ?? 0.5) * 0.3;
            ctx.fill();
            ctx.globalAlpha = 1;
          }

          ctx.beginPath();
          ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
          ctx.fillStyle = nodeColors[renderNode.category];
          ctx.fill();
          ctx.lineWidth = renderNode.category === "actor" ? 2.5 : 1.5;
          ctx.strokeStyle = "#ffffff";
          ctx.stroke();

          ctx.font = `600 ${fontSize}px Inter, system-ui, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = "#111827";
          ctx.fillText(renderNode.name, x, y + radius + 5);
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          const renderNode = node as RenderNode;
          const radius = getNodeRadius(renderNode) + 18;
          const x = renderNode.x ?? 0;
          const y = renderNode.y ?? 0;

          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
        onNodeClick={(node) => {
          const renderNode = node as RenderNode;

          if (renderNode.category === "actor") {
            onActorClick(renderNode.id);
          }
        }}
        cooldownTicks={80}
        d3VelocityDecay={0.28}
        enableNodeDrag
      />
    </div>
  );
}
