import { useEffect, useState } from "react";
import {
  getActor,
  getActorEvidence,
  getActorCorrelation,
} from "../api/client";
import type { CorrelationResult } from "../api/client";

interface ActorDetail {
  actor_id: string;
  primary_handle: string;
  risk_category: string;
  confidence_score: number;
  priority_score: number;
  first_seen: string;
  last_seen: string;
  handles: string[];
  wallets: string[];
  marketplaces: string[];
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

        <button
          className="primary-button"
          onClick={onGraph}
        >
          Explore Graph
        </button>
      </div>

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