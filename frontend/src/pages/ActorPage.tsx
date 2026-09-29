import { useEffect, useState } from "react";
import {
  getActor,
  getActorEvidence,
  getActorCorrelation,
  getActorGraph,
  downloadActorExport,
  downloadActorReport,
} from "../api/client";
import type { CorrelationResult, GraphNode, GraphLink } from "../api/client";

interface ActorDetail {
  actor_id: string;
  primary_handle: string;
  risk_category: string;
  confidence_score: number;
  priority_score: number;
  first_seen: string;
  last_seen: string;
  last_scan_date?: string;
  handles: string[];
  wallets: string[];
  marketplaces: string[];
  pgp_keys: string[];
  trust_links: {
    source: string;
    target: string;
    relationship_type: string;
    confidence: number;
    source_name?: string;
  }[];
  evidence_trail: unknown[];
}

interface ActorPageProps {
  actorId: string;
  onBack: () => void;
  onGraph: () => void;
}

interface Evidence {
  observation_id: string;
  signal_type: string;
  confidence: number;
  description: string;
  detected: boolean;
  value?: string;
  timestamp?: string;
  source?: string;
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatDate(value?: string) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function signalLabel(type: string) {
  switch (type) {
    case "wallet_reuse":
      return "Wallet reuse";

    case "infrastructure":
      return "Infrastructure";

    case "tls":
      return "TLS / certificate";

    case "banner":
      return "Banner reuse";

    case "descriptor_timing":
      return "Descriptor timing";

    case "stylometry":
      return "Stylometry";

    default:
      return type.replace(/_/g, " ");
  }
}

function graphNodeType(node: GraphNode): string {
  return String(
    node.type ??
      node.category ??
      node.label ??
      "unknown",
  ).trim().toLowerCase();
}

function shortenGraphLabel(value: string, max = 24): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 7)}...${value.slice(-4)}`;
}

async function createGraphSnapshot(actorId: string): Promise<string | undefined> {
  const graph = await getActorGraph(actorId);
  const nodes = graph.nodes || [];
  const links = graph.links || [];

  if (!nodes.length) return undefined;

  const canvas = document.createElement("canvas");
  canvas.width = 1600;
  canvas.height = 900;

  const ctx = canvas.getContext("2d");
  if (!ctx) return undefined;

  const width = canvas.width;
  const height = canvas.height;

  ctx.fillStyle = "#0b0f17";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#f1f3f5";
  ctx.font = "700 30px Inter, Arial, sans-serif";
  ctx.fillText("DeCypher — Investigation Graph", 55, 58);

  ctx.fillStyle = "#8d99ae";
  ctx.font = "400 16px Inter, Arial, sans-serif";
  ctx.fillText(
    `Actor: ${actorId}  •  ${nodes.length} nodes  •  ${links.length} relationships`,
    55,
    88,
  );

  const positions = new Map<string, { x: number; y: number }>();
  const actorNode =
    nodes.find((node) => graphNodeType(node) === "actor") ||
    nodes[0];

  positions.set(actorNode.id, {
    x: width / 2,
    y: height / 2,
  });

  const groups = new Map<string, GraphNode[]>();
  for (const node of nodes) {
    if (node.id === actorNode.id) continue;
    const type = graphNodeType(node);
    if (!groups.has(type)) groups.set(type, []);
    groups.get(type)!.push(node);
  }

  const preferredOrder = [
    "handle",
    "wallet",
    "marketplace",
    "pgpkey",
    "trustedhandle",
    "observation",
    "infrastructure",
  ];

  const orderedTypes = [
    ...preferredOrder.filter((type) => groups.has(type)),
    ...Array.from(groups.keys()).filter(
      (type) => !preferredOrder.includes(type),
    ),
  ];

  const ringRadii = [170, 290, 390, 455];
  let ringIndex = 0;

  orderedTypes.forEach((type) => {
    const group = groups.get(type) || [];
    const radius = ringRadii[Math.min(ringIndex, ringRadii.length - 1)];
    const centerX = width / 2;
    const centerY = height / 2;

    group.forEach((node, index) => {
      const angle =
        (index / Math.max(group.length, 1)) * Math.PI * 2 -
        Math.PI / 2;

      positions.set(node.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      });
    });

    ringIndex += 1;
  });

  const colors: Record<string, string> = {
    actor: "#ff4d6d",
    handle: "#4dabf7",
    wallet: "#ffd43b",
    marketplace: "#69db7c",
    infrastructure: "#da77f2",
    observation: "#ffa94d",
    pgpkey: "#f783ac",
    trustedhandle: "#74c0fc",
  };

  // Relationships first.
  for (const link of links as GraphLink[]) {
    const source = positions.get(String(link.source));
    const target = positions.get(String(link.target));

    if (!source || !target) continue;

    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.strokeStyle = "rgba(150,160,180,0.45)";
    ctx.lineWidth = 2;
    ctx.stroke();

    const angle = Math.atan2(
      target.y - source.y,
      target.x - source.x,
    );
    const arrowSize = 8;

    ctx.beginPath();
    ctx.moveTo(target.x, target.y);
    ctx.lineTo(
      target.x - Math.cos(angle - Math.PI / 6) * arrowSize,
      target.y - Math.sin(angle - Math.PI / 6) * arrowSize,
    );
    ctx.lineTo(
      target.x - Math.cos(angle + Math.PI / 6) * arrowSize,
      target.y - Math.sin(angle + Math.PI / 6) * arrowSize,
    );
    ctx.closePath();
    ctx.fillStyle = "rgba(180,190,205,0.65)";
    ctx.fill();

    const midX = (source.x + target.x) / 2;
    const midY = (source.y + target.y) / 2;
    const relation = String(
      link.relation ?? link.type ?? "RELATED_TO",
    ).replace(/_/g, " ");

    ctx.font = "500 11px Inter, Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(205,213,221,0.72)";
    ctx.fillText(relation, midX, midY - 5);
  }

  // Nodes and labels.
  for (const node of nodes) {
    const position = positions.get(node.id);
    if (!position) continue;

    const type = graphNodeType(node);
    const radius = type === "actor" ? 25 : 16;

    ctx.beginPath();
    ctx.arc(position.x, position.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = colors[type] || "#adb5bd";
    ctx.fill();

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = type === "actor" ? 3 : 1.5;
    ctx.stroke();

    const rawLabel = String(
      node.name ?? node.label ?? node.id,
    );
    const label = shortenGraphLabel(rawLabel);

    ctx.textAlign = "center";
    ctx.font =
      type === "actor"
        ? "700 14px Inter, Arial, sans-serif"
        : "600 12px Inter, Arial, sans-serif";

    const textWidth = ctx.measureText(label).width;
    ctx.fillStyle = "rgba(11,15,23,0.92)";
    ctx.fillRect(
      position.x - textWidth / 2 - 6,
      position.y + radius + 7,
      textWidth + 12,
      21,
    );

    ctx.fillStyle = "#f1f3f5";
    ctx.fillText(label, position.x, position.y + radius + 22);
  }

  // Legend.
  const legend = [
    ["Actor", "actor"],
    ["Handle", "handle"],
    ["Wallet", "wallet"],
    ["Marketplace", "marketplace"],
    ["PGP Key", "pgpkey"],
    ["Trusted Handle", "trustedhandle"],
    ["Observation", "observation"],
    ["Infrastructure", "infrastructure"],
  ];

  let legendX = 55;
  const legendY = height - 45;
  ctx.font = "600 12px Inter, Arial, sans-serif";
  ctx.textAlign = "left";

  for (const [label, type] of legend) {
    ctx.beginPath();
    ctx.arc(legendX + 7, legendY, 7, 0, Math.PI * 2);
    ctx.fillStyle = colors[type] || "#adb5bd";
    ctx.fill();

    ctx.fillStyle = "#cdd5df";
    ctx.fillText(label, legendX + 19, legendY + 4);
    legendX += 105 + label.length * 2;
  }

  return canvas.toDataURL("image/png");
}

export default function ActorPage({
  actorId,
  onBack,
  onGraph,
}: ActorPageProps) {
  const [actor, setActor] = useState<ActorDetail | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [correlation, setCorrelation] =
    useState<CorrelationResult | null>(null);

  const [loading, setLoading] = useState(true);
  const [correlationLoading, setCorrelationLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");

  useEffect(() => {
    setLoading(true);
    setCorrelation(null);
    setCorrelationLoading(true);

    Promise.all([
      getActor(actorId),
      getActorEvidence(actorId),
    ])
      .then(([actorData, evidenceData]) => {
        const actorResult = actorData as ActorDetail;
        const evidenceResult = evidenceData as Evidence[];

        setActor(actorResult);
        setEvidence(evidenceResult);

        /*
         * The correlation engine needs two handles for the
         * stylometry signal. Prefer the first two known handles.
         */
        const handles = actorResult.handles || [];

        const handleA =
          handles[0] || actorResult.primary_handle || undefined;

        const handleB = handles[1] || undefined;

        if (handleA && handleB) {
          return getActorCorrelation(actorId, handleA, handleB)
            .then((correlationResult) => {
              setCorrelation(correlationResult);
            })
            .catch((error) => {
              console.error(
                "Failed to load correlation analysis:",
                error
              );
              setCorrelation(null);
            })
            .finally(() => {
              setCorrelationLoading(false);
            });
        }

        setCorrelationLoading(false);
        return null;
      })
      .catch((error) => {
        console.error(
          "Failed to load actor investigation:",
          error
        );

        setActor(null);
        setEvidence([]);
        setCorrelation(null);
        setCorrelationLoading(false);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [actorId]);

  if (loading) {
    return (
      <div className="empty-state">
        Loading investigation...
      </div>
    );
  }

  if (!actor) {
    return (
      <div className="empty-state">
        Actor not found.
      </div>
    );
  }

  return (
    <section className="page-section">
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "24px",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <button className="back-button" onClick={onBack}>
          ← Back
        </button>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <select
            className="secondary-button"
            disabled={exporting}
            defaultValue=""
            onChange={async (event) => {
              const format = event.target.value as "pdf" | "csv" | "json";
              if (!format) return;
              setExportError("");
              setExporting(true);
              try {
                if (format === "pdf") {
                  const graphImage = await createGraphSnapshot(actorId);
                  await downloadActorReport(actorId, graphImage);
                } else {
                  await downloadActorExport(actorId, format);
                }
              } catch (error) {
                console.error("Actor export failed:", error);
                setExportError("Export failed. Please try again.");
              } finally {
                setExporting(false);
                event.target.value = "";
              }
            }}
          >
            <option value="" disabled>
              {exporting ? "Exporting..." : "Export Actor"}
            </option>
            <option value="pdf">PDF Report</option>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
          </select>

          <button
            className="primary-button"
            onClick={onGraph}
          >
            Explore Graph
          </button>
        </div>
      </div>

      {exportError && (
        <div style={{ marginBottom: "16px", color: "#ff8787", fontSize: "13px" }}>
          {exportError}
        </div>
      )}

      {/* Actor overview */}
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "20px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div className="eyebrow">ACTOR INVESTIGATION</div>

            <h1 style={{ marginBottom: "8px" }}>
              {actor.primary_handle}
            </h1>

            <div
              style={{
                fontFamily: "monospace",
                opacity: 0.7,
              }}
            >
              {actor.actor_id}
            </div>
          </div>

          <div
            style={{
              textAlign: "right",
            }}
          >
            <div className="eyebrow">RISK CATEGORY</div>

            <div
              style={{
                fontSize: "18px",
                fontWeight: 700,
                marginTop: "6px",
              }}
            >
              {actor.risk_category}
            </div>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "16px",
            marginTop: "24px",
          }}
        >
          <div>
            <div className="eyebrow">CONFIDENCE</div>
            <strong>
              {formatPercent(actor.confidence_score)}
            </strong>
          </div>

          <div>
            <div className="eyebrow">PRIORITY</div>
            <strong>{actor.priority_score}</strong>
          </div>

          <div>
            <div className="eyebrow">FIRST SEEN</div>
            <strong>{formatDate(actor.first_seen)}</strong>
          </div>

          <div>
            <div className="eyebrow">LAST SEEN</div>
            <strong>{formatDate(actor.last_seen)}</strong>
          </div>

          <div>
            <div className="eyebrow">LAST SCAN</div>
            <strong>{formatDate(actor.last_scan_date)}</strong>
          </div>
        </div>
      </div>

      {/* Correlation analysis */}
      <div className="card" style={{ marginTop: "20px" }}>
        <div className="eyebrow">CORRELATION ANALYSIS</div>

        <h2 style={{ marginTop: "8px" }}>
          Evidence Correlation
        </h2>

        {correlationLoading ? (
          <div
            style={{
              marginTop: "20px",
              opacity: 0.7,
            }}
          >
            Running correlation engine...
          </div>
        ) : correlation ? (
          <>
            {/* Overall score */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "20px",
                marginTop: "20px",
                padding: "20px",
                borderRadius: "10px",
                background: "rgba(255,255,255,0.04)",
              }}
            >
              <div>
                <div className="eyebrow">
                  OVERALL ASSOCIATION
                </div>

                <div
                  style={{
                    fontSize: "36px",
                    fontWeight: 800,
                    marginTop: "6px",
                  }}
                >
                  {formatPercent(
                    correlation.overall_confidence
                  )}
                </div>
              </div>

              <div
                style={{
                  textTransform: "uppercase",
                  fontWeight: 700,
                  fontSize: "14px",
                }}
              >
                {correlation.risk_level}
              </div>
            </div>

            {/* Signals */}
            <div style={{ marginTop: "24px" }}>
              <div className="eyebrow">
                CORRELATION SIGNALS
              </div>

              {correlation.signals.map((signal) => (
                <div
                  key={signal.type}
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "minmax(150px, 1fr) minmax(90px, 130px)",
                    gap: "16px",
                    alignItems: "center",
                    marginTop: "14px",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontWeight: 600,
                        textTransform: "capitalize",
                      }}
                    >
                      {signalLabel(signal.type)}
                    </div>

                    <div
                      style={{
                        fontSize: "13px",
                        opacity: 0.65,
                        marginTop: "3px",
                      }}
                    >
                      {signal.description}
                    </div>
                  </div>

                  <div>
                    <div
                      style={{
                        fontFamily: "monospace",
                        textAlign: "right",
                        marginBottom: "5px",
                      }}
                    >
                      {formatPercent(signal.confidence)}
                    </div>

                    <div
                      style={{
                        height: "6px",
                        borderRadius: "999px",
                        background: "rgba(255,255,255,0.08)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${Math.max(
                            0,
                            Math.min(
                              100,
                              signal.confidence * 100
                            )
                          )}%`,
                          height: "100%",
                          background: "currentColor",
                          borderRadius: "999px",
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Signal coverage */}
            <div
              style={{
                marginTop: "24px",
                paddingTop: "18px",
                borderTop:
                  "1px solid rgba(255,255,255,0.08)",
                fontSize: "14px",
                opacity: 0.75,
              }}
            >
              {correlation.signal_count} / 6 signals available
            </div>

            {/* Interpretation */}
            <div
              style={{
                marginTop: "18px",
                padding: "16px",
                borderRadius: "8px",
                background: "rgba(255,255,255,0.035)",
              }}
            >
              <div
                style={{
                  fontWeight: 700,
                  marginBottom: "6px",
                }}
              >
                {correlation.interpretation}
              </div>

              <div
                style={{
                  fontSize: "13px",
                  opacity: 0.65,
                }}
              >
                Weighted evidence score across available
                correlation signals.
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              marginTop: "18px",
              opacity: 0.7,
            }}
          >
            Correlation analysis requires at least two
            associated handles.
          </div>
        )}
      </div>

      {/* Handles / wallets / marketplaces */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "20px",
          marginTop: "20px",
        }}
      >
        <div className="card">
          <div className="eyebrow">ASSOCIATED HANDLES</div>

          <div style={{ marginTop: "12px" }}>
            {actor.handles?.length ? (
              actor.handles.map((handle) => (
                <div
                  key={handle}
                  style={{
                    padding: "8px 0",
                    fontFamily: "monospace",
                  }}
                >
                  {handle}
                </div>
              ))
            ) : (
              <div style={{ opacity: 0.6 }}>
                No handles recorded.
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="eyebrow">WALLETS</div>

          <div style={{ marginTop: "12px" }}>
            {actor.wallets?.length ? (
              actor.wallets.map((wallet) => (
                <div
                  key={wallet}
                  style={{
                    padding: "8px 0",
                    fontFamily: "monospace",
                    wordBreak: "break-all",
                  }}
                >
                  {wallet}
                </div>
              ))
            ) : (
              <div style={{ opacity: 0.6 }}>
                No wallets recorded.
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="eyebrow">MARKETPLACES</div>

          <div style={{ marginTop: "12px" }}>
            {actor.marketplaces?.length ? (
              actor.marketplaces.map((marketplace) => (
                <div
                  key={marketplace}
                  style={{
                    padding: "8px 0",
                  }}
                >
                  {marketplace}
                </div>
              ))
            ) : (
              <div style={{ opacity: 0.6 }}>
                No marketplaces recorded.
              </div>
            )}
          </div>
        </div>
      </div>

           {/* PGP / trust intelligence */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "20px",
          marginTop: "20px",
        }}
      >
        <div className="card">
          <div className="eyebrow">PGP IDENTIFIERS</div>
          <div style={{ marginTop: "12px" }}>
            {actor.pgp_keys?.length ? (
              actor.pgp_keys.map((fingerprint) => (
                <div
                  key={fingerprint}
                  style={{
                    padding: "8px 0",
                    fontFamily: "monospace",
                    fontSize: "11px",
                    wordBreak: "break-all",
                  }}
                >
                  {fingerprint}
                </div>
              ))
            ) : (
              <div style={{ opacity: 0.6 }}>No PGP keys recorded.</div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="eyebrow">TRUST LINKS</div>
          <div style={{ marginTop: "12px" }}>
            {actor.trust_links?.length ? (
              actor.trust_links.map((link, index) => (
                <div
                  key={`${link.source}-${link.target}-${index}`}
                  style={{
                    padding: "9px 0",
                    borderBottom:
                      index === actor.trust_links.length - 1
                        ? "0"
                        : "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div
                    style={{
                      fontFamily: "monospace",
                      fontSize: "11px",
                    }}
                  >
                    {link.source} → {link.target}
                  </div>
                  <div
                    style={{
                      marginTop: "4px",
                      fontSize: "10px",
                      opacity: 0.6,
                      textTransform: "uppercase",
                    }}
                  >
                    {link.relationship_type} ·{" "}
                    {(link.confidence * 100).toFixed(0)}% confidence
                  </div>
                </div>
              ))
            ) : (
              <div style={{ opacity: 0.6 }}>No trust links recorded.</div>
            )}
          </div>
        </div>
      </div>

      {/* Evidence timeline */}
      <div className="card" style={{ marginTop: "20px" }}>
        <div className="eyebrow">EVIDENCE TIMELINE</div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            gap: "16px",
            flexWrap: "wrap",
            marginTop: "8px",
          }}
        >
          <div>
            <h2 style={{ margin: 0 }}>
              Investigation Evidence
            </h2>

            <div
              style={{
                marginTop: "6px",
                fontSize: "13px",
                opacity: 0.65,
              }}
            >
              Chronological observations associated with this actor.
            </div>
          </div>

          <div
            style={{
              fontFamily: "monospace",
              fontSize: "12px",
              opacity: 0.6,
            }}
          >
            {evidence.length} observation
            {evidence.length === 1 ? "" : "s"}
          </div>
        </div>

        {evidence.length === 0 ? (
          <div
            style={{
              marginTop: "20px",
              padding: "20px",
              border: "1px dashed rgba(255,255,255,0.12)",
              borderRadius: "10px",
              opacity: 0.65,
            }}
          >
            No evidence observations recorded.
          </div>
        ) : (
          <div style={{ marginTop: "22px" }}>
            {[...evidence]
              .sort((a, b) => {
                const timeA = a.timestamp
                  ? new Date(a.timestamp).getTime()
                  : 0;

                const timeB = b.timestamp
                  ? new Date(b.timestamp).getTime()
                  : 0;

                return timeB - timeA;
              })
              .map((item, index) => (
                <div
                  key={item.observation_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "150px 18px minmax(0, 1fr)",
                    gap: "14px",
                    minHeight:
                      index === evidence.length - 1
                        ? "auto"
                        : "120px",
                  }}
                >
                  {/* Timestamp */}
                  <div
                    style={{
                      textAlign: "right",
                      paddingTop: "2px",
                      fontSize: "12px",
                      fontFamily: "monospace",
                      opacity: 0.6,
                    }}
                  >
                    {item.timestamp
                      ? formatDate(item.timestamp)
                      : "Unknown time"}
                  </div>

                  {/* Timeline marker */}
                  <div
                    style={{
                      position: "relative",
                      display: "flex",
                      justifyContent: "center",
                    }}
                  >
                    {index !== evidence.length - 1 && (
                      <div
                        style={{
                          position: "absolute",
                          top: "12px",
                          bottom: "-20px",
                          width: "1px",
                          background:
                            "rgba(255,255,255,0.12)",
                        }}
                      />
                    )}

                    <div
                      style={{
                        position: "relative",
                        zIndex: 1,
                        width: "10px",
                        height: "10px",
                        marginTop: "4px",
                        borderRadius: "50%",
                        background: "#ffa94d",
                        boxShadow:
                          "0 0 0 4px rgba(255,169,77,0.12)",
                      }}
                    />
                  </div>

                  {/* Evidence content */}
                  <div
                    style={{
                      paddingBottom:
                        index === evidence.length - 1
                          ? "4px"
                          : "24px",
                    }}
                  >
                    <div
                      style={{
                        padding: "16px",
                        borderRadius: "10px",
                        border:
                          "1px solid rgba(255,255,255,0.08)",
                        background:
                          "rgba(255,255,255,0.025)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent:
                            "space-between",
                          alignItems: "flex-start",
                          gap: "14px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div>
                          <div
                            style={{
                              fontSize: "11px",
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                              opacity: 0.5,
                            }}
                          >
                            {item.signal_type}
                          </div>

                          <strong
                            style={{
                              display: "block",
                              marginTop: "4px",
                              fontSize: "16px",
                            }}
                          >
                            {signalLabel(item.signal_type)}
                          </strong>
                        </div>

                        <div
                          style={{
                            fontFamily: "monospace",
                            fontSize: "13px",
                            fontWeight: 600,
                          }}
                        >
                          {formatPercent(item.confidence)}
                        </div>
                      </div>

                      {item.description && (
                        <div
                          style={{
                            marginTop: "10px",
                            fontSize: "13px",
                            lineHeight: 1.5,
                            opacity: 0.7,
                          }}
                        >
                          {item.description}
                        </div>
                      )}

                      {item.value && (
                        <div
                          style={{
                            marginTop: "12px",
                            padding: "10px 12px",
                            borderRadius: "7px",
                            background:
                              "rgba(0,0,0,0.18)",
                            fontFamily: "monospace",
                            fontSize: "12px",
                            lineHeight: 1.5,
                            wordBreak: "break-all",
                          }}
                        >
                          {item.value}
                        </div>
                      )}

                      <div
                        style={{
                          display: "flex",
                          justifyContent:
                            "space-between",
                          gap: "12px",
                          flexWrap: "wrap",
                          marginTop: "12px",
                          fontSize: "11px",
                          opacity: 0.45,
                          fontFamily: "monospace",
                        }}
                      >
                        <span>
                          {item.observation_id}
                        </span>
                        <span>
                          Source: {item.source || "unknown"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </section>
  );
}