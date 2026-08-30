import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# Actor & Evidence Schemas
# ------------------------------------------------------------------

class EvidenceSignal(BaseModel):
    signal_type: str
    confidence: Optional[float] = None
    description: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:8]}")
    indicator_type: Optional[str] = None
    detected: bool = True
    value: Optional[str] = None
    target: Optional[str] = None
    source: Optional[str] = "manual"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActorSummary(BaseModel):
    actor_id: str
    primary_handle: str
    risk_category: str
    confidence_score: float
    associated_handles: List[str] = Field(default_factory=list)
    last_active: Optional[str] = None


class ActorDetail(BaseModel):
    actor_id: str
    primary_handle: str
    risk_category: str
    confidence_score: float
    priority_score: Optional[int] = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    last_active: Optional[str] = None
    associated_handles: List[str] = Field(default_factory=list)
    handles: List[str] = Field(default_factory=list)
    wallets: List[str] = Field(default_factory=list)
    marketplaces: List[str] = Field(default_factory=list)
    evidence_trail: List[EvidenceSignal] = Field(default_factory=list)


# ------------------------------------------------------------------
# Graph Schemas
# ------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    name: str
    category: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class GraphPayload(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    links: List[GraphEdge] = Field(default_factory=list)


# ------------------------------------------------------------------
# Feedback Schemas (routers/feedback.py)
# ------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    actor_id: Optional[str] = None
    feedback_type: str = "general"
    comment: str
    rating: Optional[int] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FeedbackResponse(BaseModel):
    status: str = "success"
    feedback_id: str = Field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:8]}")
    message: str = "Feedback received successfully"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ------------------------------------------------------------------
# Scanner & Observation Schemas (routers/scanner.py)
# ------------------------------------------------------------------

class ObservationCreate(BaseModel):
    indicator_type: str = "general"
    value: str
    source: str = "scanner"
    target: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = 1.0


class ObservationBatchCreate(BaseModel):
    observations: List[ObservationCreate] = Field(default_factory=list)
    batch_source: Optional[str] = "scanner_batch"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ObservationResponse(BaseModel):
    status: str = "success"
    processed_count: int = 0
    observation_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScanRequest(BaseModel):
    target: str
    scan_type: str = "full"


class ScanResult(BaseModel):
    scan_id: str = Field(default_factory=lambda: f"scan_{uuid.uuid4().hex[:8]}")
    status: str = "completed"
    findings: List[Dict[str, Any]] = Field(default_factory=list)


# ------------------------------------------------------------------
# Search, Auth, Export Schemas
# ------------------------------------------------------------------

class SearchQuery(BaseModel):
    query: str
    limit: int = 10
    offset: int = 0


class SearchResult(BaseModel):
    total: int = 0
    results: List[Any] = Field(default_factory=list)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExportRequest(BaseModel):
    format: str = "json"
    filters: Dict[str, Any] = Field(default_factory=dict)