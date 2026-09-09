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
    priority_score: Optional[int] = 0
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
# Feedback Schemas
# ------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    actor_id: str = Field(..., description="Target actor identifier")
    verdict: str = Field(..., description="Investigator verdict (e.g. Confirmed, False Positive, High Risk)")
    investigator_id: Optional[str] = Field("analyst", description="Investigator username or badge")
    notes: Optional[str] = Field(None, description="Investigator analytical justification")


class FeedbackResponse(BaseModel):
    status: str = "success"
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeedbackItemResponse(BaseModel):
    id: int
    actor_id: str
    verdict: str
    investigator_id: Optional[str] = None
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


# ------------------------------------------------------------------
# Scanner & Observation Schemas
# ------------------------------------------------------------------

class ObservationCreate(BaseModel):
    observation_id: str = Field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:8]}")
    indicator_type: str
    detected: bool = True
    value: Optional[str] = None
    target: str
    source: str = "scanner"
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Optional[float] = 1.0
    description: Optional[str] = None


class ObservationBatchCreate(BaseModel):
    observations: List[ObservationCreate] = Field(default_factory=list)


class BatchIngestionResponse(BaseModel):
    status: str = "success"
    inserted_count: int = 0
    message: str = "Successfully ingested scanner observations."


class ObservationResponse(BaseModel):
    id: int
    observation_id: str
    indicator_type: str
    detected: bool
    value: Optional[str] = None
    target: str
    source: str
    timestamp: Optional[datetime] = None
    confidence: Optional[float] = 1.0
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ScanRequest(BaseModel):
    target: str
    scan_type: str = "full"


class ScanResult(BaseModel):
    scan_id: str = Field(default_factory=lambda: f"scan_{uuid.uuid4().hex[:8]}")
    status: str = "completed"
    findings: List[Dict[str, Any]] = Field(default_factory=list)


# ------------------------------------------------------------------
# Search, Auth, Export & NLP Schemas
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


class HandleCompareRequest(BaseModel):
    handle_a: str = Field(..., description="First dark web handle identifier")
    handle_b: str = Field(..., description="Second dark web handle identifier")
    sample_text_a: Optional[str] = Field(None, description="Optional raw text sample for handle A")
    sample_text_b: Optional[str] = Field(None, description="Optional raw text sample for handle B")


class HandleCompareResponse(BaseModel):
    handle_a: str
    handle_b: str
    similarity_score: float
    is_same_author: bool
    confidence: float
    shared_linguistic_markers: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
