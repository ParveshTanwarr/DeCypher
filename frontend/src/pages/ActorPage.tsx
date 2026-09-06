import { useEffect, useState } from "react";
import { getActor, getActorEvidence } from "../api/client";

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

export default function ActorPage({
  actorId,
  onBack,
  onGraph,
}: ActorPageProps) {
  const [actor, setActor] = useState<ActorDetail | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);

    Promise.all([
      getActor(actorId),
      getActorEvidence(actorId),
    ])
      .then(([actorData, evidenceData]) => {
        setActor(actorData as ActorDetail);
        setEvidence(evidenceData as Evidence[]);
      })
      .catch((error) => {
        console.error("Failed to load actor investigation:", error);
        setActor(null);
        setEvidence([]);
      })
      .finally(() => setLoading(false));
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
      <button className="back-button" onClick={onBack}>
        ← Back to search
      </button>

      <div className="actor-header">
        <div>
          <div className="eyebrow">ACTOR PROFILE</div>

          <h1>{actor.primary_handle}</h1>

          <span className="actor-id">
            {actor.actor_id}
          </span>
        </div>

        <button
          className="graph-button"
          onClick={onGraph}
        >
          Open correlation graph
        </button>
      </div>

      <div className="stats">
        <div className="stat-card">
          <span>Risk Category</span>

          <strong className="small-stat">
            {actor.risk_category}
          </strong>
        </div>

        <div className="stat-card">
          <span>Confidence</span>

          <strong>
            {Math.round(actor.confidence_score * 100)}%
          </strong>
        </div>

        <div className="stat-card">
          <span>Last Seen</span>

          <strong className="small-stat">
            {actor.last_seen}
          </strong>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Associated Handles</h2>
        </div>

        <div className="tag-list">
          {actor.handles.length === 0 ? (
            <div className="empty-state">
              No associated handles found.
            </div>
          ) : (
            actor.handles.map((handle) => (
              <span className="tag" key={handle}>
                {handle}
              </span>
            ))
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Associated Wallets</h2>
        </div>

        <div className="tag-list">
          {actor.wallets.length === 0 ? (
            <div className="empty-state">
              No associated wallets found.
            </div>
          ) : (
            actor.wallets.map((wallet) => (
              <span className="tag" key={wallet}>
                {wallet}
              </span>
            ))
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h2>Marketplaces</h2>
        </div>

        <div className="tag-list">
          {actor.marketplaces.length === 0 ? (
            <div className="empty-state">
              No marketplace associations found.
            </div>
          ) : (
            actor.marketplaces.map((marketplace) => (
              <span className="tag" key={marketplace}>
                {marketplace}
              </span>
            ))
          )}
        </div>
      </div>

      <div className="panel evidence-panel">
        <div className="panel-header">
          <div>
            <h2>Evidence Trail</h2>

            <p>
              {evidence.length} observations associated
              with this actor
            </p>
          </div>
        </div>

        {evidence.length === 0 ? (
          <div className="empty-state">
            No evidence observations found.
          </div>
        ) : (
          evidence.map((item) => (
            <div
              className="evidence-item"
              key={item.observation_id}
            >
              <div className="evidence-main">
                <strong>
                  {item.signal_type}
                </strong>

                <span>
                  {item.description}
                </span>

                {item.value && (
                  <span className="evidence-value">
                    {item.value}
                  </span>
                )}
              </div>

              <div className="evidence-meta">
                <span>
                  {Math.round(item.confidence * 100)}%
                  confidence
                </span>

                <span>
                  {item.timestamp || "Unknown date"}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}