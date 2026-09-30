import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, BarChart3, GitBranch, LayoutDashboard, LogOut, Moon, Search, ShieldCheck, Sun, Target } from "lucide-react";
import "./App.css";
import "./dashboard.css";
import { getActors, getAllCorrelations, setAuthToken } from "./api/client";
import ExportMenu from "./components/export/ExportMenu";
import NotificationBell, { type AppNotification } from "./components/notifications/NotificationBell";
import LoginPage from "./pages/LoginPage";
import SearchPage from "./pages/SearchPage";
import ActorPage from "./pages/ActorPage";
import GraphPage from "./pages/GraphPage";
import ChatAssistant from "./components/ai/ChatAssistant";

type Page = "dashboard" | "search" | "actor" | "graph";
type NavItem = { id: Page; label: string; icon: typeof LayoutDashboard };
interface ActorSummary { actor_id: string; primary_handle: string; risk_category: string; confidence_score: number; priority_score: number; associated_handles: string[]; last_active: string; }
function priorityClass(score: number) { if (score >= 85) return "critical"; if (score >= 70) return "high"; if (score >= 50) return "medium"; return "low"; }

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("decypher_token") || "");
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedActor, setSelectedActor] = useState("");
  const [actors, setActors] = useState<ActorSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("decypher_theme") as "dark" | "light") || "dark");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("decypher_theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!token) return;
    setAuthToken(token); setLoadError("");
    Promise.allSettled([getActors(), getAllCorrelations()])
      .then(([actorsResult, correlationsResult]) => {
        if (actorsResult.status === "rejected") {
          console.error("Failed to load actors:", actorsResult.reason);
          setActors([]);
          setLoadError("Unable to load actor intelligence from the backend.");
          return;
        }

        const actorRows = actorsResult.value;
        const correlationRows =
          correlationsResult.status === "fulfilled"
            ? correlationsResult.value
            : { results: [] };

        if (correlationsResult.status === "rejected") {
          console.error("Failed to load correlations; showing actor data without correlation refresh:", correlationsResult.reason);
          setLoadError("Actor data loaded, but live correlation refresh is unavailable.");
        }

        const priorities = new Map(
          correlationRows.results.map((item) => [
            item.candidate_actor,
            item.priority?.score ?? 0,
          ]),
        );
        const mergedActors = actorRows
          .map((actor) => ({
            ...actor,
            priority_score:
              priorities.get(actor.actor_id) ?? actor.priority_score ?? 0,
          }))
          .sort(
            (a, b) =>
              Number(b.priority_score || 0) -
                Number(a.priority_score || 0) ||
              Number(b.confidence_score || 0) -
                Number(a.confidence_score || 0) ||
              a.actor_id.localeCompare(b.actor_id),
          );

        setActors(mergedActors);

        const urgent = mergedActors.filter(
          (actor) => Number(actor.priority_score || 0) >= 70,
        ).length;
        const topActors = mergedActors.slice(0, 3);

        setNotifications([
          {
            id: "feed-ready",
            title: "Intelligence feed synchronized",
            message: `${mergedActors.length} actor profiles are indexed and ranked by operational priority.`,
            time: "Just now",
            type: "success",
          },
          ...(urgent
            ? [
                {
                  id: "priority-update",
                  title: "Priority queue updated",
                  message: `${urgent} actors are currently at high or critical priority.`,
                  time: "Just now",
                  type: "warning" as const,
                },
              ]
            : []),
          ...topActors.map((actor, index) => ({
            id: `priority-actor-${actor.actor_id}`,
            title: `Priority #${index + 1} · ${actor.actor_id}`,
            message: `${actor.primary_handle} is ranked at ${Number(actor.priority_score || 0)}/100.`,
            time: "Just now",
            type:
              Number(actor.priority_score || 0) >= 70
                ? ("warning" as const)
                : ("info" as const),
          })),
        ]);
      })
      .finally(() => setLoading(false));
  }, [token]);

  function handleLogin(newToken: string) { sessionStorage.setItem("decypher_token", newToken); setAuthToken(newToken); setToken(newToken); setPage("dashboard"); }
  function handleLogout() { sessionStorage.removeItem("decypher_token"); setAuthToken(""); setToken(""); setActors([]); setSelectedActor(""); setPage("dashboard"); }
  function openActor(actorId: string) { setSelectedActor(actorId); setPage("actor"); }
  function markAllRead() { setNotifications((items) => items.map((item) => ({ ...item, read: true }))); }
  async function handleExport(format: string) { console.info(`Exported ${format}`); }

  const highPriorityCount = actors.filter((a) => Number(a.priority_score || 0) >= 70).length;
  const averageConfidence = actors.length ? actors.reduce((sum, a) => sum + Number(a.confidence_score || 0), 0) / actors.length * 100 : 0;
  const priorityStats = useMemo(() => { const scores = actors.map((a) => Number(a.priority_score || 0)); const average = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0; return { average, urgent: scores.filter((s) => s >= 70).length }; }, [actors]);
  const navItems: NavItem[] = [{ id: "dashboard", label: "Dashboard", icon: LayoutDashboard }, { id: "search", label: "Investigation Search", icon: Search }];
  if (selectedActor) navItems.push({ id: "actor", label: "Actor Investigation", icon: ShieldCheck }, { id: "graph", label: "Graph Explorer", icon: GitBranch });
  if (!token) return <LoginPage onLogin={handleLogin} />;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">D</div><div className="brand-copy"><h1>DeCypher</h1><span>Threat Intelligence</span></div></div>
      <div className="sidebar-label">Workspace</div>
      <nav aria-label="Primary navigation">{navItems.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item${page === id ? " active" : ""}`} onClick={() => setPage(id)}><span className="nav-icon"><Icon size={16} strokeWidth={1.8} /></span><span className="nav-label">{label}</span></button>)}</nav>
      <div className="sidebar-status"><span className="status-dot" /><div><strong>System online</strong><small>Evidence correlation engine ready</small></div></div>
      <div className="sidebar-bottom"><div className="sidebar-meta"><Activity size={13} /><span>LIVE WORKSPACE</span></div><button className="theme-toggle" onClick={() => setTheme((value) => value === "dark" ? "light" : "dark")} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}><span className="theme-toggle-icon">{theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}</span><span>{theme === "dark" ? "Light mode" : "Dark mode"}</span></button><button className="logout-button" onClick={handleLogout}><LogOut size={15} /><span>Sign out</span></button></div>
    </aside>

    <main className="main-content"><div className="content-frame">
      {page === "dashboard" && <section className="dashboard-view">
        <header className="page-header dashboard-header"><div><div className="eyebrow">THREAT INTELLIGENCE PLATFORM</div><h2>Investigation Dashboard</h2><p>Prioritize actors by risk, evidence strength, recency and cross-source correlation.</p></div><div className="dashboard-actions"><ExportMenu onExport={handleExport} /><NotificationBell notifications={notifications} onMarkAllRead={markAllRead} /><button className="primary-button" onClick={() => setPage("search")}><Search size={15} /> Start Investigation</button></div></header>
        {loadError && <div className="error">{loadError}</div>}
        {loading ? <div className="loading">Calculating evidence priorities…</div> : <>
          <section className="stats-grid">
            <div className="stat-card stat-blue"><span>Total Actors</span><strong>{actors.length}</strong><small>Indexed identities</small><LayoutDashboard size={18} /></div>
            <div className="stat-card stat-red"><span>Priority ≥ High</span><strong>{priorityStats.urgent}</strong><small>Actors needing attention</small><AlertTriangle size={18} /></div>
            <div className="stat-card stat-green"><span>Average Priority</span><strong>{priorityStats.average.toFixed(0)}</strong><small>Derived triage score / 100</small><Target size={18} /></div>
            <div className="stat-card stat-purple"><span>Average Confidence</span><strong>{averageConfidence.toFixed(1)}%</strong><small>{highPriorityCount} high/critical priority actors</small><ShieldCheck size={18} /></div>
          </section>
          <section className="dashboard-grid">
            <div className="panel actors-panel"><div className="panel-header"><div><div className="eyebrow">PRIORITY QUEUE</div><h3>Actors ranked by operational priority</h3><p className="panel-meta">{actors.length} indexed actors · highest priority first</p></div><button className="secondary-button" onClick={() => setPage("search")}>Open investigation search <span aria-hidden="true">→</span></button></div>
              <div className="table-container priority-queue-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Actor</th>
                      <th>Primary handle</th>
                      <th>Risk</th>
                      <th>Priority</th>
                      <th>Confidence</th>
                      <th>Last active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {actors.map((actor, index) => {
                      const score = Number(actor.priority_score || 0);
                      return (
                        <tr
                          key={actor.actor_id}
                          className="clickable-row"
                          onClick={() => openActor(actor.actor_id)}
                        >
                          <td className="queue-rank">{String(index + 1).padStart(3, "0")}</td>
                          <td className="actor-id">{actor.actor_id}</td>
                          <td>{actor.primary_handle}</td>
                          <td>
                            <span className={`risk-badge ${String(actor.risk_category || "").toLowerCase()}`}>
                              {actor.risk_category}
                            </span>
                          </td>
                          <td>
                            <span className={`priority-pill ${priorityClass(score)}`}>
                              <span>{score}</span> / 100
                            </span>
                          </td>
                          <td>{(Number(actor.confidence_score || 0) * 100).toFixed(1)}%</td>
                          <td>{actor.last_active || "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
            <aside className="priority-panel"><div className="priority-panel-top"><div><div className="eyebrow">TRIAGE MODEL</div><h3>Priority score</h3></div><BarChart3 size={18} /></div><div className="priority-score-big">{priorityStats.average.toFixed(0)}<span>/100</span></div><p>Transparent operational ranking. {highPriorityCount} actors are currently at high or critical priority. This is a triage score, not a probability of identity.</p><div className="priority-legend"><div><span className="legend-swatch critical" />Critical <b>85–100</b></div><div><span className="legend-swatch high" />High <b>70–84</b></div><div><span className="legend-swatch medium" />Medium <b>50–69</b></div><div><span className="legend-swatch low" />Low <b>0–49</b></div></div></aside>
          </section>
        </>}
      </section>}
      {page === "search" && <SearchPage onSelectActor={openActor} />}
      {page === "actor" && selectedActor && <ActorPage actorId={selectedActor} onBack={() => setPage("search")} onGraph={() => setPage("graph")} />}
      {page === "graph" && selectedActor && <GraphPage actorId={selectedActor} onBack={() => setPage("actor")} />}
    </div></main>
    <ChatAssistant actorId={selectedActor || undefined} />
  </div>;
}
export default App;
