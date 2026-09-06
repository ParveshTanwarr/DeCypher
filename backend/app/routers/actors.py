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
    actor = (
        db.query(Actor)
        .filter(func.lower(Actor.actor_id) == actor_id.lower())
        .first()
    )

    if not actor:
        raise HTTPException(
            status_code=404,
            detail="Actor graph not found",
        )

    handles = (
        db.query(DarkWebHandle)
        .filter(DarkWebHandle.actor_id == actor.actor_id)
        .all()
    )

    wallets = (
        db.query(Wallet)
        .filter(Wallet.actor_id == actor.actor_id)
        .all()
    )

    observations = (
        db.query(Observation)
        .filter(
            func.lower(Observation.target).in_(
                [
                    actor.actor_id.lower(),
                    actor.primary_handle.lower(),
                    *[h.handle.lower() for h in handles],
                ]
            )
        )
        .all()
    )

    # ---------------------------------------------------------
    # Synchronize the current actor's PostgreSQL evidence into
    # Neo4j. This makes the graph usable even when the ingestion
    # pipeline has not explicitly populated Neo4j yet.
    # ---------------------------------------------------------

    try:
        graph_service.sync_actor_batch(
            actors=[
                {
                    "actor_id": actor.actor_id,
                    "primary_handle": actor.primary_handle,
                    "risk_category": actor.risk_category,
                    "confidence_score": actor.confidence_score,
                }
            ],
            handles=[
                {
                    "actor_id": h.actor_id,
                    "handle": h.handle,
                    "platform": h.platform,
                    "status": h.status,
                }
                for h in handles
            ],
            wallets=[
                {
                    "actor_id": w.actor_id,
                    "address": w.address,
                    "currency": w.currency,
                    "associated_handle": w.associated_handle,
                }
                for w in wallets
            ],
        )

        graph_service.sync_actor_observations(
            actor.actor_id,
            [
                {
                    "observation_id": o.observation_id,
                    "indicator_type": o.indicator_type,
                    "detected": o.detected,
                    "value": o.value,
                    "target": o.target,
                    "source": o.source,
                    "confidence": o.confidence,
                    "description": o.description,
                    "timestamp": (
                        o.timestamp.isoformat()
                        if o.timestamp
                        else None
                    ),
                }
                for o in observations
            ],
        )

    except Exception as exc:
        # Graph sync is additive. If Neo4j is unavailable,
        # the existing Postgres fallback still works.
        print(f"Neo4j sync warning: {exc}")

    # ---------------------------------------------------------
    # Prefer the rich Neo4j investigation graph.
    # ---------------------------------------------------------

    neo4j_graph = graph_service.get_actor_subgraph(
        actor.actor_id
    )

    if neo4j_graph:
        nodes = [
            GraphNode(
                id=actor.actor_id,
                label="Actor",
                name=actor.primary_handle,
                category="Actor",
            )
        ]

        links = []

        # Handles
        for handle in neo4j_graph.get("handles", []):
            nodes.append(
                GraphNode(
                    id=f"handle:{handle}",
                    label="Handle",
                    name=handle,
                    category="Handle",
                )
            )

            links.append(
                GraphEdge(
                    source=actor.actor_id,
                    target=f"handle:{handle}",
                    relation="USES_HANDLE",
                )
            )

        # Wallets
        for wallet in neo4j_graph.get("wallets", []):
            nodes.append(
                GraphNode(
                    id=f"wallet:{wallet}",
                    label="Wallet",
                    name=wallet,
                    category="Wallet",
                )
            )

            links.append(
                GraphEdge(
                    source=actor.actor_id,
                    target=f"wallet:{wallet}",
                    relation="SHARES_WALLET",
                )
            )

                # Correlated handles discovered through wallet reuse.
        # Preserve the exact wallet -> handle relationship returned
        # by Neo4j instead of connecting every wallet to every handle.
        for pair in neo4j_graph.get(
            "wallet_correlations",
            [],
        ):
            wallet = pair.get("wallet")
            other_handle = pair.get("handle")

            if not wallet or not other_handle:
                continue

            nodes.append(
                GraphNode(
                    id=f"handle:{other_handle}",
                    label="Handle",
                    name=other_handle,
                    category="CorrelatedHandle",
                )
            )

            links.append(
                GraphEdge(
                    source=f"wallet:{wallet}",
                    target=f"handle:{other_handle}",
                    relation="ALSO_USED_BY",
                )
            )

                        # Marketplaces
        # Preserve the actual handle -> marketplace relationship
        # from the Neo4j graph instead of connecting every handle
        # to every marketplace.
        for pair in neo4j_graph.get(
            "handle_marketplaces",
            [],
        ):
            handle = pair.get("handle")
            marketplace = pair.get("marketplace")

            if not handle or not marketplace:
                continue

            nodes.append(
                GraphNode(
                    id=f"marketplace:{marketplace}",
                    label="Marketplace",
                    name=marketplace,
                    category="Marketplace",
                )
            )

            links.append(
                GraphEdge(
                    source=f"handle:{handle}",
                    target=f"marketplace:{marketplace}",
                    relation="USES_MARKETPLACE",
                )
            )
        # Observations
        for observation in neo4j_graph.get(
            "observations",
            [],
        ):
            observation_id = observation.get(
                "observation_id"
            )

            if not observation_id:
                continue

            name = (
                observation.get("description")
                or observation.get("value")
                or observation.get("indicator_type")
                or observation_id
            )

            nodes.append(
                GraphNode(
                    id=f"observation:{observation_id}",
                    label="Observation",
                    name=str(name),
                    category="Observation",
                )
            )

            links.append(
                GraphEdge(
                    source=actor.actor_id,
                    target=f"observation:{observation_id}",
                    relation="HAS_OBSERVATION",
                )
            )

        # Infrastructure
        for infrastructure in neo4j_graph.get(
            "infrastructure",
            [],
        ):
            key = (
                infrastructure.get("key")
                or infrastructure.get("value")
                or infrastructure.get("target")
            )

            if not key:
                continue

            nodes.append(
                GraphNode(
                    id=f"infrastructure:{key}",
                    label="Infrastructure",
                    name=str(key),
                    category="Infrastructure",
                )
            )

            for observation in neo4j_graph.get(
                "observations",
                [],
            ):
                if (
                    observation.get("value") == infrastructure.get("value")
                    or observation.get("target") == infrastructure.get("target")
                ):
                    observation_id = observation.get(
                        "observation_id"
                    )

                    if observation_id:
                        links.append(
                            GraphEdge(
                                source=f"observation:{observation_id}",
                                target=f"infrastructure:{key}",
                                relation="EVIDENCE_OF",
                            )
                        )

        # Remove duplicate nodes while preserving order.
        unique_nodes = {}
        for node in nodes:
            unique_nodes[node.id] = node

        # Remove duplicate edges.
        unique_links = {}
        for link in links:
            edge_key = (
                link.source,
                link.target,
                link.relation,
            )
            unique_links[edge_key] = link

        return GraphPayload(
            nodes=list(unique_nodes.values()),
            links=list(unique_links.values()),
        )

    # ---------------------------------------------------------
    # PostgreSQL fallback
    # ---------------------------------------------------------

    nodes = [
        GraphNode(
            id=actor.actor_id,
            label="Actor",
            name=actor.primary_handle,
            category="Actor",
        )
    ]

    links = []

    for h in handles:
        nodes.append(
            GraphNode(
                id=f"handle:{h.handle}",
                label="Handle",
                name=h.handle,
                category="Handle",
            )
        )

        links.append(
            GraphEdge(
                source=actor.actor_id,
                target=f"handle:{h.handle}",
                relation="USES_HANDLE",
            )
        )

    for w in wallets:
        nodes.append(
            GraphNode(
                id=f"wallet:{w.address}",
                label="Wallet",
                name=w.address,
                category="Wallet",
            )
        )

        links.append(
            GraphEdge(
                source=actor.actor_id,
                target=f"wallet:{w.address}",
                relation="SHARES_WALLET",
            )
        )

    return GraphPayload(
        nodes=nodes,
        links=links,
    )