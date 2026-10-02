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

export interface CorrelationSignal { type: string; confidence: number; description: string; weight: number; details?: { handle_a?: string; handle_b?: string; is_same_author?: boolean; threshold_used?: number; shared_markers?: string[]; domain_routing?: Record<string, number>; }; }
export interface PriorityResult { score: number; level: string; components: { risk_severity: number; correlation: number; evidence_confidence: number; recency: number; evidence_coverage: number; }; weights: Record<string, number>; }
export interface CorrelationResult { candidate_actor: string; primary_handle: string; overall_confidence: number; risk_level: string; signals: CorrelationSignal[]; signal_count: number; available_weight: number; interpretation: string; priority?: PriorityResult; }
export function getActorCorrelation(actorId: string, handleA?: string, handleB?: string): Promise<CorrelationResult> { const params = new URLSearchParams(); if (handleA) params.set("handle_a", handleA); if (handleB) params.set("handle_b", handleB); const query = params.toString(); return request<CorrelationResult>(`/correlation/actor/${encodeURIComponent(actorId)}${query ? `?${query}` : ""}`); }
export function getAllCorrelations(): Promise<{ results: CorrelationResult[] }> { return request<{ results: CorrelationResult[] }>(`/correlation/actors`); }
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
