import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getGraphPayload } from "../api/graph";
import { ActorGraph } from "../components/graph/ActorGraph";
import { GraphControls } from "../components/graph/GraphControls";
import { GraphLegend } from "../components/graph/GraphLegend";
import type { GraphPayload, NodeCategory } from "../types/graph";

const allCategories: NodeCategory[] = ["actor", "handle", "wallet"];

export function GraphPage() {
  const navigate = useNavigate();
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<Set<NodeCategory>>(
    () => new Set(allCategories),
  );

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
      return { actors: 0, handles: 0, wallets: 0, links: 0 };
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
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">DeCypher</p>
          <h1>Actor Relationship Graph</h1>
        </div>
        <div className="summary-strip" aria-label="Graph summary">
          <span>{summary.actors} actors</span>
          <span>{summary.handles} handles</span>
          <span>{summary.wallets} wallets</span>
          <span>{summary.links} links</span>
        </div>
      </header>

      <div className="graph-layout">
        <aside className="sidebar">
          <GraphControls
            selectedCategories={selectedCategories}
            onToggleCategory={toggleCategory}
            onReset={resetCategories}
          />
          <GraphLegend />
        </aside>
        {graph ? (
          <ActorGraph
            graph={graph}
            selectedCategories={selectedCategories}
            onActorClick={(actorId) => navigate(`/actors/${actorId}`)}
          />
        ) : (
          <div className="graph-stage loading-state">Loading graph</div>
        )}
      </div>
    </main>
  );
}
