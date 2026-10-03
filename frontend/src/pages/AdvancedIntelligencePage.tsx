
import { useEffect, useState } from "react";
import {
  getAdvancedAlerts,
  getCollectionStatus,
  getCollectionSources,
  getCalibrationEvaluation,
  getGraphAnomalyLeaderboard,
  runStylometryDiscovery,
  runEvidenceAblation,
  getActorEntityLinks,
  compareMedia,
  fingerprintMedia,
  createCollectionSource,
  runHistoricalCaseValidation,
  inspectTor,
  getMerkleStatus,
  type AdvancedAlert,
  type CollectionStatus,
  type CollectionSource,
  type GraphAnomalyResult,
} from "../api/client";

interface Props { actorId?: string; }

export default function AdvancedIntelligencePage({ actorId }: Props) {
  const [collection, setCollection] = useState<CollectionStatus | null>(null);
  const [sources, setSources] = useState<CollectionSource[]>([]);
  const [discovery, setDiscovery] = useState<any[]>([]);
  const [calibration, setCalibration] = useState<Record<string, any> | null>(null);
  const [anomalies, setAnomalies] = useState<GraphAnomalyResult[]>([]);
  const [alerts, setAlerts] = useState<AdvancedAlert[]>([]);
  const [ablation, setAblation] = useState<any>(null);
  const [disabled, setDisabled] = useState<string[]>([]);
  const [entityLinks, setEntityLinks] = useState<any[]>([]);
  const [mediaA, setMediaA] = useState("");
  const [mediaB, setMediaB] = useState("");
  const [mediaResult, setMediaResult] = useState<Record<string, any> | null>(null);
  const [merkle, setMerkle] = useState<Record<string, any> | null>(null);
  const [torUrl, setTorUrl] = useState("");
  const [torResult, setTorResult] = useState<Record<string, any> | null>(null);
  const [caseManifest, setCaseManifest] = useState("");
  const [caseResult, setCaseResult] = useState<Record<string, any> | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [sourceKind, setSourceKind] = useState<"json" | "rss" | "html" | "tor_http">("rss");
  const [sourceUrl, setSourceUrl] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.allSettled([
      getCollectionStatus(),
      getCollectionSources(),
      getCalibrationEvaluation(60),
      getGraphAnomalyLeaderboard(10),
      getAdvancedAlerts(),
      getMerkleStatus(),
    ]).then(([c, s, cal, graph, a, m]) => {
      if (c.status === "fulfilled") setCollection(c.value);
      if (s.status === "fulfilled") setSources(s.value);
      if (cal.status === "fulfilled") setCalibration(cal.value);
      if (graph.status === "fulfilled") setAnomalies(graph.value.results);
      if (a.status === "fulfilled") setAlerts(a.value);
      if (m.status === "fulfilled") setMerkle(m.value);
    });
  }, []);

  useEffect(() => {
    if (!actorId) return;
    getActorEntityLinks(actorId).then(setEntityLinks).catch(() => setEntityLinks([]));
  }, [actorId]);

  useEffect(() => {
    const token = sessionStorage.getItem("decypher_token");
    if (!token) return;
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
    const apiUrl = new URL(apiBase);
    const protocol = apiUrl.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${apiUrl.host}/alerts/ws`);
    socket.onopen = () => socket.send(token);
    socket.onmessage = (event) => {
      try {
        const alert = JSON.parse(event.data) as AdvancedAlert;
        if (alert.id) {
          setAlerts((current) => [...current.filter((item) => item.id !== alert.id), alert].slice(-25));
        }
      } catch {
        // Ignore malformed live messages.
      }
    };
    return () => socket.close();
  }, []);

  async function discover() {
    setLoading(true);
    try {
      const result = await runStylometryDiscovery(100, actorId);
      setDiscovery(result.results);
    } finally {
      setLoading(false);
    }
  }

  async function ablate() {
    if (!actorId) return;
    setAblation(await runEvidenceAblation(actorId, disabled));
  }

  async function uploadImage(
    event: React.ChangeEvent<HTMLInputElement>,
    slot: "a" | "b",
  ) {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const dataUrl = String(reader.result || "");
      const id = `image-${slot}-${Date.now()}`;
      const result = await fingerprintMedia(id, dataUrl, "investigator_upload", actorId);
      if (slot === "a") setMediaA(id);
      else setMediaB(id);
      setMediaResult(result);
    };
    reader.readAsDataURL(file);
  }

  async function compareImages() {
    if (!mediaA || !mediaB) return;
    setMediaResult(await compareMedia(mediaA, mediaB));
  }

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">ADVANCED INTELLIGENCE</div>
          <h2>Evidence & Discovery Lab</h2>
          <p>
            Continuous collection, automatic stylometry discovery, calibration, entity linkage,
            media correlation, graph analytics and live alerting.
          </p>
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="eyebrow">EVIDENCE BLOCKCHAIN / MERKLE</div>
          <h3 style={{ marginTop: 8 }}>Tamper-evident evidence blocks</h3>
          <div style={{ fontFamily: "monospace", fontSize: 12 }}>
            {merkle ? `${merkle.block_count || 0} blocks · ${merkle.entry_count || 0} entries · valid=${String(merkle.valid)}` : "Loading Merkle verification…"}
          </div>
          <p style={{ opacity: 0.6, fontSize: 12, marginTop: 8 }}>
            SHA-256 evidence chain + Merkle blocks. Optional external blockchain anchoring remains deployment-configurable.
          </p>
        </div>
        <div className="card">
          <div className="eyebrow">TOR INTELLIGENCE</div>
          <h3 style={{ marginTop: 8 }}>Allowlisted hidden-service inspection</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={torUrl} onChange={(e) => setTorUrl(e.target.value)} placeholder="https://example.onion/" style={{ flex: 1 }} />
            <button className="secondary-button" onClick={async () => { if (!torUrl) return; setTorResult(await inspectTor(torUrl)); }}>Inspect</button>
          </div>
          {torResult && <pre style={{ whiteSpace: "pre-wrap", fontSize: 11, marginTop: 10, opacity: 0.75 }}>{JSON.stringify(torResult, null, 2)}</pre>}
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="eyebrow">CONTINUOUS COLLECTION</div>
          <h3 style={{ marginTop: 8 }}>Marketplace / forum / deep-web connectors</h3>
          <p style={{ opacity: 0.65, fontSize: 13 }}>
            Registered sources are polled by Celery + Redis. Tor sources require an explicit
            .onion allowlist and SOCKS5 proxy.
          </p>
          <div style={{ fontFamily: "monospace", marginTop: 12 }}>
            {collection
              ? `${collection.enabled_sources}/${collection.sources} sources enabled · ${collection.poll_interval_minutes} min dispatcher`
              : "Loading…"}
          </div>
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            <input value={sourceName} onChange={(e) => setSourceName(e.target.value)} placeholder="Source name" />
            <select value={sourceKind} onChange={(e) => setSourceKind(e.target.value as any)}>
              <option value="rss">RSS</option><option value="json">JSON</option><option value="html">HTML</option><option value="tor_http">Tor HTTP</option>
            </select>
            <input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="https://feed.example" />
            <button className="secondary-button" onClick={async () => {
              if (!sourceName || !sourceUrl) return;
              const created = await createCollectionSource({ name: sourceName, kind: sourceKind, url: sourceUrl, actor_id: actorId || null });
              setSources((current) => [...current, created]);
              setSourceName("");
              setSourceUrl("");
            }}>Register source</button>
          </div>
          <div style={{ marginTop: 12 }}>
            {sources.map((source) => (
              <div key={source.id} style={{ padding: "7px 0", borderBottom: "1px solid rgba(255,255,255,.06)" }}>
                <strong>{source.name}</strong>{" "}
                <span style={{ opacity: 0.55 }}>{source.kind} · {source.last_status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="eyebrow">LIVE ALERT PIPELINE</div>
          <h3 style={{ marginTop: 8 }}>WebSocket alert stream</h3>
          <p style={{ opacity: 0.65, fontSize: 13 }}>
            New collection, Tor and investigation events are persisted and streamed to the UI.
          </p>
          {alerts.slice(-6).reverse().map((alert) => (
            <div key={alert.id} style={{ padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,.06)" }}>
              <strong>{alert.title}</strong>
              <div style={{ opacity: 0.6, fontSize: 12 }}>{alert.message}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="eyebrow">AUTOMATIC STYLOMETRY DISCOVERY</div>
          <h3 style={{ marginTop: 8 }}>Candidate handle discovery</h3>
          <button className="primary-button" onClick={discover} disabled={loading}>
            {loading ? "Analyzing…" : "Discover candidates"}
          </button>
          <div style={{ marginTop: 12 }}>
            {discovery.slice(0, 8).map((item: any, index) => (
              <div key={index} style={{ padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,.06)", fontFamily: "monospace", fontSize: 12 }}>
                {item.handle_a} ↔ {item.handle_b} · {(Number(item.similarity || 0) * 100).toFixed(1)}%
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="eyebrow">CONFIDENCE CALIBRATION</div>
          <h3 style={{ marginTop: 8 }}>Synthetic evaluation diagnostics</h3>
          {calibration && (
            <>
              <div style={{ fontFamily: "monospace", marginTop: 10 }}>
                Brier {String(calibration.brier_score)} · ECE {String(calibration.expected_calibration_error)}
              </div>
              <div style={{ marginTop: 12 }}>
                {(Array.isArray(calibration.bins) ? calibration.bins : []).map((bin: any) => (
                  <div key={`${bin.lower}-${bin.upper}`} style={{ display: "grid", gridTemplateColumns: "80px 1fr", gap: 10, padding: "5px 0" }}>
                    <span>{Math.round(bin.lower * 100)}–{Math.round(bin.upper * 100)}%</span>
                    <div style={{ background: "rgba(255,255,255,.06)", height: 8, borderRadius: 8 }}>
                      <div style={{ width: `${Math.max(2, Number(bin.empirical_match_rate || 0) * 100)}%`, height: "100%", background: "#74c0fc", borderRadius: 8 }} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="eyebrow">INTERACTIVE EVIDENCE ABLATION</div>
          <h3 style={{ marginTop: 8 }}>Disable signals and recompute</h3>
          {!actorId ? (
            <div style={{ opacity: 0.6 }}>Open an actor investigation to use ablation.</div>
          ) : (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8, marginTop: 10 }}>
                {["wallet_reuse", "infrastructure_reuse", "tls_reuse", "banner_match", "descriptor_timing", "stylometry"].map((signal) => (
                  <label key={signal} style={{ fontSize: 12 }}>
                    <input
                      type="checkbox"
                      checked={disabled.includes(signal)}
                      onChange={() => setDisabled((current) => current.includes(signal) ? current.filter((x) => x !== signal) : [...current, signal])}
                    />{" "}
                    {signal.replaceAll("_", " ")}
                  </label>
                ))}
              </div>
              <button className="secondary-button" style={{ marginTop: 12 }} onClick={ablate}>Recompute ablated score</button>
              {ablation && (
                <div style={{ marginTop: 12, fontFamily: "monospace" }}>
                  baseline {ablation.baseline_score} → ablated {ablation.ablated_score} · Δ {ablation.delta}
                </div>
              )}
            </>
          )}
        </div>

        <div className="card">
          <div className="eyebrow">REAL-WORLD ENTITY LINKAGE</div>
          <h3 style={{ marginTop: 8 }}>Technical entity associations</h3>
          <p style={{ opacity: 0.6, fontSize: 12 }}>
            Links external handles, wallets, PGP fingerprints and infrastructure domains to the selected actor using explicit match evidence.
          </p>
          {entityLinks.slice(0, 8).map((item: any, index) => (
            <div key={index} style={{ padding: "7px 0", borderBottom: "1px solid rgba(255,255,255,.06)", fontFamily: "monospace", fontSize: 12 }}>
              {item.entity_type}: {item.canonical_value} · {Math.round(Number(item.score) * 100)}%
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="eyebrow">HISTORICAL CASE VALIDATION</div>
          <h3 style={{ marginTop: 8 }}>Public-case reconstruction harness</h3>
          <p style={{ opacity: 0.6, fontSize: 12 }}>
            Paste a documented case manifest using the handle pair and expected-match schema.
          </p>
          <textarea value={caseManifest} onChange={(e) => setCaseManifest(e.target.value)} rows={7} style={{ width: "100%" }} placeholder='[{"case_id":"case-1","handle_a":"...","handle_b":"...","expected_same_actor":true}]' />
          <button className="secondary-button" style={{ marginTop: 8 }} onClick={async () => {
            try { setCaseResult(await runHistoricalCaseValidation(JSON.parse(caseManifest))); }
            catch (error) { setCaseResult({ error: String(error) }); }
          }}>Validate manifest</button>
          {caseResult && <pre style={{ whiteSpace: "pre-wrap", fontSize: 11, marginTop: 10, opacity: 0.75 }}>{JSON.stringify(caseResult, null, 2)}</pre>}
        </div>
        <div className="card">
          <div className="eyebrow">CROSS-MODAL IMAGE CORRELATION</div>
          <h3 style={{ marginTop: 8 }}>Perceptual hashing</h3>
          <div style={{ display: "grid", gap: 8 }}>
            <label>Evidence image A <input type="file" accept="image/*" onChange={(e) => uploadImage(e, "a")} /></label>
            <label>Evidence image B <input type="file" accept="image/*" onChange={(e) => uploadImage(e, "b")} /></label>
            <button className="secondary-button" onClick={compareImages} disabled={!mediaA || !mediaB}>Compare images</button>
            {mediaResult && <pre style={{ whiteSpace: "pre-wrap", fontSize: 11, opacity: 0.75 }}>{JSON.stringify(mediaResult, null, 2)}</pre>}
          </div>
        </div>

        <div className="card">
          <div className="eyebrow">ADVANCED GRAPH ANOMALY</div>
          <h3 style={{ marginTop: 8 }}>Population-relative structural outliers</h3>
          {anomalies.slice(0, 8).map((item) => (
            <div key={item.actor_id} style={{ padding: "7px 0", display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,.06)" }}>
              <span>{item.actor_id}</span>
              <span style={{ fontFamily: "monospace" }}>{item.anomaly_score.toFixed(1)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
