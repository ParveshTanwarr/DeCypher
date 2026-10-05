import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import ForceGraph2D from "react-force-graph-2d";

import { getActorGraph, getHistoricalCaseContext } from "../api/client";

import type {
  GraphLink,
  GraphNode,
  HistoricalCaseContext,
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
  "pgpkey",
  "trustedhandle",
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
  const [historicalCases, setHistoricalCases] = useState<HistoricalCaseContext[]>([]);

  const [selectedNode, setSelectedNode] =
    useState<GraphNode | null>(null);
  const [showEvidenceNodes, setShowEvidenceNodes] =
    useState(false);

  const graphRef = useRef<any>(null);

  useEffect(() => {
    setError("");
    setSelectedNode(null);
    setHistoricalCases([]);

    getHistoricalCaseContext(actorId)
      .then((result) => setHistoricalCases(result.matches || []))
      .catch(() => setHistoricalCases([]));

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

    type: node.type,
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

    relation: link.relation,
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
    () => {
      const nodes = graph.nodes.filter(
        (node) =>
          showEvidenceNodes ||
          getNodeType(node) !== "observation",
      );

      const visibleIds = new Set(
        nodes.map((node) => String(node.id)),
      );

      const links = graph.links.filter(
        (link) =>
          visibleIds.has(getEndpointId(link.source)) &&
          visibleIds.has(getEndpointId(link.target)) &&
          getEndpointId(link.source) !==
            getEndpointId(link.target),
      );

      return {
        nodes: nodes.map((node) => ({
          ...node,
        })),
        links: links.map((link) => ({
          ...link,
        })),
      };
    },
    [graph, showEvidenceNodes],
  );

  function getNodeType(
    node: GraphNode,
  ): string {
    const explicitType =
      String(
        node.type,
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

  const caseAliases = useMemo(
    () => new Set(
      historicalCases.flatMap((item) =>
        item.matched_identities.flatMap((identity) =>
          identity.matched_aliases.map((alias) => alias.toLowerCase()),
        ),
      ),
    ),
    [historicalCases],
  );

  function isDocumentedCaseNode(node: GraphNode): boolean {
    return (
      getNodeType(node) === "handle" &&
      caseAliases.has(getNodeDisplayLabel(node).toLowerCase())
    );
  }

  function getNodeColor(
    node: GraphNode,
  ) {
    if (isDocumentedCaseNode(node)) {
      return "#51cf66";
    }

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

      case "pgpkey":
        return "#f783ac";

      case "trustedhandle":
        return "#74c0fc";

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

      case "pgpkey":
        return 10;

      case "trustedhandle":
        return 9;

      default:
        return 8;
    }
  }

  function getNodeDisplayLabel(
    node: GraphNode,
  ): string {
    const type = getNodeType(node);
    const rawLabel = String(
      node.name ??
        node.label ??
        node.id ??
        "",
    )
      .replace(
        /\s*(?:Synthetic evidence generated.*?controlled SIH demonstration;|not a real-world observation\.?)/gi,
        "",
      )
      .replace(/\s{2,}/g, " ")
      .trim();

    if (type === "observation") {
      const indicatorType = String(
        node.properties?.indicator_type || "",
      ).trim().toLowerCase();

      const signalLabels: Record<string, string> = {
        default_banner: "Default service banner",
        ssl_cert_reuse: "TLS / certificate reuse",
        exposed_status_page: "Exposed status page",
        descriptor_timing: "Descriptor timing",
        banner: "Banner correlation",
        tls: "TLS / certificate",
        infrastructure: "Infrastructure signal",
      };

      if (signalLabels[indicatorType]) {
        return signalLabels[indicatorType];
      }

      const lower = rawLabel.toLowerCase();
      if (lower.includes("banner")) {
        return "Banner correlation";
      }
      if (lower.includes("status page")) {
        return "Exposed status page";
      }
      if (
        lower.includes("tls") ||
        lower.includes("certificate") ||
        lower.includes("cert")
      ) {
        return "TLS / certificate reuse";
      }
      if (lower.includes("descriptor")) {
        return "Descriptor timing";
      }

      return "Evidence";
    }

    return rawLabel || String(node.id);
  }

  function getShortLabel(
    node: GraphNode,
  ): string {
    const label =
      getNodeDisplayLabel(
        node,
      );

    if (
      (getNodeType(node) === "wallet" ||
        getNodeType(node) === "pgpkey" ||
        getNodeType(node) === "infrastructure") &&
      label.length > 20
    ) {
      return (
        label.slice(0, 9) +
        "..." +
        label.slice(-7)
      );
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

      graphData.links.forEach(
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
      graphData.links,
    ]);

  const selectedRelationships =
    useMemo(() => {
      if (!selectedNode) {
        return [];
      }

      return graphData.links.filter(
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
      graphData.links,
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

    return graphData.nodes.find(
      (node) =>
        node.id === otherId,
    );
  }

  function getLinkDistance(
    link: GraphLink,
  ): number {
    switch (
      String(link.relation || "").toUpperCase()
    ) {
      case "USES_HANDLE":
        return 135;
      case "SHARES_WALLET":
      case "ALSO_USED_BY":
        return 145;
      case "HAS_PGP_KEY":
        return 125;
      case "USES_MARKETPLACE":
        return 120;
      case "TRUSTS":
        return 155;
      case "EVIDENCE_OF":
        return 115;
      case "POSSIBLE_MATCH":
        return 145;
      case "HAS_OBSERVATION":
        return 105;
      default:
        return 130;
    }
  }

  function resetView() {
    setSelectedNode(null);
    graphRef.current?.d3ReheatSimulation?.();

    window.setTimeout(() => {
      graphRef.current?.zoomToFit?.(650, 54);
    }, 80);
  }

  useEffect(() => {
    const graphApi = graphRef.current;

    if (!graphApi || !graphData.nodes.length) {
      return;
    }

    graphApi
      .d3Force?.("charge")
      ?.strength?.(-430)
      ?.distanceMax?.(720);

    graphApi
      .d3Force?.("link")
      ?.distance?.((link: GraphLink) =>
        getLinkDistance(link),
      );

    graphApi
      .d3Force?.("center")
      ?.strength?.(0.08);

    graphApi.d3ReheatSimulation?.();

    const timer = window.setTimeout(() => {
      graphApi.zoomToFit?.(650, 54);
    }, 220);

    return () =>
      window.clearTimeout(timer);
  }, [
    graphData.nodes.length,
    graphData.links.length,
    showEvidenceNodes,
  ]);

  if (loading) {
    return (
      <section className="page-section">
        <div className="empty-state">
          Loading correlation graph...
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
            Relationship network
            for actor{" "}
            <strong>
              {actorId}
            </strong>
          </p>

          {historicalCases.length > 0 && (
            <div style={{ marginTop: "12px", display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
              <span className="eyebrow">DOCUMENTED CASE CONTEXT</span>
              {historicalCases.map((item) => (
                <span key={item.case_id} style={{ fontSize: "11px", padding: "5px 8px", borderRadius: "999px", background: "rgba(81,207,102,0.12)", border: "1px solid rgba(81,207,102,0.28)" }}>
                  {item.case_name} · {item.matched_aliases.join(", ")}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="graph-header-actions">
          <button
            className="secondary-button"
            onClick={() =>
              setShowEvidenceNodes((value) => !value)
            }
          >
            {showEvidenceNodes
              ? "Hide evidence nodes"
              : "Show evidence nodes"}
          </button>

          <button
            className="secondary-button"
            onClick={resetView}
          >
            Fit graph
          </button>
        </div>
      </div>

      <div className="stats">
        <div className="stat-card">
          <span>Nodes</span>

          <strong>
            {graphData.nodes.length}
          </strong>
        </div>

        <div className="stat-card">
          <span>
            Relationships
          </span>

          <strong>
            {graphData.links.length}
          </strong>
        </div>

        <div className="stat-card">
          <span>Case-linked handles</span>
          <strong>{caseAliases.size}</strong>
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
                RELATIONSHIP NETWORK
              </div>

              <h2>
                Infrastructure & Identity Correlation
              </h2>
              <span className="graph-panel-hint">
                Select a node to inspect relationships
              </span>
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

                return String(l.relation || "RELATED_TO");
              }}

              linkDirectionalArrowLength={
                6
              }

              linkDirectionalArrowRelPos={
                0.96
              }

              linkDistance={(link) =>
                getLinkDistance(link as GraphLink)
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

              cooldownTicks={190}

              warmupTicks={70}

              d3VelocityDecay={0.47}

              d3AlphaDecay={0.035}

              minZoom={0.35}

              maxZoom={5}

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

              onBackgroundClick={() => {
                setSelectedNode(null);
              }}

              nodeCanvasObject={(
                node,
                ctx,
                globalScale,
              ) => {
                const n =
                  node as GraphNodeWithPosition;

                if (
                  typeof n.x !== "number" ||
                  typeof n.y !== "number"
                ) {
                  return;
                }

                const graphNode =
                  n as GraphNode;

                const type =
                  getNodeType(
                    graphNode,
                  );

                const radius =
                  getNodeSize(
                    graphNode,
                  );

                const isSelected =
                  selectedNode?.id === n.id;

                const isConnected =
                  !selectedNode ||
                  connectedNodeIds.has(
                    String(n.id),
                  );

                ctx.save();

                ctx.globalAlpha =
                  isConnected ? 1 : 0.2;

                if (isSelected) {
                  ctx.beginPath();
                  ctx.arc(
                    n.x,
                    n.y,
                    radius +
                      5 /
                        Math.max(
                          globalScale,
                          0.4,
                        ),
                    0,
                    2 * Math.PI,
                  );
                  ctx.fillStyle =
                    "rgba(255,255,255,0.08)";
                  ctx.fill();
                }

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
                    : "rgba(255,255,255,0.28)";

                ctx.lineWidth =
                  (isSelected ? 2.8 : 1) /
                  Math.max(
                    globalScale,
                    0.45,
                  );

                ctx.stroke();

                const primaryType =
                  type === "actor" ||
                  type === "handle" ||
                  type === "trustedhandle";

                const labelVisible =
                  isSelected ||
                  (primaryType &&
                    globalScale >= 0.78) ||
                  (!primaryType &&
                    globalScale >= 1.25);

                if (!labelVisible) {
                  ctx.restore();
                  return;
                }

                const rawLabel =
                  getNodeDisplayLabel(
                    graphNode,
                  );

                const label =
                  rawLabel.length > 22 &&
                  !primaryType
                    ? rawLabel.slice(0, 10) +
                      "..." +
                      rawLabel.slice(-7)
                    : rawLabel;

                const fontSize =
                  Math.max(
                    10 /
                      Math.max(
                        globalScale,
                        0.45,
                      ),
                    4,
                  );

                ctx.font =
                  "600 " +
                  fontSize +
                  "px Inter, Arial, sans-serif";

                ctx.textAlign =
                  "center";

                ctx.textBaseline =
                  "middle";

                const textWidth =
                  ctx.measureText(
                    label,
                  ).width;

                const paddingX = 5;
                const paddingY = 3;

                const boxWidth =
                  textWidth +
                  paddingX * 2;

                const boxHeight =
                  fontSize +
                  paddingY * 2;

                const labelY =
                  n.y +
                  radius +
                  8;

                ctx.fillStyle =
                  "rgba(11,15,23,0.86)";

                const left =
                  n.x -
                  boxWidth / 2;

                if (
                  typeof ctx.roundRect ===
                  "function"
                ) {
                  ctx.beginPath();
                  ctx.roundRect(
                    left,
                    labelY,
                    boxWidth,
                    boxHeight,
                    4 /
                      Math.max(
                        globalScale,
                        0.45,
                      ),
                  );
                  ctx.fill();
                } else {
                  ctx.fillRect(
                    left,
                    labelY,
                    boxWidth,
                    boxHeight,
                  );
                }

                ctx.fillStyle =
                  "#edf2f7";

                ctx.textBaseline =
                  "top";

                ctx.fillText(
                  label,
                  n.x,
                  labelY +
                    paddingY,
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
              Click an actor, handle, wallet, marketplace, PGP key,
              or infrastructure node to inspect its relationships.
              Evidence records are hidden from the canvas by default
              to keep the network readable.
            </div>
          ) : (
            <>
              {selectedNode && isDocumentedCaseNode(selectedNode) && (
            <div style={{ marginBottom: "12px", padding: "10px 12px", borderRadius: "8px", background: "rgba(81,207,102,0.08)", border: "1px solid rgba(81,207,102,0.22)", fontSize: "11px" }}>
              <strong>Documented case alias</strong>
              <div style={{ opacity: 0.65, marginTop: "3px" }}>
                This handle matches a documented public-case alias. The graph highlight is provenance context, not an independent identity conclusion.
              </div>
            </div>
          )}

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
                            {link.relation}
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
              ...(caseAliases.size > 0
                ? [[
                    "Documented case alias",
                    "#51cf66",
                  ]]
                : []),
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
              ...(showEvidenceNodes
                ? [
                    [
                      "Evidence",
                      "#ffa94d",
                    ],
                  ]
                : []),
              [
                "PGP Key",
                "#f783ac",
              ],
              [
                "Trusted Handle",
                "#74c0fc",
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