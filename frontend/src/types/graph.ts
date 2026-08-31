export type NodeCategory = "actor" | "handle" | "wallet";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  category: NodeCategory;
  risk?: RiskLevel;
  confidence?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  relation: string;
  confidence?: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface ActorTimelineEvent {
  id: string;
  actorId: string;
  date: string;
  title: string;
  description: string;
  confidence: number;
}
