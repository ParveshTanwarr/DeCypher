from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

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
from app.routers.auth import get_current_user
from app.services import graph_service

router = APIRouter(prefix="/actors", tags=["Actors"], dependencies=[Depends(get_current_user)])


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
    limit: int = Query(1000, ge=1, le=2000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    query = db.query(Actor).filter(Actor.confidence_score >= min_confidence)
    if category:
        query = query.filter(Actor.risk_category.ilike(category))

    # Default limit is generously large (bigger than this dataset) so
    # existing callers that don't pass limit/offset keep getting
    # everything, same as before pagination was added -- but the API can
    # now actually be paged for larger datasets.
    actors = query.order_by(Actor.actor_id).offset(offset).limit(limit).all()
    if not actors:
        return []

    actor_ids = [a.actor_id for a in actors]

    # Batch fetch all handles in 1 query to prevent N+1 overhead
    handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id.in_(actor_ids)).all()
    handles_by_actor = {}
    for h in handles:
        handles_by_actor.setdefault(h.actor_id, []).append(h)

    results = []
    for actor in actors:
        actor_handles = handles_by_actor.get(actor.actor_id, [])
        last_dates = [h.last_seen for h in actor_handles if h.last_seen]
        last_active_str = max(last_dates).strftime("%Y-%m-%d") if last_dates else "N/A"

        results.append(
            ActorSummary(
                actor_id=actor.actor_id,
                primary_handle=actor.primary_handle,
                risk_category=actor.risk_category,
                confidence_score=actor.confidence_score,
                associated_handles=[h.handle for h in actor_handles],
                last_active=last_active_str,
            )
        )
    return results


@router.get("/{actor_id}", response_model=ActorDetail)
def get_actor_detail(actor_id: str, db: Session = Depends(get_db)):
    # Exact (case-insensitive) match -- ilike() alone would treat literal
    # "%" / "_" in a caller-supplied ID as SQL wildcards instead of an
    # exact identifier lookup.
    actor = db.query(Actor).filter(func.lower(Actor.actor_id) == actor_id.lower()).first()
    if not actor:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")
    return _build_actor_detail(actor, db)


@router.get("/{actor_id}/evidence", response_model=List[EvidenceSignal])
def get_actor_evidence(actor_id: str, db: Session = Depends(get_db)):
    actor = db.query(Actor).filter(func.lower(Actor.actor_id) == actor_id.lower()).first()
    target_keys = [actor_id.lower()]

    if actor:
        target_keys.append(actor.primary_handle.lower())
        handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
        target_keys.extend([h.handle.lower() for h in handles])

    # Query filtered directly in SQL instead of doing full table scan
    matched_observations = (
        db.query(Observation)
        .filter(func.lower(Observation.target).in_(target_keys))
        .all()
    )

    if not actor and not matched_observations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Actor with ID '{actor_id}' not found.",
        )

    evidence_list: List[EvidenceSignal] = []
    for obs in matched_observations:
        default_description = f"Observed {obs.indicator_type}" + (f": {obs.value}" if obs.value else " (not detected)")
        signal = EvidenceSignal(
            observation_id=obs.observation_id,
            signal_type=obs.indicator_type or "infrastructure",
            indicator_type=obs.indicator_type,
            confidence=obs.confidence if obs.confidence is not None else 1.0,
            description=obs.description or default_description,
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
    actor = db.query(Actor).filter(func.lower(Actor.actor_id) == actor_id.lower()).first()
    if not actor:
        raise HTTPException(status_code=404, detail="Actor graph not found")

    # Prefer the real Neo4j correlation graph -- it can surface *other*
    # handles that reused one of this actor's wallets, which the flat
    # Postgres join below has no way to know about. Falls back to
    # Postgres if Neo4j hasn't been synced yet (or isn't reachable), so
    # this endpoint still works before/without the graph pipeline running.
    neo4j_graph = graph_service.get_actor_subgraph(actor.actor_id)
    if neo4j_graph:
        nodes = [GraphNode(id=actor.actor_id, label="Actor", name=actor.primary_handle, category="Actor")]
        links = []
        for handle in neo4j_graph.get("handles", []):
            nodes.append(GraphNode(id=handle, label="Handle", name=handle, category="Handle"))
            links.append(GraphEdge(source=actor.actor_id, target=handle, relation="USES_HANDLE"))
        for wallet in neo4j_graph.get("wallets", []):
            nodes.append(GraphNode(id=wallet, label="Wallet", name=wallet, category="Wallet"))
            links.append(GraphEdge(source=actor.actor_id, target=wallet, relation="SHARES_WALLET"))
        for other_handle in neo4j_graph.get("correlated_handles", []):
            nodes.append(GraphNode(id=other_handle, label="Handle", name=other_handle, category="CorrelatedHandle"))
            # Linked via whichever wallet they share -- good enough for a
            # visual "these might be the same actor" cue without needing
            # a second round trip to work out exactly which wallet.
            for wallet in neo4j_graph.get("wallets", []):
                links.append(GraphEdge(source=wallet, target=other_handle, relation="ALSO_USED_BY"))
        return GraphPayload(nodes=nodes, links=links)

    # --- Fallback: build the same shape straight from Postgres ---
    handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
    wallets = db.query(Wallet).filter(Wallet.actor_id == actor.actor_id).all()

    nodes = [GraphNode(id=actor.actor_id, label="Actor", name=actor.primary_handle, category="Actor")]
    links = []

    for h in handles:
        nodes.append(GraphNode(id=h.handle, label="Handle", name=h.handle, category="Handle"))
        links.append(GraphEdge(source=actor.actor_id, target=h.handle, relation="USES_HANDLE"))

    for w in wallets:
        nodes.append(GraphNode(id=w.address, label="Wallet", name=w.address, category="Wallet"))
        links.append(GraphEdge(source=actor.actor_id, target=w.address, relation="SHARES_WALLET"))

    return GraphPayload(nodes=nodes, links=links)