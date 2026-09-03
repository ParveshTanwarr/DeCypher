# Backward compatibility stub for legacy routers
MOCK_ACTORS = []
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.schemas import (
    ActorDetail,
    ActorSummary,
    EvidenceSignal,
    GraphEdge,
    GraphNode,
    GraphPayload,
)
from app.models.sql_models import Actor, DarkWebHandle, Wallet, Observation

router = APIRouter(prefix="/actors", tags=["Actors"])


def _build_actor_detail(actor: Actor, db: Session) -> ActorDetail:
    handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
    wallets = db.query(Wallet).filter(Wallet.actor_id == actor.actor_id).all()

    handle_names = [h.handle for h in handles]
    wallet_addrs = [w.address for w in wallets]

    first_dates = [h.first_seen for h in handles if h.first_seen]
    last_dates = [h.last_seen for h in handles if h.last_seen]

    first_seen_str = min(first_dates).strftime("%Y-%m-%d") if first_dates else "N/A"
    last_seen_str = max(last_dates).strftime("%Y-%m-%d") if last_dates else "N/A"

    platforms = list({h.platform for h in handles if h.platform})

    return ActorDetail(
        actor_id=actor.actor_id,
        primary_handle=actor.primary_handle,
        risk_category=actor.risk_category,
        confidence_score=actor.confidence_score,
        priority_score=actor.priority_score,
        first_seen=first_seen_str,
        last_seen=last_seen_str,
        handles=handle_names,
        wallets=wallet_addrs,
        marketplaces=platforms,
        evidence_trail=[],
    )


@router.get("", response_model=List[ActorSummary])
def get_actors(
    category: Optional[str] = Query(None, description="Filter by risk category (e.g. Critical, High)"),
    min_confidence: Optional[float] = Query(0.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db),
):
    query = db.query(Actor).filter(Actor.confidence_score >= min_confidence)
    if category:
        query = query.filter(Actor.risk_category.ilike(category))

    actors = query.all()
    results = []

    for actor in actors:
        handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
        last_dates = [h.last_seen for h in handles if h.last_seen]
        last_active_str = max(last_dates).strftime("%Y-%m-%d") if last_dates else "N/A"

        results.append(
            ActorSummary(
                actor_id=actor.actor_id,
                primary_handle=actor.primary_handle,
                risk_category=actor.risk_category,
                confidence_score=actor.confidence_score,
                associated_handles=[h.handle for h in handles],
                last_active=last_active_str,
            )
        )
    return results


@router.get("/{actor_id}", response_model=ActorDetail)
def get_actor_detail(actor_id: str, db: Session = Depends(get_db)):
    actor = db.query(Actor).filter(Actor.actor_id.ilike(actor_id)).first()
    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")
    return _build_actor_detail(actor, db)


@router.get("/{actor_id}/evidence", response_model=List[EvidenceSignal])
def get_actor_evidence(actor_id: str, db: Session = Depends(get_db)):
    actor = db.query(Actor).filter(Actor.actor_id.ilike(actor_id)).first()
    target_keys = [actor_id.lower()]

    if actor:
        target_keys.append(actor.primary_handle.lower())
        handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
        target_keys.extend([h.handle.lower() for h in handles])

    db_observations = db.query(Observation).all()
    matched_observations = [
        obs for obs in db_observations
        if obs.target and obs.target.lower() in target_keys
    ]

    if not actor and not matched_observations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Actor with ID '{actor_id}' not found.",
        )

    evidence_list: List[EvidenceSignal] = []
    for obs in matched_observations:
        signal = EvidenceSignal(
            observation_id=obs.observation_id,
            signal_type=obs.indicator_type or "infrastructure",
            indicator_type=obs.indicator_type,
            confidence=obs.confidence if obs.confidence is not None else 1.0,
            description=obs.description or f"Observed {obs.indicator_type}: {obs.value}",
            detected=obs.detected,
            value=obs.value,
            target=obs.target,
            source=obs.source or "scanner",
            timestamp=obs.timestamp,
            details={
                "indicator_type": obs.indicator_type,
                "value": obs.value,
                "source": obs.source,
            },
        )
        evidence_list.append(signal)

    return evidence_list


@router.get("/{actor_id}/graph", response_model=GraphPayload)
def get_actor_subgraph(actor_id: str, db: Session = Depends(get_db)):
    actor = db.query(Actor).filter(Actor.actor_id.ilike(actor_id)).first()
    if not actor:
        raise HTTPException(status_code=404, detail="Actor graph not found")

    handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
    wallets = db.query(Wallet).filter(Wallet.actor_id == actor.actor_id).all()

    nodes = [GraphNode(id=actor.actor_id, label="Actor", name=actor.primary_handle, category="Actor")]
    links = []

    for h in handles:
        nodes.append(GraphNode(id=h.handle, label="Handle", name=h.handle, category="Handle"))
        links.append(GraphEdge(source=actor.actor_id, target=h.handle, relation="USES_HANDLE"))

    for w in wallets:
        nodes.append(GraphNode(id=w.address, label="Wallet", name=w.address, category="Wallet"))
        links.append(GraphEdge(source=actor.primary_handle, target=w.address, relation="SHARES_WALLET"))

    return GraphPayload(nodes=nodes, links=links)