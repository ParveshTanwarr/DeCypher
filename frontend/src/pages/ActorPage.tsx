import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getActorTimeline } from "../api/graph";
import { ActorTimeline } from "../components/actor/ActorTimeline";
import type { ActorTimelineEvent } from "../types/graph";

export function ActorPage() {
  const { actorId = "" } = useParams();
  const [events, setEvents] = useState<ActorTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    setLoading(true);

    getActorTimeline(actorId).then((timelineEvents) => {
      if (isMounted) {
        setEvents(timelineEvents);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [actorId]);

  const displayId = actorId || "UNKNOWN ACTOR";

  return (
    <main className="actor-investigation-page">
      <div className="investigation-background" aria-hidden="true">
        <div className="background-grid" />
        <div className="background-glow background-glow-one" />
        <div className="background-glow background-glow-two" />
      </div>

      <header className="investigation-header">
        <div className="investigation-brand">
          <Link to="/" className="brand">
            <span className="brand-mark">D</span>

            <span className="brand-copy">
              <strong>DeCypher</strong>
              <small>RELATIONSHIP INTELLIGENCE</small>
            </span>
          </Link>

          <span className="header-divider" />

          <div className="workspace-label">
            <span className="live-indicator" />
            ACTOR INVESTIGATION
          </div>
        </div>

        <Link to="/graph" className="back-link">
          <span>←</span>
          Back to graph
        </Link>
      </header>

      <section className="actor-content">
        <div className="actor-breadcrumb">
          <Link to="/graph">Graph</Link>
          <span>/</span>
          <span>Actor Investigation</span>
          <span>/</span>
          <strong>{displayId}</strong>
        </div>

        <div className="actor-title-row">
          <div>
            <p className="section-kicker">ENTITY DOSSIER</p>

            <h1>{displayId}</h1>

            <p className="actor-subtitle">
              Behavioral identity lifecycle and relationship evidence
            </p>
          </div>

          <div className="actor-risk-badge">
            <span className="risk-dot" />
            <span>INVESTIGATION ACTIVE</span>
          </div>
        </div>

        <div className="actor-overview-grid">
          <article className="intel-card primary-intel-card">
            <div className="intel-card-header">
              <span>IDENTITY</span>
              <span className="intel-card-index">01</span>
            </div>

            <div className="identity-display">
              <div className="identity-avatar">
                {displayId.slice(-1)}
              </div>

              <div>
                <span>ACTOR IDENTIFIER</span>
                <strong>{displayId}</strong>
              </div>
            </div>

            <div className="intel-divider" />

            <div className="intel-stat-grid">
              <div>
                <span>STATUS</span>
                <strong>ACTIVE</strong>
              </div>

              <div>
                <span>EVIDENCE</span>
                <strong>{events.length} EVENTS</strong>
              </div>
            </div>
          </article>

          <article className="intel-card">
            <div className="intel-card-header">
              <span>RISK ASSESSMENT</span>
              <span className="intel-card-index">02</span>
            </div>

            <div className="risk-display">
              <strong>HIGH</strong>
              <span>Requires analyst attention</span>
            </div>

            <div className="risk-meter">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>

            <div className="risk-footer">
              <span>CONFIDENCE</span>
              <strong>94.8%</strong>
            </div>
          </article>

          <article className="intel-card">
            <div className="intel-card-header">
              <span>RELATIONSHIPS</span>
              <span className="intel-card-index">03</span>
            </div>

            <div className="relationship-count">
              <strong>{events.length || 0}</strong>
              <span>observed events</span>
            </div>

            <div className="relationship-types">
              <span>HANDLE</span>
              <span>WALLET</span>
              <span>STYLOMETRY</span>
            </div>
          </article>
        </div>

        <section className="timeline-section">
          <div className="section-heading-row">
            <div>
              <p className="section-kicker">LIFECYCLE ANALYSIS</p>
              <h2>Actor Timeline</h2>
              <p>
                Chronological view of observed identity and relationship
                signals.
              </p>
            </div>

            <div className="timeline-status">
              <span className="status-pulse" />
              EVIDENCE STREAM
            </div>
          </div>

          <div className="timeline-container">
            {loading ? (
              <div className="actor-loading">
                <div className="loading-orbit">
                  <span />
                  <span />
                  <span />
                </div>

                <p>RECONSTRUCTING ACTOR LIFECYCLE</p>
                <span>Correlating observed signals...</span>
              </div>
            ) : events.length > 0 ? (
              <ActorTimeline events={events} />
            ) : (
              <div className="actor-empty-state">
                <span>NO TIMELINE DATA</span>
                <p>
                  No lifecycle events are currently available for this actor.
                </p>
              </div>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}