export type NodeCategory = 'ACTOR' | 'HANDLE' | 'WALLET';

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

export type RelationshipType = 
  | 'controls'
  | 'uses wallet'
  | 'wallet reuse'
  | 'shared wallet signal'
  | 'shared PGP signal'
  | 'stylometry match'
  | 'infrastructure overlap'
  | 'possible rebrand';

export interface GraphNode {
  id: string;
  category: NodeCategory;
  label: string;
  subLabel?: string;
  risk?: RiskLevel;
  confidence: number;
  // Node metrics
  clusterId?: string;
  actorId?: string;
  platform?: string;
  currency?: string;
  address?: string;
  fullAddress?: string;
  signals?: string[];
  connectedCount?: number;
  val?: number; // Force graph size
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphLink {
  id?: string;
  source: string | GraphNode;
  target: string | GraphNode;
  type: RelationshipType;
  confidence: number;
  notes?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface TimelineEvent {
  id: string;
  date: string;
  title: string;
  description: string;
  confidence: number;
  type: 'OBSERVED' | 'DORMANCY' | 'REBRAND' | 'WALLET_OVERLAP' | 'ACTIVITY';
  categoryIcon?: string;
}

export interface ActorSignal {
  id: string;
  title: string;
  type: 'HANDLE CORRELATION' | 'WALLET REUSE' | 'BEHAVIORAL SIGNAL' | 'LIFECYCLE SIGNAL' | 'INFRASTRUCTURE';
  description: string;
  confidence: number;
  severity?: RiskLevel;
  details?: string;
}

export interface ActorProfile {
  id: string;
  clusterId: string;
  name: string;
  risk: RiskLevel;
  confidence: number;
  threatCategory: string;
  firstSeen: string;
  lastActive: string;
  summary: string;
  handles: string[];
  wallets: {
    currency: string;
    address: string;
    fullAddress: string;
    role: string;
  }[];
  signals: ActorSignal[];
  timeline: TimelineEvent[];
  executiveSummary: string;
  relationshipFindings: string[];
  behavioralSignals: {
    feature: string;
    similarityScore: number;
    description: string;
  }[];
  infrastructureFindings: string[];
  lifecycleAnalysis: string;
  finalAssessment: string;
}

export interface FilterState {
  nodeTypes: {
    actors: boolean;
    handles: boolean;
    wallets: boolean;
  };
  riskLevels: {
    critical: boolean;
    high: boolean;
    medium: boolean;
    low: boolean;
  };
  confidenceThreshold: 'all' | 'high' | 'medium' | 'low';
  searchTerm: string;
}
