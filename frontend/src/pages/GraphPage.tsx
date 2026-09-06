import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import ForceGraph2D from "react-force-graph-2d";

import { getActorGraph } from "../api/client";

import type {
  GraphLink,
  GraphNode,
} from "../api/client";

interface GraphPageProps {
  actorId: string;
  onBack: () => void;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface GraphNodeWithPosition extends GraphNode {
  x?: number;
  y?: number;
}

const ENTITY_TYPES = [
  "actor",
  "handle",
  "wallet",
  "marketplace",
  "infrastructure",
  "observation",
];

export default function GraphPage({
  actorId,
  onBack,
}: GraphPageProps) {
  const [graph, setGraph] = useState<GraphData>({
    nodes: [],
    links: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedNode, setSelectedNode] =
    useState<GraphNode | null>(null);

  const graphRef = useRef<any>(null);

  useEffect(() => {
    setLoading(true);
    setError("");
    setSelectedNode(null);

    getActorGraph(actorId)
      .then((data) => {
        const safeNodes = (data.nodes || []).map(
  (node) => ({
    ...node,

    id: String(
      node.id ?? "",
    ),

    label: String(
      node.label ??
        node.category ??
        node.id ??
        "Unknown entity",
    ),

    type: String(
      node.type ??
        node.category ??
        node.label ??
        "unknown",
    ),
  }),
);

        const safeLinks = (data.links || []).map(
  (link) => ({
    ...link,

    source: String(
      link.source,
    ),

    target: String(
      link.target,
    ),

    type: String(
      link.type ??
        link.relation ??
        "RELATED_TO",
    ),
  }),
);

        setGraph({
          nodes: safeNodes,
          links: safeLinks,
        });
      })
      .catch((err) => {
        console.error(
          "Failed to load graph:",
          err,
        );

        setError(
          "Unable to load graph data.",
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, [actorId]);

  const graphData = useMemo(
    () => ({
      nodes: graph.nodes.map(
        (node) => ({
          ...node,
        }),
      ),

      links: graph.links.map(
        (link) => ({
          ...link,
        }),
      ),
    }),
    [graph],
  );

  function getNodeType(
    node: GraphNode,
  ): string {
    const explicitType =
      String(
        node.type ?? "",
      )
        .trim()
        .toLowerCase();

    if (
      ENTITY_TYPES.includes(
        explicitType,
      )
    ) {
      return explicitType;
    }

    const labelType =
      String(
        node.label ?? "",
      )
        .trim()
        .toLowerCase();

    if (
      ENTITY_TYPES.includes(
        labelType,
      )
    ) {
      return labelType;
    }

    return "unknown";
  }

  function getNodeColor(
    node: GraphNode,
  ) {
    switch (getNodeType(node)) {
      case "actor":
        return "#ff4d6d";

      case "handle":
        return "#4dabf7";

      case "wallet":
        return "#ffd43b";

      case "marketplace":
        return "#69db7c";

      case "infrastructure":
        return "#da77f2";

      case "observation":
        return "#ffa94d";

      default:
        return "#adb5bd";
    }
  }

  function getNodeSize(
    node: GraphNode,
  ) {
    switch (getNodeType(node)) {
      case "actor":
        return 18;

      case "wallet":
        return 11;

      case "handle":
        return 9;

      case "marketplace":
        return 10;

      case "infrastructure":
        return 10;

      case "observation":
        return 8;

      default:
        return 8;
    }
  }

  function getNodeDisplayLabel(
    node: GraphNode,
  ): string {
    const label = String(
  node.name ??
    node.label ??
    node.id ??
    "",
);

    const labelIsType =
      ENTITY_TYPES.includes(
        label
          .trim()
          .toLowerCase(),
      );

    if (labelIsType) {
      return String(
        node.id ?? label,
      );
    }

    return (
      label ||
      String(node.id)
    );
  }

  function getShortLabel(
    node: GraphNode,
  ): string {
    const label =
      getNodeDisplayLabel(
        node,
      );

    if (
      getNodeType(node) ===
        "wallet" &&
      label.length > 18
    ) {
      return `${label.slice(
        0,
        8,
      )}...${label.slice(-6)}`;
    }

    return label;
  }

  function getEndpointId(
    endpoint: unknown,
  ): string {
    if (
      typeof endpoint ===
      "string"
    ) {
      return endpoint;
    }

    if (
      endpoint &&
      typeof endpoint ===
        "object" &&
      "id" in endpoint
    ) {
      return String(
        (
          endpoint as {
            id: unknown;
          }
        ).id,
      );
    }

    return String(endpoint);
  }

  const connectedNodeIds =
    useMemo(() => {
      if (!selectedNode) {
        return new Set<string>();
      }

      const ids =
        new Set<string>();

      ids.add(
        String(
          selectedNode.id,
        ),
      );

      graph.links.forEach(
        (link) => {
          const source =
            getEndpointId(
              link.source,
            );

          const target =
            getEndpointId(
              link.target,
            );

          if (
            source ===
            selectedNode.id
          ) {
            ids.add(target);
          }

          if (
            target ===
            selectedNode.id
          ) {
            ids.add(source);
          }
        },
      );

      return ids;
    }, [
      selectedNode,
      graph.links,
    ]);

  const selectedRelationships =
    useMemo(() => {
      if (!selectedNode) {
        return [];
      }

      return graph.links.filter(
        (link) => {
          const source =
            getEndpointId(
              link.source,
            );

          const target =
            getEndpointId(
              link.target,
            );

          return (
            source ===
              selectedNode.id ||
            target ===
              selectedNode.id
          );
        },
      );
    }, [
      selectedNode,
      graph.links,
    ]);

  function getConnectedNode(
    link: GraphLink,
  ): GraphNode | undefined {
    if (!selectedNode) {
      return undefined;
    }

    const source =
      getEndpointId(
        link.source,
      );

    const target =
      getEndpointId(
        link.target,
      );

    const otherId =
      source ===
      selectedNode.id
        ? target
        : source;

    return graph.nodes.find(
      (node) =>
        node.id === otherId,
    );
  }

  function resetView() {
    setSelectedNode(null);

    graphRef.current?.zoomToFit(
      500,
      60,
    );
  }

  if (loading) {
    return (
      <section className="page-section">
        <div className="empty-state">
          Loading Neo4j graph...
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="page-section">
        <button
          className="back-button"
          onClick={onBack}
        >
          ← Back to actor
        </button>

        <div className="empty-state">
          {error}
        </div>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="graph-page-header">
        <div>
          <button
            className="back-button"
            onClick={onBack}
          >
            ← Back to actor
          </button>

          <div className="eyebrow">
            RELATIONSHIP ANALYSIS
          </div>

          <h1>
            Correlation Graph
          </h1>

          <p>
            Neo4j relationship network
            for actor{" "}
            <strong>
              {actorId}
            </strong>
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={resetView}
        >
          Reset View
        </button>
      </div>

      <div className="stats">
        <div className="stat-card">
          <span>Nodes</span>

          <strong>
            {graph.nodes.length}
          </strong>
        </div>

        <div className="stat-card">
          <span>
            Relationships
          </span>

          <strong>
            {graph.links.length}
          </strong>
        </div>

        <div className="stat-card">
          <span>
            Selected
          </span>

          <strong className="small-stat">
            {selectedNode
              ? getNodeDisplayLabel(
                  selectedNode,
                )
              : "None"}
          </strong>
        </div>
      </div>

      <div className="graph-layout">
        <div className="panel graph-panel">
          <div className="panel-header">
            <div>
              <div className="eyebrow">
                NEO4J NETWORK
              </div>

              <h2>
                Infrastructure &
                Identity Correlation
              </h2>
            </div>
          </div>

          <div className="graph-container">
            <ForceGraph2D
              ref={graphRef}

              graphData={graphData}

              nodeLabel={(node) => {
                const n =
                  node as GraphNode;

                return `${getNodeType(
                  n,
                )}: ${getNodeDisplayLabel(
                  n,
                )}`;
              }}

              nodeColor={(node) => {
                const n =
                  node as GraphNode;

                if (
                  selectedNode &&
                  !connectedNodeIds.has(
                    n.id,
                  )
                ) {
                  return "rgba(100,110,125,0.30)";
                }

                return getNodeColor(
                  n,
                );
              }}

              nodeVal={(node) => {
                const n =
                  node as GraphNode;

                return getNodeSize(
                  n,
                );
              }}

              linkLabel={(link) => {
                const l =
                  link as GraphLink;

                return String(
                  l.type ??
                    "RELATED_TO",
                );
              }}

              linkDirectionalArrowLength={
                6
              }

              linkDirectionalArrowRelPos={
                1
              }

              linkWidth={(link) => {
                if (!selectedNode) {
                  return 1.5;
                }

                const l =
                  link as GraphLink;

                const source =
                  getEndpointId(
                    l.source,
                  );

                const target =
                  getEndpointId(
                    l.target,
                  );

                return source ===
                  selectedNode.id ||
                  target ===
                    selectedNode.id
                  ? 3
                  : 0.7;
              }}

              linkColor={(link) => {
                if (!selectedNode) {
                  return "rgba(150,160,180,0.55)";
                }

                const l =
                  link as GraphLink;

                const source =
                  getEndpointId(
                    l.source,
                  );

                const target =
                  getEndpointId(
                    l.target,
                  );

                if (
                  source ===
                    selectedNode.id ||
                  target ===
                    selectedNode.id
                ) {
                  return "#ffffff";
                }

                return "rgba(100,110,125,0.18)";
              }}

              backgroundColor="#0b0f17"

              cooldownTicks={150}

              warmupTicks={50}

              d3VelocityDecay={0.3}

              d3AlphaDecay={0.025}

              onEngineStop={() => {
                graphRef.current?.zoomToFit(
                  500,
                  60,
                );
              }}

              onNodeClick={(node) => {
                setSelectedNode(
                  node as GraphNode,
                );
              }}

              nodeCanvasObject={(
                node,
                ctx,
                globalScale,
              ) => {
                const n =
                  node as GraphNodeWithPosition;

                if (
                  typeof n.x !==
                    "number" ||
                  typeof n.y !==
                    "number"
                ) {
                  return;
                }

                const graphNode =
                  n as GraphNode;

                const label =
                  getShortLabel(
                    graphNode,
                  );

                const radius =
                  getNodeSize(
                    graphNode,
                  );

                const isSelected =
                  selectedNode?.id ===
                  n.id;

                const isConnected =
                  !selectedNode ||
                  connectedNodeIds.has(
                    n.id,
                  );

                const opacity =
                  isConnected
                    ? 1
                    : 0.25;

                ctx.save();

                ctx.globalAlpha =
                  opacity;

                ctx.beginPath();

                ctx.arc(
                  n.x,
                  n.y,
                  radius,
                  0,
                  2 * Math.PI,
                );

                ctx.fillStyle =
                  getNodeColor(
                    graphNode,
                  );

                ctx.fill();

                ctx.strokeStyle =
                  isSelected
                    ? "#ffffff"
                    : "rgba(255,255,255,0.35)";

                ctx.lineWidth =
                  isSelected
                    ? 3 /
                      globalScale
                    : 1 /
                      globalScale;

                ctx.stroke();

                const fontSize =
                  Math.max(
                    11 /
                      globalScale,
                    4,
                  );

                ctx.font = `600 ${fontSize}px Inter, Arial, sans-serif`;

                ctx.textAlign =
                  "center";

                ctx.textBaseline =
                  "middle";

                const textWidth =
                  ctx.measureText(
                    label,
                  ).width;

                const padding = 5;

                const boxWidth =
                  textWidth +
                  padding * 2;

                const boxHeight =
                  fontSize +
                  padding;

                const labelX =
                  n.x -
                  boxWidth / 2;

                const labelY =
                  n.y +
                  radius +
                  8;

                ctx.fillStyle =
                  "rgba(11,15,23,0.88)";

                ctx.fillRect(
                  labelX,
                  labelY,
                  boxWidth,
                  boxHeight,
                );

                ctx.fillStyle =
                  "#f1f3f5";

                ctx.textBaseline =
                  "top";

                ctx.fillText(
                  label,
                  n.x,
                  labelY +
                    padding / 2,
                );

                ctx.restore();
              }}
            />
          </div>
        </div>

        <div className="panel graph-details">
          <div className="panel-header">
            <div>
              <div className="eyebrow">
                ENTITY DETAILS
              </div>

              <h2>
                {selectedNode
                  ? getNodeDisplayLabel(
                      selectedNode,
                    )
                  : "Select a node"}
              </h2>
            </div>
          </div>

          {!selectedNode ? (
            <div className="empty-state">
              Click any node in
              the graph to inspect
              the entity and its
              relationships.
            </div>
          ) : (
            <>
              <div className="node-details">
                <div className="detail-row">
                  <span>
                    Type
                  </span>

                  <strong>
                    {getNodeType(
                      selectedNode,
                    )}
                  </strong>
                </div>

                <div className="detail-row">
                  <span>
                    Identifier
                  </span>

                  <strong>
                    {selectedNode.id}
                  </strong>
                </div>

                <div className="detail-row">
                  <span>
                    Label
                  </span>

                  <strong>
                    {getNodeDisplayLabel(
                      selectedNode,
                    )}
                  </strong>
                </div>
              </div>

              <div className="relationships">
                <h3>
                  Connected Entities
                </h3>

                {selectedRelationships
                  .length === 0 ? (
                  <div className="empty-state">
                    No relationships
                    found.
                  </div>
                ) : (
                  selectedRelationships.map(
                    (link, index) => {
                      const connected =
                        getConnectedNode(
                          link,
                        );

                      return (
                        <div
                          className="relationship-item"
                          key={`${link.source}-${link.target}-${index}`}
                        >
                          <div>
                            <strong>
                              {connected
                                ? getNodeDisplayLabel(
                                    connected,
                                  )
                                : "Unknown"}
                            </strong>

                            <span>
                              {connected
                                ? getNodeType(
                                    connected,
                                  )
                                : "unknown"}
                            </span>
                          </div>

                          <span className="relationship-type">
                            {link.type}
                          </span>
                        </div>
                      );
                    },
                  )
                )}
              </div>
            </>
          )}

          <div className="legend">
            <h3>
              Entity Types
            </h3>

            {[
              [
                "Actor",
                "#ff4d6d",
              ],
              [
                "Handle",
                "#4dabf7",
              ],
              [
                "Wallet",
                "#ffd43b",
              ],
              [
                "Marketplace",
                "#69db7c",
              ],
              [
                "Infrastructure",
                "#da77f2",
              ],
              [
                "Observation",
                "#ffa94d",
              ],
            ].map(
              ([name, color]) => (
                <div
                  className="legend-item"
                  key={name}
                >
                  <span
                    className="legend-dot"
                    style={{
                      backgroundColor:
                        color,
                    }}
                  />

                  <span>
                    {name}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
      </div>
    </section>
  );
}