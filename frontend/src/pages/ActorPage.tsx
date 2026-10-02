import { useEffect, useMemo, useState } from "react";
import {
  getActor,
  getActorEvidence,
  getActorCorrelation,
  getActorGraph,
  getActorTimeline,
  getActorGraphAnomaly,
  getActorBehavioralProfile,
  refreshActorBehavioralProfile,
  getEvidenceIntegrityStatus,
  verifyEvidenceIntegrity,
  downloadActorExport,
  downloadActorReport,
} from "../api/client";
import type {
  BehavioralProfile,
  CorrelationResult,
  EvidenceIntegrityStatus,
  EvidenceIntegrityVerification,
  GraphNode,
  GraphLink,
  ActorTimeline,
  GraphAnomalyResult,
} from "../api/client";

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
  target?: string;
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
    node.type || node.category || node.label || "unknown",
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
      link.relation || "RELATED_TO",
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
  const [behavioralProfile, setBehavioralProfile] =
    useState<BehavioralProfile | null>(null);
  const [behavioralLoading, setBehavioralLoading] = useState(true);
  const [behavioralError, setBehavioralError] = useState("");
  const [integrityStatus, setIntegrityStatus] =
    useState<EvidenceIntegrityStatus | null>(null);
  const [integrityVerification, setIntegrityVerification] =
    useState<EvidenceIntegrityVerification | null>(null);
  const [integrityChecking, setIntegrityChecking] = useState(false);
  const [timelineData, setTimelineData] = useState<ActorTimeline | null>(null);
  const [graphAnomaly, setGraphAnomaly] = useState<GraphAnomalyResult | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [analyticsError, setAnalyticsError] = useState("");

  const [loading, setLoading] = useState(true);
  const [correlationLoading, setCorrelationLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [timelineStart, setTimelineStart] = useState("");
  const [timelineEnd, setTimelineEnd] = useState("");


  const behavioralDrift = behavioralProfile?.behavioral_drift;

  const filteredEvidence = useMemo(() => {
    const start = timelineStart
      ? new Date(`${timelineStart}T00:00:00`).getTime()
      : Number.NEGATIVE_INFINITY;
    const end = timelineEnd
      ? new Date(`${timelineEnd}T23:59:59.999`).getTime()
      : Number.POSITIVE_INFINITY;

    return evidence.filter((item) => {
      if (!item.timestamp) return !timelineStart && !timelineEnd;
      const time = new Date(item.timestamp).getTime();
      return time >= start && time <= end;
    });
  }, [evidence, timelineStart, timelineEnd]);

  useEffect(() => {
    let cancelled = false;

    setLoadError("");
    setCorrelation(null);
    setCorrelationLoading(true);

    getActor(actorId)
      .then((actorData) => {
        if (cancelled) return;

        const actorResult = actorData as ActorDetail;
        setActor(actorResult);

        setBehavioralLoading(true);
        setBehavioralError("");
        const loadBehavioralProfile = async () => {
          try {
            // Profile snapshots are persisted by the backend. Read the latest
            // snapshot first so opening an actor page does not rerun NLP.
            const profile = await getActorBehavioralProfile(actorId);
            // Older persisted snapshots are still readable, but refresh once
            // after a profile-version change so the new aggregation/drift
            // semantics become active without recomputing on every page load.
            if (profile.profile_version !== "1.1") {
              return await refreshActorBehavioralProfile(actorId);
            }
            return profile;
          } catch (error) {
            // Generate only when this actor has never had a profile created.
            // Do not silently turn API/network failures into expensive refreshes.
            if (
              error instanceof Error &&
              (error as Error & { status?: number }).status === 404
            ) {
              return refreshActorBehavioralProfile(actorId);
            }
            throw error;
          }
        };

        loadBehavioralProfile()
          .then((profile) => {
            if (!cancelled) setBehavioralProfile(profile);
          })
          .catch((error) => {
            console.error("Failed to load behavioural profile:", error);
            if (!cancelled) {
              setBehavioralProfile(null);
              setBehavioralError("Behavioural profile could not be loaded from the available evidence.");
            }
          })
          .finally(() => {
            if (!cancelled) setBehavioralLoading(false);
          });

        const handles = actorResult.handles || [];
        const handleA =
          handles[0] || actorResult.primary_handle || undefined;
        const handleB = handles[1] || undefined;

        if (handleA && handleB) {
          getActorCorrelation(actorId, handleA, handleB)
            .then((correlationResult) => {
              if (!cancelled) setCorrelation(correlationResult);
            })
            .catch((error) => {
              console.error(
                "Failed to load correlation analysis:",
                error,
              );
              if (!cancelled) setCorrelation(null);
            })
            .finally(() => {
              if (!cancelled) setCorrelationLoading(false);
            });
        } else {
          setCorrelationLoading(false);
        }
      })
      .catch((error) => {
        console.error("Failed to load actor investigation:", error);
        if (!cancelled) {
          setActor(null);
          setCorrelation(null);
          setCorrelationLoading(false);
          setLoadError(
            error instanceof Error
              ? error.message
              : "Unable to load actor investigation.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    getEvidenceIntegrityStatus()
      .then((status) => {
        if (!cancelled) setIntegrityStatus(status);
      })
      .catch((error) => {
        console.error("Failed to load evidence integrity status:", error);
        if (!cancelled) setIntegrityStatus(null);
      });

    // Evidence is supplementary to the actor record. A failure here
    // must not make an otherwise valid actor appear as "Actor not found".
    getActorEvidence(actorId)
      .then((evidenceData) => {
        if (!cancelled) setEvidence(evidenceData as Evidence[]);
      })
      .catch((error) => {
        console.error("Failed to load actor evidence:", error);
        if (!cancelled) setEvidence([]);
      });

    setAnalyticsLoading(true);
    setAnalyticsError("");
    Promise.allSettled([
      getActorTimeline(actorId, 50),
      getActorGraphAnomaly(actorId),
    ])
      .then(([timelineResult, anomalyResult]) => {
        if (cancelled) return;

        let failed = false;

        if (timelineResult.status === "fulfilled") {
          setTimelineData(timelineResult.value);
        } else {
          failed = true;
          setTimelineData(null);
          console.error("Failed to load actor timeline:", timelineResult.reason);
        }

        if (anomalyResult.status === "fulfilled") {
          setGraphAnomaly(anomalyResult.value);
        } else {
          failed = true;
          setGraphAnomaly(null);
          console.error("Failed to load graph anomaly analysis:", anomalyResult.reason);
        }

        if (failed) {
          setAnalyticsError("One or more advanced analytics views could not be loaded.");
        }
      })
      .finally(() => {
        if (!cancelled) setAnalyticsLoading(false);
      });

    return () => {
      cancelled = true;
    };
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
        {loadError || "Actor not found."}
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

      {/* Evidence-backed behavioural profile */}
      <div className="card" style={{ marginTop: "20px" }}>
        <div className="eyebrow">BEHAVIOURAL INTELLIGENCE · PROFILE v1.0</div>
        <h2 style={{ marginTop: "8px" }}>Behavioural Profile</h2>
        {behavioralLoading ? (
          <div style={{ marginTop: "18px", opacity: 0.7 }}>Extracting linguistic, lifecycle and operational patterns…</div>
        ) : behavioralError || !behavioralProfile ? (
          <div style={{ marginTop: "18px", color: "#ff8787", fontSize: "13px" }}>
            {behavioralError || "No behavioural profile is available."}
          </div>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", flexWrap: "wrap", marginTop: "18px" }}>
              <div>
                <div className="eyebrow">DATA COVERAGE</div>
                <strong style={{ fontSize: "26px" }}>{Math.round(behavioralProfile.coverage.score * 100)}%</strong>
                <div style={{ fontSize: "12px", opacity: 0.65 }}>{behavioralProfile.coverage.available_dimensions}/{behavioralProfile.coverage.total_dimensions} dimensions supported by available data</div>
              </div>
              <div style={{ fontSize: "11px", opacity: 0.55, fontFamily: "monospace" }}>
                {behavioralProfile.generated_at ? new Date(behavioralProfile.generated_at).toLocaleString() : "Generated on refresh"}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(145px, 1fr))", gap: "12px", marginTop: "20px" }}>
              {[
                ["Linked handles", behavioralProfile.summary.linked_handle_count],
                ["Marketplace footprint", behavioralProfile.summary.marketplace_count],
                ["Posts analysed", behavioralProfile.summary.post_count],
                ["Wallet records", behavioralProfile.summary.wallet_count],
                ["Trust links", behavioralProfile.summary.trust_link_count],
                ["Infrastructure findings", behavioralProfile.summary.infrastructure_observation_count],
              ].map(([label, value]) => (
                <div key={label} style={{ padding: "13px", borderRadius: "9px", background: "rgba(255,255,255,0.035)", border: "1px solid rgba(255,255,255,0.07)" }}>
                  <div className="eyebrow">{label}</div>
                  <strong style={{ display: "block", marginTop: "7px", fontSize: "21px" }}>{value}</strong>
                </div>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: "16px", marginTop: "20px" }}>
              <div style={{ padding: "15px", borderRadius: "9px", background: "rgba(255,255,255,0.025)" }}>
                <strong>Linguistic behaviour</strong>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "7px" }}>
                  {behavioralProfile.dimensions.linguistic.available
                    ? `${behavioralProfile.dimensions.linguistic.profiled_handle_count} handles profiled · ${behavioralProfile.dimensions.linguistic.sample_post_count.toLocaleString()} posts analysed`
                    : "No usable post text is available for this actor."}
                </div>
                <div style={{ fontSize: "12px", marginTop: "8px" }}>
                  Cross-handle similarity: {behavioralProfile.dimensions.linguistic.cross_handle_consistency.mean_similarity == null
                    ? "Not available"
                    : `${(behavioralProfile.dimensions.linguistic.cross_handle_consistency.mean_similarity * 100).toFixed(1)}%`}
                </div>
                <div style={{ fontSize: "11px", opacity: 0.55, marginTop: "5px" }}>
                  NLP engine: {behavioralProfile.dimensions.linguistic.engine_status}
                  {behavioralProfile.dimensions.linguistic.fallback_used ? " · fallback active" : ""}
                </div>
                {behavioralProfile.dimensions.linguistic.per_handle.slice(0, 3).map((item) => (
                  <div key={item.handle} style={{ display: "flex", justifyContent: "space-between", gap: "10px", marginTop: "8px", fontSize: "11px" }}>
                    <span>{item.handle}</span><span style={{ opacity: 0.65 }}>{item.post_count.toLocaleString()} posts</span>
                  </div>
                ))}
              </div>
              <div style={{ padding: "15px", borderRadius: "9px", background: "rgba(255,255,255,0.025)" }}>
                <strong>Temporal lifecycle</strong>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "7px" }}>
                  First seen: {behavioralProfile.dimensions.temporal_lifecycle.first_observed || "Unknown"}
                </div>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "5px" }}>
                  Last seen: {behavioralProfile.dimensions.temporal_lifecycle.last_observed || "Unknown"}
                </div>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "5px" }}>
                  Account lifecycle span: {behavioralProfile.dimensions.temporal_lifecycle.observed_span_days == null ? "Unknown" : `${behavioralProfile.dimensions.temporal_lifecycle.observed_span_days.toLocaleString()} days`}
                </div>
                <div style={{ fontSize: "11px", opacity: 0.55, marginTop: "8px" }}>Posting cadence unavailable: source posts have no usable event timestamps.</div>
              </div>
              <div style={{ padding: "15px", borderRadius: "9px", background: "rgba(255,255,255,0.025)" }}>
                <strong>Operational footprint</strong>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "7px" }}>
                  Wallet reuse within actor: {behavioralProfile.dimensions.operational.within_actor_wallet_reuse_count}
                </div>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "5px" }}>
                  Wallets shared across actor records: {behavioralProfile.dimensions.operational.cross_actor_shared_wallet_count}
                </div>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "5px" }}>
                  PGP key associations outside profile: {behavioralProfile.dimensions.operational.pgp_reuse_across_other_handles_count}
                </div>
                {behavioralProfile.dimensions.operational.marketplaces.map((item) => (
                  <div key={item.name} style={{ display: "flex", justifyContent: "space-between", marginTop: "7px", fontSize: "11px" }}>
                    <span>{item.name}</span><span style={{ opacity: 0.65 }}>{item.handle_count} handles</span>
                  </div>
                ))}
              </div>
              <div style={{ padding: "15px", borderRadius: "9px", background: "rgba(255,255,255,0.025)" }}>
                <strong>Interaction & infrastructure</strong>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "7px" }}>
                  Trust links: {behavioralProfile.dimensions.interaction.trust_link_count} · counterparties: {behavioralProfile.dimensions.interaction.distinct_counterparty_handles}
                </div>
                <div style={{ fontSize: "12px", opacity: 0.7, marginTop: "5px" }}>
                  Detected infrastructure observations: {behavioralProfile.dimensions.infrastructure.observation_count}
                </div>
                <div style={{ fontSize: "11px", opacity: 0.55, marginTop: "8px" }}>
                  {behavioralProfile.dimensions.interaction.scope_note}
                </div>
              </div>
            </div>
            {behavioralProfile.patterns.length > 0 && (
              <div style={{ marginTop: "18px" }}>
                <div className="eyebrow">OBSERVED PATTERNS</div>
                {behavioralProfile.patterns.map((pattern, index) => (
                  <div key={index} style={{ marginTop: "8px", padding: "10px 12px", borderRadius: "7px", background: "rgba(255,255,255,0.025)", fontSize: "12px" }}>{pattern}</div>
                ))}
              </div>
            )}
            {behavioralDrift && (
              <div style={{ marginTop: "18px", padding: "14px", borderRadius: "9px", background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div className="eyebrow">PROFILE CHANGE ANALYSIS</div>
                <strong style={{ display: "block", marginTop: "6px" }}>Behavioural drift</strong>
                {!behavioralDrift.available ? (
                  <div style={{ fontSize: "12px", opacity: 0.65, marginTop: "7px" }}>{behavioralDrift.note}</div>
                ) : (
                  <>
                    <div style={{ fontSize: "12px", opacity: 0.65, marginTop: "7px" }}>
                      Compared with {behavioralDrift.baseline_generated_at ? new Date(behavioralDrift.baseline_generated_at).toLocaleString() : "the previous snapshot"}.
                    </div>
                    {behavioralDrift.linguistic_feature_deltas.length > 0 && (
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "8px", marginTop: "10px" }}>
                        {behavioralDrift.linguistic_feature_deltas.slice(0, 4).map((item) => (
                          <div key={item.feature} style={{ padding: "9px", background: "rgba(255,255,255,0.035)", borderRadius: "7px", fontSize: "11px" }}>
                            <div style={{ opacity: 0.65 }}>{item.feature.replace(/_/g, " ")}</div>
                            <strong>{item.delta > 0 ? "+" : ""}{item.delta.toFixed(4)}</strong>
                          </div>
                        ))}
                      </div>
                    )}
                    {Object.entries(behavioralDrift.operational_changes).map(([name, change]) => (
                      <div key={name} style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginTop: "7px", fontSize: "11px" }}>
                        <span>Operational · {name.replace(/_/g, " ")}</span><strong>{change.delta > 0 ? "+" : ""}{change.delta}</strong>
                      </div>
                    ))}
                    {Object.entries(behavioralDrift.lifecycle_changes).map(([name, change]) => (
                      <div key={`lifecycle-${name}`} style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginTop: "7px", fontSize: "11px" }}>
                        <span>Lifecycle · {name.replace(/_/g, " ")}</span><strong>{change.delta > 0 ? "+" : ""}{change.delta}</strong>
                      </div>
                    ))}
                    {Object.entries(behavioralDrift.interaction_changes).map(([name, change]) => (
                      <div key={`interaction-${name}`} style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginTop: "7px", fontSize: "11px" }}>
                        <span>Interaction · {name.replace(/_/g, " ")}</span><strong>{change.delta > 0 ? "+" : ""}{change.delta}</strong>
                      </div>
                    ))}
                    {Object.entries(behavioralDrift.infrastructure_changes).map(([name, change]) => (
                      <div key={`infra-${name}`} style={{ display: "flex", justifyContent: "space-between", gap: "12px", marginTop: "7px", fontSize: "11px" }}>
                        <span>Infrastructure · {name.replace(/_/g, " ")}</span><strong>{change.delta > 0 ? "+" : ""}{change.delta}</strong>
                      </div>
                    ))}
                    <div style={{ fontSize: "11px", opacity: 0.55, marginTop: "10px" }}>{behavioralDrift.note}</div>
                  </>
                )}
              </div>
            )}
            <details style={{ marginTop: "16px", fontSize: "12px", opacity: 0.75 }}>
              <summary style={{ cursor: "pointer" }}>Data limitations & interpretation</summary>
              <ul style={{ paddingLeft: "20px", lineHeight: 1.6 }}>
                {behavioralProfile.limitations.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
              <div style={{ fontFamily: "monospace", fontSize: "10px", wordBreak: "break-all" }}>Profile fingerprint: {behavioralProfile.source_fingerprint}</div>
            </details>
          </>
        )}
      </div>

      {/* Temporal / structural analytics */}
      <div className="card" style={{ marginTop: "20px" }}>
        <div className="eyebrow">ADVANCED EVIDENCE ANALYTICS</div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(260px, 0.85fr) minmax(320px, 1.15fr)",
            gap: "24px",
            marginTop: "14px",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              background: "rgba(255,255,255,0.025)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <div style={{ fontSize: "11px", opacity: 0.55, letterSpacing: "0.08em" }}>
              STRUCTURAL GRAPH ANALYSIS
            </div>
            {analyticsLoading ? (
              <div style={{ marginTop: "14px", opacity: 0.65 }}>Computing graph structure...</div>
            ) : graphAnomaly ? (
              <>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: "10px",
                    marginTop: "10px",
                  }}
                >
                  <div style={{ fontSize: "34px", fontWeight: 800, fontFamily: "monospace" }}>
                    {graphAnomaly.anomaly_score.toFixed(1)}
                  </div>
                  <span style={{ fontSize: "12px", opacity: 0.55 }}>/ 100</span>
                </div>
                <div style={{ fontSize: "12px", opacity: 0.68, marginTop: "4px" }}>
                  {graphAnomaly.level.replace(/_/g, " ")}
                </div>
                <div style={{ marginTop: "16px" }}>
                  {graphAnomaly.contributing_features.length > 0 ? (
                    graphAnomaly.contributing_features.slice(0, 4).map((item) => (
                      <div
                        key={item.feature}
                        style={{
                          padding: "8px 0",
                          borderBottom: "1px solid rgba(255,255,255,0.05)",
                          fontSize: "11px",
                        }}
                      >
                        <div style={{ fontWeight: 700 }}>
                          {item.feature.replace(/_/g, " ")}
                        </div>
                        <div style={{ opacity: 0.52, marginTop: "3px" }}>
                          Population percentile {item.population_percentile.toFixed(1)} · tail score {item.tail_score.toFixed(1)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: "11px", opacity: 0.5 }}>
                      No strong structural outlier features detected.
                    </div>
                  )}
                </div>
                <div style={{ fontSize: "10px", opacity: 0.42, marginTop: "12px", lineHeight: 1.5 }}>
                  Population-relative graph triage signal. It is not an identity verdict or a causal model.
                </div>
              </>
            ) : (
              <div style={{ marginTop: "14px", opacity: 0.55 }}>
                Graph anomaly analysis unavailable.
              </div>
            )}
          </div>

          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              background: "rgba(255,255,255,0.025)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <div style={{ fontSize: "11px", opacity: 0.55, letterSpacing: "0.08em" }}>
              TEMPORAL EVIDENCE GRAPH
            </div>
            {analyticsLoading ? (
              <div style={{ marginTop: "14px", opacity: 0.65 }}>Materializing evidence timeline...</div>
            ) : timelineData ? (
              <>
                <div style={{ display: "flex", gap: "14px", marginTop: "10px", marginBottom: "10px", flexWrap: "wrap" }}>
                  <strong>{timelineData.total_events.toLocaleString()} events</strong>
                  {Object.entries(timelineData.event_types).slice(0, 4).map(([name, count]) => (
                    <span key={name} style={{ fontSize: "10px", opacity: 0.52 }}>
                      {name.replace(/_/g, " ")} · {count}
                    </span>
                  ))}
                </div>
                <div style={{ maxHeight: "255px", overflowY: "auto", paddingRight: "4px" }}>
                  {timelineData.events.slice(0, 10).map((event) => (
                    <div
                      key={event.event_key}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "132px minmax(120px, 1fr)",
                        gap: "12px",
                        padding: "9px 0",
                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                      }}
                    >
                      <div style={{ fontSize: "10px", opacity: 0.46 }}>
                        {formatDate(event.timestamp)}
                      </div>
                      <div>
                        <div style={{ fontSize: "11px", fontWeight: 700 }}>
                          {event.event_type.replace(/_/g, " ")}
                        </div>
                        <div style={{ fontSize: "10px", opacity: 0.48, marginTop: "3px" }}>
                          {event.entity_type} · {event.source}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: "10px", opacity: 0.42, marginTop: "10px", lineHeight: 1.5 }}>
                  Normalized from observed timestamps only; missing activity is not inferred.
                </div>
              </>
            ) : (
              <div style={{ marginTop: "14px", opacity: 0.55 }}>
                Temporal analytics unavailable.
              </div>
            )}
          </div>
        </div>
        {analyticsError && (
          <div style={{ marginTop: "12px", fontSize: "11px", opacity: 0.55 }}>
            {analyticsError}
          </div>
        )}
      </div>

      {/* Evidence integrity */}
      <div className="card" style={{ marginTop: "20px" }}>
        <div className="eyebrow">EVIDENCE INTEGRITY</div>
        <h2 style={{ marginTop: "8px" }}>Tamper-Evident Ledger</h2>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "16px",
            flexWrap: "wrap",
            marginTop: "16px",
          }}
        >
          <div>
            <strong>
              {integrityStatus
                ? `${integrityStatus.entry_count.toLocaleString()} chained evidence records`
                : "Integrity status unavailable"}
            </strong>
            {integrityStatus && (
              <>
                <div style={{ fontSize: "11px", opacity: 0.55, marginTop: "6px" }}>
                  Mode: {integrityStatus.mode.replace(/_/g, " ")} · external blockchain anchor:{" "}
                  {integrityStatus.blockchain_anchor_configured ? "configured" : "not configured"}
                </div>
                <div
                  style={{
                    fontFamily: "monospace",
                    fontSize: "10px",
                    opacity: 0.55,
                    marginTop: "7px",
                    wordBreak: "break-all",
                  }}
                >
                  Head hash: {integrityStatus.head_hash}
                </div>
              </>
            )}
          </div>
          <button
            className="secondary-button"
            disabled={integrityChecking || !integrityStatus}
            onClick={async () => {
              setIntegrityChecking(true);
              try {
                setIntegrityVerification(await verifyEvidenceIntegrity());
              } catch (error) {
                console.error("Evidence integrity verification failed:", error);
                setIntegrityVerification({
                  valid: false,
                  entry_count: integrityStatus?.entry_count || 0,
                  verified_entries: 0,
                  head_hash: integrityStatus?.head_hash || "",
                  broken_sequence_id: null,
                  reason: "Verification request failed.",
                });
              } finally {
                setIntegrityChecking(false);
              }
            }}
          >
            {integrityChecking ? "Verifying..." : "Verify Chain"}
          </button>
        </div>
        {integrityVerification && (
          <div
            style={{
              marginTop: "14px",
              padding: "11px 12px",
              borderRadius: "8px",
              background: "rgba(255,255,255,0.025)",
              fontSize: "11px",
            }}
          >
            <strong>
              {integrityVerification.valid ? "Chain verified" : "Integrity check failed"}
            </strong>
            <div style={{ opacity: 0.62, marginTop: "5px" }}>
              {integrityVerification.reason}
            </div>
          </div>
        )}
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
                  EVIDENCE CORRELATION SCORE
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
                <div style={{ marginTop: "8px", fontSize: "12px", opacity: 0.58, lineHeight: 1.5 }}>
                  Weighted evidence-agreement score, not a calibrated identity probability. Review it with signal coverage and the underlying observations.
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

            {correlation.counterfactual?.available && (
              <div
                style={{
                  marginTop: "20px",
                  paddingTop: "18px",
                  borderTop: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                <div className="eyebrow">COUNTERFACTUAL SENSITIVITY</div>
                <div style={{ fontSize: "12px", opacity: 0.62, marginTop: "6px", lineHeight: 1.5 }}>
                  Leave-one-signal-out analysis shows how sensitive the current weighted score is to each available signal. This is sensitivity analysis, not a causal effect.
                </div>

                <div style={{ marginTop: "12px" }}>
                  {correlation.counterfactual.scenarios.map((scenario) => (
                    <div
                      key={scenario.removed_signal}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "minmax(150px, 1fr) 90px 90px",
                        gap: "10px",
                        alignItems: "center",
                        padding: "9px 0",
                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600 }}>
                          {signalLabel(scenario.removed_signal)}
                        </div>
                        <div style={{ fontSize: "10px", opacity: 0.5, marginTop: "2px" }}>
                          Without: {formatPercent(scenario.without_score)}
                        </div>
                      </div>
                      <div style={{ fontFamily: "monospace", textAlign: "right" }}>
                        Δ {scenario.delta >= 0 ? "+" : ""}{formatPercent(scenario.delta)}
                      </div>
                      <div style={{ fontFamily: "monospace", textAlign: "right", opacity: 0.7 }}>
                        {formatPercent(scenario.absolute_impact)}
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: "10px", opacity: 0.48, marginTop: "9px" }}>
                  {correlation.counterfactual.note}
                </div>
              </div>
            )}

            {correlation.source_reliability &&
              Object.keys(correlation.source_reliability).length > 0 && (
                <div
                  style={{
                    marginTop: "20px",
                    paddingTop: "18px",
                    borderTop: "1px solid rgba(255,255,255,0.08)",
                  }}
                >
                  <div className="eyebrow">SOURCE RELIABILITY</div>
                  <div style={{ fontSize: "12px", opacity: 0.62, marginTop: "6px", lineHeight: 1.5 }}>
                    Review-conditioned source estimates are updated from investigator verdicts on other actors and leave the current actor out of the estimate.
                  </div>

                  {Object.values(correlation.source_reliability).map((source) => (
                    <div
                      key={source.source}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "minmax(140px, 1fr) 90px 90px",
                        gap: "10px",
                        alignItems: "center",
                        padding: "9px 0",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "12px" }}>{source.source}</div>
                        <div style={{ fontSize: "10px", opacity: 0.48, marginTop: "2px" }}>
                          {source.review_count} reviewed actor{source.review_count === 1 ? "" : "s"} · coverage {formatPercent(source.review_coverage)}
                        </div>
                      </div>
                      <div style={{ fontFamily: "monospace", textAlign: "right" }}>
                        {formatPercent(source.posterior)}
                      </div>
                      <div style={{ fontFamily: "monospace", textAlign: "right", opacity: 0.65 }}>
                        ×{source.multiplier.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
            {filteredEvidence.length} observation
            {filteredEvidence.length === 1 ? "" : "s"}
            {filteredEvidence.length !== evidence.length
              ? ` · ${evidence.length} total`
              : ""}
          </div>
        </div>

          <div
            style={{
              display: "flex",
              gap: "10px",
              flexWrap: "wrap",
              marginTop: "16px",
              alignItems: "center",
            }}
          >
            <label style={{ fontSize: "12px", opacity: 0.7 }}>
              From{" "}
              <input
                type="date"
                value={timelineStart}
                max={timelineEnd || undefined}
                onChange={(event) => setTimelineStart(event.target.value)}
                aria-label="Evidence timeline start date"
              />
            </label>
            <label style={{ fontSize: "12px", opacity: 0.7 }}>
              To{" "}
              <input
                type="date"
                value={timelineEnd}
                min={timelineStart || undefined}
                onChange={(event) => setTimelineEnd(event.target.value)}
                aria-label="Evidence timeline end date"
              />
            </label>
            {(timelineStart || timelineEnd) && (
              <button
                className="text-button"
                onClick={() => {
                  setTimelineStart("");
                  setTimelineEnd("");
                }}
              >
                Clear dates
              </button>
            )}
          </div>

        {filteredEvidence.length === 0 ? (
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
            {[...filteredEvidence]
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
                      index === filteredEvidence.length - 1
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
                    {index !== filteredEvidence.length - 1 && (
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
                        index === filteredEvidence.length - 1
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
                          marginTop: "12px",
                          display: "grid",
                          gridTemplateColumns:
                            "repeat(auto-fit, minmax(180px, 1fr))",
                          gap: "8px 16px",
                          fontSize: "11px",
                          fontFamily: "monospace",
                          opacity: 0.58,
                        }}
                      >
                        <span>Observation: {item.observation_id}</span>
                        <span>Source: {item.source || "unknown"}</span>
                        <span>Target: {item.target || "unknown"}</span>
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