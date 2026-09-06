import { useEffect, useState } from "react";
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

  useEffect(() => {
    if (!token) {
      return;
    }

    setAuthToken(token);
    setLoading(true);

    getActors()
      .then((data) => {
        setActors(data);
      })
      .catch((error) => {
        console.error("Failed to load actors:", error);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  function handleLogin(newToken: string) {
    sessionStorage.setItem("decypher_token", newToken);
    setAuthToken(newToken);
    setToken(newToken);
    setPage("dashboard");
  }

  function handleLogout() {
    sessionStorage.removeItem("decypher_token");
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
    if (selectedActor) {
      setPage("graph");
    }
  }

  if (!token) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">D</div>

          <div>
            <h1>DeCypher</h1>
            <span>Threat Intelligence</span>
          </div>
        </div>

        <nav>
          <button
            className={
              page === "dashboard"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => setPage("dashboard")}
          >
            Dashboard
          </button>

          <button
            className={
              page === "search"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => setPage("search")}
          >
            Investigation Search
          </button>

          {selectedActor && (
            <button
              className={
                page === "actor"
                  ? "nav-item active"
                  : "nav-item"
              }
              onClick={() => setPage("actor")}
            >
              Actor Investigation
            </button>
          )}

          {selectedActor && (
            <button
              className={
                page === "graph"
                  ? "nav-item active"
                  : "nav-item"
              }
              onClick={() => setPage("graph")}
            >
              Graph Explorer
            </button>
          )}
        </nav>

        <div className="sidebar-bottom">
          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-content">
        {page === "dashboard" && (
          <>
            <header className="page-header">
              <div>
                <p className="eyebrow">
                  THREAT INTELLIGENCE PLATFORM
                </p>

                <h2>Investigation Dashboard</h2>

                <p>
                  Correlate actors, infrastructure, wallets,
                  handles and evidence.
                </p>
              </div>

              <button
                className="primary-button"
                onClick={() => setPage("search")}
              >
                Start Investigation
              </button>
            </header>

            {loading ? (
              <div className="loading">
                Loading intelligence data...
              </div>
            ) : (
              <>
                <section className="stats-grid">
                  <div className="stat-card">
                    <span>Total Actors</span>
                    <strong>{actors.length}</strong>
                  </div>

                  <div className="stat-card">
                    <span>High Risk</span>

                    <strong>
                      {
                        actors.filter(
                          (actor) =>
                            actor.risk_category === "high" ||
                            actor.risk_category === "critical",
                        ).length
                      }
                    </strong>
                  </div>

                  <div className="stat-card">
                    <span>Average Confidence</span>

                    <strong>
                      {actors.length > 0
                        ? `${(
                            (actors.reduce(
                              (sum, actor) =>
                                sum +
                                Number(
                                  actor.confidence_score || 0,
                                ),
                              0,
                            ) /
                              actors.length) *
                            100
                          ).toFixed(1)}%`
                        : "0%"}
                    </strong>
                  </div>
                </section>

                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <p className="eyebrow">
                        CORRELATED ACTORS
                      </p>

                      <h3>Recent Intelligence</h3>
                    </div>

                    <button
                      className="secondary-button"
                      onClick={() => setPage("search")}
                    >
                      View all
                    </button>
                  </div>

                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          <th>Actor ID</th>
                          <th>Primary Handle</th>
                          <th>Risk Category</th>
                          <th>Confidence</th>
                          <th>Last Active</th>
                        </tr>
                      </thead>

                      <tbody>
                        {actors.slice(0, 10).map((actor) => (
                          <tr
                            key={actor.actor_id}
                            className="clickable-row"
                            onClick={() =>
                              openActor(actor.actor_id)
                            }
                          >
                            <td>{actor.actor_id}</td>

                            <td>
                              {actor.primary_handle}
                            </td>

                            <td>
                              <span className="risk-badge">
                                {actor.risk_category}
                              </span>
                            </td>

                            <td>
                              {(
                                Number(
                                  actor.confidence_score,
                                ) * 100
                              ).toFixed(1)}
                              %
                            </td>

                            <td>
                              {actor.last_active}
                            </td>
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

        {page === "search" && (
          <SearchPage
            onSelectActor={openActor}
          />
        )}

        {page === "actor" && selectedActor && (
          <ActorPage
            actorId={selectedActor}
            onBack={() => setPage("search")}
            onGraph={openGraph}
          />
        )}

        {page === "graph" && selectedActor && (
          <GraphPage
            actorId={selectedActor}
            onBack={() => setPage("actor")}
          />
        )}
      </main>
    </div>
  );
}

export default App;