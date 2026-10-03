const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface Actor { actor_id: string; primary_handle: string; risk_category: string; confidence_score: number; priority_score: number; associated_handles: string[]; last_active: string; }
export interface SearchResult { type: string; id: string; matched_value: string; risk_category?: string; }
export interface SearchResponse { query: string; total_matches: number; results: SearchResult[]; }
let authToken = "";
export function setAuthToken(token: string) { authToken = token; }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { ...(options.headers || {}), ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) } });
  if (!response.ok) {
    const error = new Error((await response.text()) || `API error: ${response.status}`) as Error & { status: number };
    error.status = response.status;
    throw error;
  }
  return response.json();
}

async function triggerBrowserDownload(blob: Blob, filename: string): Promise<void> {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  // Keep the object URL alive through the browser's download hand-off.
  // Revoking it synchronously can cancel or destabilize some Chromium/WebKit
  // download flows.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${API_BASE}/auth/token`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body });
  if (!response.ok) throw new Error("Invalid username or password");
  const data = await response.json();
  setAuthToken(data.access_token);
  return data.access_token;
}

export async function downloadExport(format: "pdf" | "csv" | "json"): Promise<void> {
  const endpoint = format === "pdf" ? "report" : format;
  const response = await fetch(`${API_BASE}/export/${endpoint}`, {
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  });
  if (!response.ok) throw new Error((await response.text()) || `Export failed: ${response.status}`);

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || `decypher_export.${format}`;

  await triggerBrowserDownload(blob, filename);
}

export async function downloadActorReport(
  actorId: string,
  graphImage?: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/export/actor/${encodeURIComponent(actorId)}/report`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authToken
          ? { Authorization: `Bearer ${authToken}` }
          : {}),
      },
      body: JSON.stringify({
        graph_image: graphImage || null,
      }),
    },
  );
  if (!response.ok) {
    throw new Error(
      (await response.text()) ||
        `Actor PDF export failed: ${response.status}`,
    );
  }

  const blob = await response.blob();
  const disposition =
    response.headers.get("Content-Disposition") || "";
  const match =
    disposition.match(/filename="?([^"]+)"?/i);
  const filename =
    match?.[1] ||
    `actor_${actorId}_report.pdf`;

  await triggerBrowserDownload(blob, filename);
}

export async function downloadActorExport(
  actorId: string,
  format: "pdf" | "csv" | "json",
): Promise<void> {
  const endpoint = format === "pdf" ? "report" : format;
  const response = await fetch(
    `${API_BASE}/export/actor/${encodeURIComponent(actorId)}/${endpoint}`,
    {
      headers: authToken
        ? { Authorization: `Bearer ${authToken}` }
        : {},
    },
  );
  if (!response.ok) {
    throw new Error(
      (await response.text()) ||
        `Actor export failed: ${response.status}`,
    );
  }

  const blob = await response.blob();
  const disposition =
    response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename =
    match?.[1] ||
    `actor_${actorId}_export.${format}`;

  await triggerBrowserDownload(blob, filename);
}

export function getActors(): Promise<Actor[]> { return request<Actor[]>(`/actors`); }
export function getActor(actorId: string) { return request(`/actors/${encodeURIComponent(actorId)}`); }
export function getActorEvidence(
  actorId: string,
  start?: string,
  end?: string,
) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const query = params.toString();
  return request(
    `/actors/${encodeURIComponent(actorId)}/evidence${query ? `?${query}` : ""}`,
  );
}

export interface GraphNode { id: string; label: string; name: string; category: string; type: string; properties?: Record<string, unknown>; }
export interface GraphLink { source: string; target: string; relation: string; }
export interface GraphPayload { nodes: GraphNode[]; links: GraphLink[]; }
export function getActorGraph(actorId: string): Promise<GraphPayload> { return request<GraphPayload>(`/actors/${encodeURIComponent(actorId)}/graph`); }

export interface TemporalEvent {
  id: number;
  event_key: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  timestamp: string;
  source: string;
  payload: Record<string, unknown>;
}
export interface ActorTimeline {
  actor_id: string;
  total_events: number;
  event_types: Record<string, number>;
  events: TemporalEvent[];
  methodology: string;
}
export interface GraphAnomalyResult {
  actor_id: string;
  anomaly_score: number;
  level: string;
  features: Record<string, number>;
  feature_percentiles: Record<string, number>;
  feature_tail_scores: Record<string, number>;
  contributing_features: Array<{
    feature: string;
    feature_value: number;
    population_percentile: number;
    tail_score: number;
  }>;
  feature_weights: Record<string, number>;
  methodology: string;
}
export function getActorTimeline(actorId: string, limit = 250): Promise<ActorTimeline> {
  return request<ActorTimeline>(`/analytics/actors/${encodeURIComponent(actorId)}/timeline?limit=${limit}`);
}
export function getActorGraphAnomaly(actorId: string): Promise<GraphAnomalyResult> {
  return request<GraphAnomalyResult>(`/analytics/actors/${encodeURIComponent(actorId)}/graph-anomaly`);
}
export function getGraphAnomalyLeaderboard(limit = 25): Promise<{ total_actors: number; results: GraphAnomalyResult[]; limit: number }> {
  return request(`/analytics/graph-anomalies?limit=${limit}`);
}

export interface SourceReliability {
  source: string;
  prior: number;
  posterior: number;
  review_count: number;
  confirmed_reviews: number;
  false_positive_reviews: number;
  review_coverage: number;
  multiplier: number;
  basis: string;
}

export interface CounterfactualScenario {
  removed_signal: string;
  baseline_score: number;
  without_score: number;
  delta: number;
  absolute_impact: number;
  remaining_signal_count: number;
  remaining_weight: number;
  interpretation: string;
}

export interface CounterfactualAnalysis {
  available: boolean;
  baseline_evidence_score: number;
  scenarios: CounterfactualScenario[];
  note: string;
}

export interface CorrelationSignal {
  type: string;
  confidence: number;
  description: string;
  weight: number;
  details?: {
    handle_a?: string;
    handle_b?: string;
    is_same_author?: boolean;
    threshold_used?: number;
    shared_markers?: string[];
    domain_routing?: Record<string, number>;
    contradiction?: Record<string, unknown> | null;
    source_reliability?: Record<string, SourceReliability>;
  };
}
export interface PriorityResult { score: number; level: string; components: { risk_severity: number; correlation: number; evidence_confidence: number; recency: number; evidence_coverage: number; }; weights: Record<string, number>; }
export interface CorrelationResult {
  candidate_actor: string;
  primary_handle: string;
  overall_confidence: number;
  risk_level: string;
  signals: CorrelationSignal[];
  signal_count: number;
  available_weight: number;
  interpretation: string;
  deconfliction?: Record<string, unknown> | null;
  priority?: PriorityResult;
  counterfactual?: CounterfactualAnalysis;
  source_reliability?: Record<string, SourceReliability>;
}
export function getActorCorrelation(actorId: string, handleA?: string, handleB?: string): Promise<CorrelationResult> {
  const params = new URLSearchParams();
  if (handleA) params.set("handle_a", handleA);
  if (handleB) params.set("handle_b", handleB);
  const query = params.toString();
  return request<CorrelationResult>(`/correlation/actor/${encodeURIComponent(actorId)}${query ? `?${query}` : ""}`);
}
export function getActorCounterfactual(actorId: string, handleA?: string, handleB?: string) {
  const params = new URLSearchParams();
  if (handleA) params.set("handle_a", handleA);
  if (handleB) params.set("handle_b", handleB);
  const query = params.toString();
  return request<Pick<CorrelationResult, "candidate_actor" | "counterfactual" | "source_reliability">>(
    `/correlation/actor/${encodeURIComponent(actorId)}/counterfactual${query ? `?${query}` : ""}`,
  );
}
export function getAllCorrelations(): Promise<{ results: CorrelationResult[] }> { return request<{ results: CorrelationResult[] }>(`/correlation/actors`); }
export function refreshActorCorrelation(actorId: string, handleA?: string, handleB?: string): Promise<CorrelationResult> {
  const params = new URLSearchParams();
  if (handleA) params.set("handle_a", handleA);
  if (handleB) params.set("handle_b", handleB);
  const query = params.toString();
  return request<CorrelationResult>(`/correlation/actor/${encodeURIComponent(actorId)}/refresh${query ? `?${query}` : ""}`, { method: "POST" });
}
export function refreshAllCorrelations(): Promise<{ results: CorrelationResult[] }> {
  return request<{ results: CorrelationResult[] }>("/correlation/actors/refresh", { method: "POST" });
}
export function searchActors(query: string): Promise<SearchResponse> { return request<SearchResponse>(`/search?q=${encodeURIComponent(query)}`); }


export interface ChatMessage { role: "user" | "assistant"; content: string; }
export interface ChatResponse { answer: string; provider: string; model: string; scope: string; actor_id?: string; }
export function chatWithAI(message: string, actorId?: string, history: ChatMessage[] = []): Promise<ChatResponse> {
  return request<ChatResponse>("/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, actor_id: actorId || null, history }),
  });
}


export interface BehavioralProfile {
  actor_id: string;
  profile_version: string;
  generated_at?: string;
  source_fingerprint?: string;
  coverage: {
    score: number;
    available_dimensions: number;
    total_dimensions: number;
    dimensions: Record<string, boolean>;
  };
  summary: {
    linked_handle_count: number;
    marketplace_count: number;
    wallet_count: number;
    pgp_key_count: number;
    trust_link_count: number;
    infrastructure_observation_count: number;
    post_count: number;
  };
  dimensions: {
    linguistic: {
      available: boolean;
      sample_post_count: number;
      profiled_handle_count: number;
      engine_status: string;
      fallback_used: boolean;
      features: Record<string, number>;
      per_handle: Array<{
        handle: string;
        post_count: number;
        features: Record<string, number>;
        top_terms: Array<{ term: string; count: number }>;
      }>;
      cross_handle_consistency: {
        available: boolean;
        mean_similarity: number | null;
        comparisons: number;
        engine_status: string;
        fallback_used: boolean;
        interpretation?: string;
      };
    };
    temporal_lifecycle: {
      available: boolean;
      first_observed?: string | null;
      last_observed?: string | null;
      account_age_days?: number | null;
      observed_span_days?: number | null;
      days_since_last_seen?: number | null;
      handle_timeline: Array<{
        handle: string;
        marketplace?: string | null;
        status?: string | null;
        first_seen?: string | null;
        last_seen?: string | null;
        active_window_days?: number | null;
      }>;
      status_distribution: Record<string, number>;
      overlapping_handle_windows: number;
      inter_handle_gap_days: number[];
      has_post_timestamps: boolean;
    };
    operational: {
      available: boolean;
      marketplace_count: number;
      marketplaces: Array<{ name: string; handle_count: number }>;
      wallet_count: number;
      unique_wallet_count: number;
      within_actor_wallet_reuse_count: number;
      cross_actor_shared_wallet_count: number;
      pgp_key_count: number;
      pgp_reuse_across_other_handles_count: number;
    };
    interaction: {
      available: boolean;
      trust_link_count: number;
      outgoing_count: number;
      incoming_count: number;
      distinct_counterparty_handles: number;
      relationship_types: Record<string, number>;
      average_confidence: number | null;
      scope_note: string;
    };
    infrastructure: {
      available: boolean;
      observation_count: number;
      indicator_types: Record<string, number>;
      sources: Record<string, number>;
      last_observed: string | null;
      mean_observation_confidence: number | null;
    };
  };
  patterns: string[];
  behavioral_drift?: {
    available: boolean;
    baseline_generated_at?: string | null;
    linguistic_feature_deltas: Array<{
      feature: string;
      previous: number;
      current: number;
      delta: number;
    }>;
    operational_changes: Record<string, { previous: number; current: number; delta: number }>;
    lifecycle_changes: Record<string, { previous: number; current: number; delta: number }>;
    interaction_changes: Record<string, { previous: number; current: number; delta: number }>;
    infrastructure_changes: Record<string, { previous: number; current: number; delta: number }>;
    note: string;
  };
  limitations: string[];
  history: Array<{
    generated_at?: string;
    coverage_score: number;
    profile_version: string;
    source_fingerprint: string;
  }>;
}
export function refreshActorBehavioralProfile(actorId: string): Promise<BehavioralProfile> {
  return request<BehavioralProfile>(`/actors/${encodeURIComponent(actorId)}/behavioral-profile/refresh`, { method: "POST" });
}
export function getActorBehavioralProfile(actorId: string): Promise<BehavioralProfile> {
  return request<BehavioralProfile>(`/actors/${encodeURIComponent(actorId)}/behavioral-profile`);
}


export interface EvidenceIntegrityStatus {
  mode: "internal_hash_chain" | string;
  blockchain_anchor_configured: boolean;
  entry_count: number;
  head_hash: string;
  genesis_hash: string;
}

export interface EvidenceIntegrityVerification {
  valid: boolean;
  entry_count: number;
  verified_entries: number;
  head_hash: string;
  broken_sequence_id?: number | null;
  reason: string;
}

export function getEvidenceIntegrityStatus(): Promise<EvidenceIntegrityStatus> {
  return request<EvidenceIntegrityStatus>("/integrity/status");
}

export function verifyEvidenceIntegrity(): Promise<EvidenceIntegrityVerification> {
  return request<EvidenceIntegrityVerification>("/integrity/verify");
}


export interface CollectionSource {
  id: number;
  name: string;
  kind: string;
  url: string;
  actor_id?: string | null;
  enabled: boolean;
  interval_minutes: number;
  last_status: string;
  last_error?: string | null;
}
export interface CollectionStatus {
  enabled: boolean;
  poll_interval_minutes: number;
  sources: number;
  enabled_sources: number;
  continuous_collection: string;
}
export interface AdvancedAlert {
  id: number;
  actor_id?: string | null;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  payload: Record<string, unknown>;
  created_at?: string | null;
}
export interface AdvancedGraphAnomalyResponse {
  total_actors: number;
  results: GraphAnomalyResult[];
  limit: number;
}
export function getCollectionStatus(): Promise<CollectionStatus> {
  return request<CollectionStatus>("/collection/status");
}
export function getCollectionSources(): Promise<CollectionSource[]> {
  return request<CollectionSource[]>("/collection/sources");
}
export function getAdvancedAlerts(sinceId = 0): Promise<AdvancedAlert[]> {
  return request<AdvancedAlert[]>(`/alerts?since_id=${sinceId}`);
}
export function runStylometryDiscovery(limit = 100, actorId?: string): Promise<{ results: any[]; model_status: string }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (actorId) params.set("actor_id", actorId);
  return request<{ results: any[]; model_status: string }>(`/correlation/stylometry-discovery?${params.toString()}`, { method: "POST" });
}
export function runEvidenceAblation(actorId: string, disabledSignals: string[]): Promise<any> {
  return request<any>(`/correlation/actor/${encodeURIComponent(actorId)}/ablation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ disabled_signals: disabledSignals }),
  });
}
export function getCalibrationEvaluation(pairs = 100): Promise<Record<string, any>> {
  return request<Record<string, any>>(`/evaluation/calibration?pairs=${pairs}`);
}
export function getActorEntityLinks(actorId: string): Promise<any[]> {
  return request<any[]>(`/entities/actor/${encodeURIComponent(actorId)}`);
}
export function getMerkleIntegrityStatus(): Promise<Record<string, any>> {
  return request<Record<string, any>>("/integrity/merkle-status");
}
export function fingerprintMedia(mediaId: string, dataUrl: string, source = "investigator_upload", actorId?: string): Promise<any> {
  return request<any>("/media/fingerprint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ media_id: mediaId, data_url: dataUrl, source, actor_id: actorId || null }),
  });
}
export function compareMedia(mediaA: string, mediaB: string): Promise<Record<string, any>> {
  return request<Record<string, any>>("/media/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ media_a: mediaA, media_b: mediaB }),
  });
}

export interface HistoricalCaseProvenance {
  source: string;
  title: string;
  url: string;
  scope?: string;
}
export interface HistoricalCaseIdentityMatch {
  identity_id: string;
  documented_name: string;
  aliases: string[];
  matched_aliases: string[];
  role?: string;
}
export interface HistoricalCaseTimelineEvent {
  event_id: string;
  identity_id: string;
  date: string;
  date_precision?: string;
  event_type: string;
  entity: string;
  source: string;
  notes?: string;
  case_context?: boolean;
  matched_identity?: string | null;
}
export interface HistoricalCaseContext {
  case_id: string;
  case_name: string;
  matched_identities: HistoricalCaseIdentityMatch[];
  provenance: HistoricalCaseProvenance[];
  timeline: HistoricalCaseTimelineEvent[];
  expected_same_identity_pairs: string[][];
  expected_different_identity_pairs: string[][];
  model_limitations: string[];
  matched_aliases: string[];
  validation_summary: {
    positive_control_pairs: number;
    negative_control_pairs: number;
    modules: string[];
    stylometry_status: string;
  };
}
export interface HistoricalCaseContextResponse {
  actor_id: string;
  matches: HistoricalCaseContext[];
  note: string;
}
export function getHistoricalCaseContext(actorId: string): Promise<HistoricalCaseContextResponse> {
  return request<HistoricalCaseContextResponse>(
    `/historical-cases/context/actor/${encodeURIComponent(actorId)}`,
  );
}

export function createCollectionSource(payload: {
  name: string;
  kind: "json" | "rss" | "html" | "tor_http";
  url: string;
  actor_id?: string | null;
  enabled?: boolean;
  interval_minutes?: number;
  headers?: Record<string, string>;
  parser_config?: Record<string, unknown>;
}): Promise<CollectionSource> {
  return request<CollectionSource>("/collection/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
export function runHistoricalCaseValidation(cases: Array<{
  case_id: string;
  handle_a: string;
  handle_b: string;
  expected_same_actor: boolean;
  threshold?: number;
}>): Promise<any> {
  return request<any>("/evaluation/historical-cases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cases),
  });
}
export function inspectTor(url: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/tor/inspect?url=" + encodeURIComponent(url), { method: "POST" });
}
export function getMerkleStatus(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/integrity/merkle-status");
}
