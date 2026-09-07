import { useEffect, useState } from "react";
import {
  Activity,
  Database,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Search,
  ShieldCheck,
} from "lucide-react";
import "./App.css";

import { getActors, setAuthToken } from "./api/client";
import LoginPage from "./pages/LoginPage";
import SearchPage from "./pages/SearchPage";
import ActorPage from "./pages/ActorPage";
import GraphPage from "./pages/GraphPage";

type Page = "dashboard" | "search" | "actor" | "graph";

interface ActorSummary {
  actor_id: string;
  primary_handle: string;
  risk_category: string;
  confidence_score: number;
  associated_handles: string[];
  last_active: string;
}

function App() {
  const [token, setToken] = useState(
    () => sessionStorage.getItem("decypher_token") || "",
  );
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedActor, setSelectedActor] = useState("");
  const [actors, setActors] = useState<ActorSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!token) return;
    setAuthToken(token);
    setLoading(true);
    setLoadError("");

    getActors()
      .then(setActors)
      .catch((error) => {
        console.error("Failed to load actors:", error);
        setLoadError("Unable to load intelligence data.");
      })
      .finally(() => setLoading(false));
  }, [token]);

  function handleLogin(newToken: string) {
    sessionStorage.setItem("decypher_token", newToken);
    setAuthToken(newToken);
    setToken(newToken);
    setPage("dashboard");
  }

  function handleLogout() {
    sessionStorage.removeItem("decypher_token");
    setAuthToken("");
    setToken("");
    setActors([]);
    setSelectedActor("");
    setPage("dashboard");
  }

  function openActor(actorId: string) {
    setSelectedActor(actorId);
    setPage("actor");
  }

  function openGraph() {
    if (selectedActor) setPage("graph");
  }

  if (!token) return <LoginPage onLogin={handleLogin} />;

  const highRiskCount = actors.filter((actor) => {
    const risk = String(actor.risk_category || "").toLowerCase();
    return risk === "high" || risk === "critical";
  }).length;

  const averageConfidence = actors.length
    ? (actors.reduce((sum, actor) => sum + Number(actor.confidence_score || 0), 0) / actors.length) * 100
    : 0;

  const navItems = [
    { id: "dashboard" as const, label: "Dashboard", icon: LayoutDashboard },
    { id: "search" as const, label: "Investigation Search", icon: Search },
  ];

  if (selectedActor) {
    navItems.push(
      { id: "actor", label: "Actor Investigation", icon: ShieldCheck },
      { id: "graph", label: "Graph Explorer", icon: GitBranch },
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">D</div>
          <div className="brand-copy">
            <h1>DeCypher</h1>
            <span>Threat Intelligence</span>
          </div>
        </div>

        <div className="sidebar-label">Workspace</div>
        <nav aria-label="Primary navigation">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item${page === id ? " active" : ""}`}
              onClick={() => setPage(id)}
            >
              <span className="nav-icon"><Icon size={16} strokeWidth={1.8} /></span>
              <span className="nav-label">{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" />
          <div>
            <strong>System online</strong>
            <small>Local investigation environment</small>
          </div>
        </div>

        <div className="sidebar-bottom">
          <button className="logout-button" onClick={handleLogout}>
            <LogOut size={15} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="main-content">
        <div className="content-frame">
          {page === "dashboard" && (
            <>
              <header className="page-header">
                <div>
                  <div className="eyebrow">THREAT INTELLIGENCE PLATFORM</div>
                  <h2>Investigation Dashboard</h2>
                  <p>One workspace for actors, evidence, infrastructure and correlation.</p>
                </div>
                <button className="primary-button" onClick={() => setPage("search")}>
                  <Search size={15} />
                  Start Investigation
                </button>
              </header>

              {loadError && <div className="error">{loadError}</div>}

              {loading ? (
                <div className="loading">Loading intelligence data…</div>
              ) : (
                <>
                  <section className="stats-grid">
                    <div className="stat-card">
                      <span>Total Actors</span>
                      <strong>{actors.length}</strong>
                      <small>Indexed identities</small>
                    </div>
                    <div className="stat-card">
                      <span>High Risk</span>
                      <strong>{highRiskCount}</strong>
                      <small>High or critical category</small>
                    </div>
                    <div className="stat-card">
                      <span>Average Confidence</span>
                      <strong>{averageConfidence.toFixed(1)}%</strong>
                      <small>Across indexed actors</small>
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-header">
                      <div>
                        <div className="eyebrow">CORRELATED ACTORS</div>
                        <h3>Recent Intelligence</h3>
                      </div>
                      <button className="secondary-button" onClick={() => setPage("search")}>
                        View all <span aria-hidden="true">→</span>
                      </button>
                    </div>
                    <div className="table-container">
                      <table>
                        <thead>
                          <tr>
                            <th>Actor</th>
                            <th>Primary handle</th>
                            <th>Risk</th>
                            <th>Confidence</th>
                            <th>Last active</th>
                          </tr>
                        </thead>
                        <tbody>
                          {actors.slice(0, 10).map((actor) => (
                            <tr key={actor.actor_id} className="clickable-row" onClick={() => openActor(actor.actor_id)}>
                              <td>{actor.actor_id}</td>
                              <td>{actor.primary_handle}</td>
                              <td><span className={`risk-badge ${String(actor.risk_category || "").toLowerCase()}`}>{actor.risk_category}</span></td>
                              <td>{(Number(actor.confidence_score || 0) * 100).toFixed(1)}%</td>
                              <td>{actor.last_active || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </>
              )}
            </>
          )}

          {page === "search" && <SearchPage onSelectActor={openActor} />}
          {page === "actor" && selectedActor && <ActorPage actorId={selectedActor} onBack={() => setPage("search")} onGraph={openGraph} />}
          {page === "graph" && selectedActor && <GraphPage actorId={selectedActor} onBack={() => setPage("actor")} />}
        </div>
      </main>
    </div>
  );
}

export default App;
