from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Actor & Profile Models ---
class ActorSummary(BaseModel):
    actor_id: str
    primary_handle: str
    risk_category: str # "High", "Critical", "Medium", "Low"
    confidence_score: float # 0.0 to 1.0
    associated_handles: List[str]
    last_active: str

class EvidenceSignal(BaseModel):
    signal_type: str # "wallet_reuse", "stylometry", "pgp_key", "infrastructure"
    confidence: float
    description: str
    details: Dict[str, Any]

class ActorDetail(BaseModel):
    actor_id: str
    primary_handle: str
    risk_category: str
    confidence_score: float
    priority_score: int # 1 to 100
    first_seen: str
    last_seen: str
    handles: List[str]
    wallets: List[str]
    marketplaces: List[str]
    evidence_trail: List[EvidenceSignal]

# --- Graph Visualization Models ---
class GraphNode(BaseModel):
    id: str
    label: str # "Actor", "Handle", "Wallet", "Marketplace"
    name: str
    category: Optional[str] = "default"

class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str # "USES_HANDLE", "SHARES_WALLET", "POSSIBLY_SAME_AS"
    confidence: Optional[float] = 1.0

class GraphPayload(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphEdge]

# --- Feedback & Search Models ---
class FeedbackRequest(BaseModel):
    actor_id: str
    verdict: str # "confirm" or "reject"
    investigator_id: str
    notes: Optional[str] = None

class FeedbackResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime