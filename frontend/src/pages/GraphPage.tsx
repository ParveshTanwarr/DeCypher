import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getGraphPayload } from "../api/graph";
import { ActorGraph } from "../components/graph/ActorGraph";
import { GraphControls } from "../components/graph/GraphControls";
import { GraphLegend } from "../components/graph/GraphLegend";
import type { GraphPayload, NodeCategory } from "../types/graph";

const allCategories: NodeCategory[] = ["actor", "handle", "wallet"];

export function GraphPage() {
  const navigate = useNavigate();

  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<
    Set<NodeCategory>
  >(() => new Set(allCategories));

  useEffect(() => {
    let isMounted = true;

    getGraphPayload().then((payload) => {
      if (isMounted) {
        setGraph(payload);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const summary = useMemo(() => {
    if (!graph) {
      return {
        actors: 0,
        handles: 0,
        wallets: 0,
        links: 0,
      };
    }

    return {
      actors: graph.nodes.filter((node) => node.category === "actor").length,
      handles: graph.nodes.filter((node) => node.category === "handle").length,
      wallets: graph.nodes.filter((node) => node.category === "wallet").length,
      links: graph.links.length,
    };
  }, [graph]);

  function toggleCategory(category: NodeCategory) {
    setSelectedCategories((current) => {
      const next = new Set(current);

      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }

      return next;
    });
  }

  function resetCategories() {
    setSelectedCategories(new Set(allCategories));
  }

  return (
    <main className="investigation-page">
      {/* Ambient background */}
      <div className="investigation-background" aria-hidden="true">
        <div className="background-grid" />
        <div className="background-glow background-glow-one" />
        <div className="background-glow background-glow-two" />
      </div>

      {/* Top navigation */}
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
            <span>INVESTIGATION WORKSPACE</span>
          </div>
        </div>

        <div className="header-actions">
          <Link to="/" className="header-link">
            Home
          </Link>

          <button
            className="header-icon-button"
            type="button"
            aria-label="Toggle theme"
          >
            ◐
          </button>

          <div className="profile-chip" aria-label="Analyst">
            <span className="profile-avatar">H</span>
            <span>Analyst</span>
          </div>
        </div>
      </header>

      {/* Main workspace */}
      <section className="investigation-workspace">
        {/* Graph heading */}
        <div className="graph-heading">
          <div>
            <p className="section-kicker">NETWORK ANALYSIS</p>

            <h1>Relationship Graph</h1>

            <p>
              Explore connections between actors, handles and infrastructure.
            </p>
          </div>

          <div className="graph-statistics">
            <div className="graph-stat">
              <span className="stat-dot stat-dot-actor" />
              <div>
                <strong>{summary.actors}</strong>
                <small>ACTORS</small>
              </div>
            </div>

            <div className="graph-stat">
              <span className="stat-dot stat-dot-handle" />
              <div>
                <strong>{summary.handles}</strong>
                <small>HANDLES</small>
              </div>
            </div>

            <div className="graph-stat">
              <span className="stat-dot stat-dot-wallet" />
              <div>
                <strong>{summary.wallets}</strong>
                <small>WALLETS</small>
              </div>
            </div>

            <div className="graph-stat">
              <span className="stat-dot stat-dot-link" />
              <div>
                <strong>{summary.links}</strong>
                <small>LINKS</small>
              </div>
            </div>
          </div>
        </div>

        {/* Graph area */}
        <div className="graph-workspace">
          <div className="graph-canvas">
            {graph ? (
              <ActorGraph
                graph={graph}
                selectedCategories={selectedCategories}
                onActorClick={(actorId) =>
                  navigate(`/actors/${actorId}`)
                }
              />
            ) : (
              <div className="graph-loading">
                <div className="loading-orbit">
                  <span />
                  <span />
                  <span />
                </div>

                <p>INITIALIZING INVESTIGATION GRAPH</p>

                <span>Resolving relationships...</span>
              </div>
            )}
          </div>

          {/* Floating controls */}
          <aside className="graph-floating-controls">
            <div className="floating-panel">
              <div className="floating-panel-header">
                <span>VIEW</span>

                <button
                  type="button"
                  className="panel-reset"
                  onClick={resetCategories}
                >
                  Reset
                </button>
              </div>

              <GraphControls
                selectedCategories={selectedCategories}
                onToggleCategory={toggleCategory}
                onReset={resetCategories}
              />
            </div>
          </aside>

          {/* Floating legend */}
          <div className="graph-floating-legend">
            <GraphLegend />
          </div>

          {/* Graph status */}
          <div className="graph-status">
            <span className="status-pulse" />
            <span>LIVE GRAPH</span>
            <span className="status-separator">/</span>
            <span>{summary.links} RELATIONSHIPS MAPPED</span>
          </div>
        </div>
      </section>
    </main>
  );
}