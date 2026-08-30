from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models.schemas import ActorSummary, ActorDetail, EvidenceSignal, GraphPayload, GraphNode, GraphEdge

router = APIRouter(prefix="/actors", tags=["Actors"])

# Mock database records
MOCK_ACTORS: List[ActorDetail] = [
    ActorDetail(
        actor_id="ACT-8821",
        primary_handle="ShadowBroker_99",
        risk_category="Critical",
        confidence_score=0.94,
        priority_score=92,
        first_seen="2025-01-10",
        last_seen="2026-08-15",
        handles=["ShadowBroker_99", "GhostOperator", "NexusVendor"],
        wallets=["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
        marketplaces=["Hydra Reborn", "Abacus Market"],
        evidence_trail=[
            EvidenceSignal(
                signal_type="wallet_reuse",
                confidence=0.98,
                description="Shared BTC deposit address found across ShadowBroker_99 and GhostOperator",
                details={"wallet": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "overlap_count": 4}
            ),
            EvidenceSignal(
                signal_type="stylometry",
                confidence=0.89,
                description="Punctuation and function-word stylometric match across forum listings",
                details={"cosine_similarity": 0.892, "model": "stylometry-v1"}
            )
        ]
    ),
    ActorDetail(
        actor_id="ACT-4102",
        primary_handle="DarkPayload",
        risk_category="High",
        confidence_score=0.82,
        priority_score=78,
        first_seen="2025-06-20",
        last_seen="2026-07-30",
        handles=["DarkPayload", "SilentLeak"],
        wallets=["3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"],
        marketplaces=["TorBazaar"],
        evidence_trail=[
            EvidenceSignal(
                signal_type="infrastructure",
                confidence=0.85,
                description="Exposed status page and SSL certificate reuse between onion mirrors",
                details={"cert_sha256": "4a7d...391e", "port": 443}
            )
        ]
    )
]

@router.get("", response_model=List[ActorSummary])
def get_actors(
    category: Optional[str] = Query(None, description="Filter by risk category (e.g. Critical, High)"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold")
):
    results = []
    for actor in MOCK_ACTORS:
        if category and actor.risk_category.lower() != category.lower():
            continue
        if actor.confidence_score < min_confidence:
            continue
        results.append(
            ActorSummary(
                actor_id=actor.actor_id,
                primary_handle=actor.primary_handle,
                risk_category=actor.risk_category,
                confidence_score=actor.confidence_score,
                associated_handles=actor.handles,
                last_active=actor.last_seen
            )
        )
    return results

@router.get("/{actor_id}", response_model=ActorDetail)
def get_actor_detail(actor_id: str):
    for actor in MOCK_ACTORS:
        if actor.actor_id.lower() == actor_id.lower():
            return actor
    raise HTTPException(status_code=404, detail="Actor not found")

@router.get("/{actor_id}/evidence", response_model=List[EvidenceSignal])
def get_actor_evidence(actor_id: str):
    for actor in MOCK_ACTORS:
        if actor.actor_id.lower() == actor_id.lower():
            return actor.evidence_trail
    raise HTTPException(status_code=404, detail="Actor not found")

@router.get("/{actor_id}/graph", response_model=GraphPayload)
def get_actor_subgraph(actor_id: str):
    """Feeds React Force Graph for Lead A"""
    for actor in MOCK_ACTORS:
        if actor.actor_id.lower() == actor_id.lower():
            nodes = [GraphNode(id=actor.actor_id, label="Actor", name=actor.primary_handle, category="Actor")]
            links = []

            for h in actor.handles:
                nodes.append(GraphNode(id=h, label="Handle", name=h, category="Handle"))
                links.append(GraphEdge(source=actor.actor_id, target=h, relation="USES_HANDLE"))

            for w in actor.wallets:
                nodes.append(GraphNode(id=w, label="Wallet", name=w, category="Wallet"))
                links.append(GraphEdge(source=actor.primary_handle, target=w, relation="SHARES_WALLET"))

            return GraphPayload(nodes=nodes, links=links)
            
    raise HTTPException(status_code=404, detail="Actor graph not found")