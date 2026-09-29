const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface Actor { actor_id: string; primary_handle: string; risk_category: string; confidence_score: number; priority_score: number; associated_handles: string[]; last_active: string; }
export interface SearchResult { type: string; id: string; matched_value: string; risk_category?: string; }
export interface SearchResponse { query: string; total_matches: number; results: SearchResult[]; }
let authToken = "";
export function setAuthToken(token: string) { authToken = token; }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { ...(options.headers || {}), ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) } });
  if (!response.ok) throw new Error((await response.text()) || `API error: ${response.status}`);
  return response.json();
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
  const response = await fetch(`${API_BASE}/export/${endpoint}`, { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} });
  if (!response.ok) throw new Error((await response.text()) || `Export failed: ${response.status}`);
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || `decypher_export.${format}`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function getActors(): Promise<Actor[]> { return request<Actor[]>("/actors"); }
export function getActor(actorId: string) { return request(`/actors/${encodeURIComponent(actorId)}`); }
export function getActorEvidence(actorId: string) { return request(`/actors/${encodeURIComponent(actorId)}/evidence`); }

export interface GraphNode { id: string; label: string; name: string; category: string; type: string; properties?: Record<string, unknown>; }
export interface GraphLink { source: string; target: string; relation: string; }
export interface GraphPayload { nodes: GraphNode[]; links: GraphLink[]; }
export function getActorGraph(actorId: string): Promise<GraphPayload> { return request<GraphPayload>(`/actors/${encodeURIComponent(actorId)}/graph`); }

export interface CorrelationSignal { type: string; confidence: number; description: string; weight: number; details?: { handle_a?: string; handle_b?: string; is_same_author?: boolean; threshold_used?: number; shared_markers?: string[]; domain_routing?: Record<string, number>; }; }
export interface PriorityResult { score: number; level: string; components: { risk_severity: number; correlation: number; evidence_confidence: number; recency: number; evidence_coverage: number; }; weights: Record<string, number>; }
export interface CorrelationResult { candidate_actor: string; primary_handle: string; overall_confidence: number; risk_level: string; signals: CorrelationSignal[]; signal_count: number; available_weight: number; interpretation: string; priority?: PriorityResult; }
export function getActorCorrelation(actorId: string, handleA?: string, handleB?: string): Promise<CorrelationResult> { const params = new URLSearchParams(); if (handleA) params.set("handle_a", handleA); if (handleB) params.set("handle_b", handleB); const query = params.toString(); return request<CorrelationResult>(`/correlation/actor/${encodeURIComponent(actorId)}${query ? `?${query}` : ""}`); }
export function getAllCorrelations(): Promise<{ results: CorrelationResult[] }> { return request<{ results: CorrelationResult[] }>("/correlation/actors"); }
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
