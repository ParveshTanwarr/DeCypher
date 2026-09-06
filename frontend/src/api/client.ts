const API_BASE = "http://127.0.0.1:8000";

export interface Actor {
  actor_id: string;
  primary_handle: string;
  risk_category: string;
  confidence_score: number;
  associated_handles: string[];
  last_active: string;
}

export interface SearchResult {
  type: string;
  id: string;
  matched_value: string;
  risk_category?: string;
}

export interface SearchResponse {
  query: string;
  total_matches: number;
  results: SearchResult[];
}

let authToken = "";

export function setAuthToken(token: string) {
  authToken = token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(authToken
        ? { Authorization: `Bearer ${authToken}` }
        : {}),
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `API error: ${response.status}`);
  }

  return response.json();
}

export async function login(
  username: string,
  password: string
): Promise<string> {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const response = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  if (!response.ok) {
    throw new Error("Invalid username or password");
  }

  const data = await response.json();
  setAuthToken(data.access_token);

  return data.access_token;
}

export function getActors(): Promise<Actor[]> {
  return request<Actor[]>("/actors");
}

export function getActor(actorId: string) {
  return request(`/actors/${actorId}`);
}

export function getActorEvidence(actorId: string) {
  return request(`/actors/${actorId}/evidence`);
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, unknown>;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphPayload {
  nodes: GraphNode[];
  links: GraphLink[];
}

export function getActorGraph(actorId: string): Promise<GraphPayload> {
  return request<GraphPayload>(`/actors/${actorId}/graph`);
}

export function searchActors(query: string): Promise<SearchResponse> {
  return request<SearchResponse>(
    `/search?q=${encodeURIComponent(query)}`
  );
}