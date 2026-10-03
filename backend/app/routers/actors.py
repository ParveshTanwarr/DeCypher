from datetime import datetime
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
from app.models.sql_models import Actor, DarkWebHandle, Wallet, Observation, PGPKey, TrustLink, Marketplace, ScanTarget
from app.models.advanced_models import EntityLink, ExternalEntity
from app.routers.auth import get_current_user
from app.services import graph_service
from app.services.observation_scope import build_observation_target_keys

router = APIRouter(prefix="/actors", tags=["Actors"], dependencies=[Depends(get_current_user)])


def _graph_handle_id(handle: DarkWebHandle) -> str:
    """Return the canonical cross-system graph identity for a SQL handle."""
    return handle.source_handle_id or f"legacy:{handle.id}"


def _resolve_graph_handle_id(
    db: Session,
    handle_name: Optional[str],
    actor_id: Optional[str] = None,
) -> Optional[str]:
    """Resolve a textual wallet handle to the stable graph handle identity."""
    normalized = (handle_name or "").strip().lower()
    if not normalized:
        return None

    query = (
        db.query(DarkWebHandle)
        .filter(func.lower(DarkWebHandle.handle) == normalized)
        .order_by(DarkWebHandle.id.asc())
    )
    if actor_id:
        actor_handle = query.filter(DarkWebHandle.actor_id == actor_id).first()
        if actor_handle:
            return _graph_handle_id(actor_handle)

    handle = query.first()
    return _graph_handle_id(handle) if handle else None


def _build_actor_detail(actor: Actor, db: Session) -> ActorDetail:
    handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
    wallets = db.query(Wallet).filter(Wallet.actor_id == actor.actor_id).all()

    handle_names = [h.handle for h in handles]
    wallet_addrs = [w.address for w in wallets]

    pgp_fingerprints = sorted({
        key.fingerprint
        for handle in handles
        for key in getattr(handle, "pgp_keys", [])
        if key.fingerprint
    })

    trust_links = [
        {
            "source": link.source_handle.handle,
            "target": link.target_handle.handle,
            "relationship_type": link.relationship_type,
            "confidence": link.confidence,
            "source_name": link.source,
            "first_seen": link.first_seen,
            "last_seen": link.last_seen,
        }
        for handle in handles
        for link in (handle.trust_links_out + handle.trust_links_in)
        if link.source_handle and link.target_handle
    ]

    first_dates = [h.first_seen for h in handles if h.first_seen]
    last_dates = [h.last_seen for h in handles if h.last_seen]

    first_seen_str = min(first_dates).strftime("%Y-%m-%d") if first_dates else "N/A"
    last_seen_str = max(last_dates).strftime("%Y-%m-%d") if last_dates else "N/A"

    platforms = list({h.platform for h in handles if h.platform})

    actor_scan_targets = (
        db.query(ScanTarget)
        .filter(ScanTarget.actor_id == actor.actor_id)
        .all()
    )
    target_keys = build_observation_target_keys(
        actor.actor_id,
        actor.primary_handle,
        handles,
        actor_scan_targets,
    )
    scan_observations = (
        db.query(Observation)
        .filter(
            func.lower(Observation.target).in_(target_keys),
            Observation.detected.is_(True),
        )
        .all()
    )
    scan_dates = [o.timestamp for o in scan_observations if o.timestamp]
    target_scan_dates = [
        target.last_scan_at
        for target in actor_scan_targets
        if target.last_scan_at
    ]
    latest_scan = max(target_scan_dates or scan_dates, default=None)
    last_scan_date = latest_scan.strftime("%Y-%m-%d") if latest_scan else None

    return ActorDetail(
        actor_id=actor.actor_id,
        primary_handle=actor.primary_handle,
        risk_category=actor.risk_category,
        confidence_score=actor.confidence_score,
        priority_score=actor.priority_score,
        first_seen=first_seen_str,
        last_scan_date=last_scan_date,
        last_seen=last_seen_str,
        handles=handle_names,
        wallets=wallet_addrs,
        marketplaces=platforms,
        pgp_keys=pgp_fingerprints,
        trust_links=trust_links,
        evidence_trail=[
            {
                "observation_id": o.observation_id,
                "signal_type": o.indicator_type or "infrastructure",
                "indicator_type": o.indicator_type,
                "detected": o.detected,
                "value": o.value,
                "target": o.target,
                "source": o.source,
                "confidence": o.confidence,
                "timestamp": o.timestamp,
                "description": o.description,
            }
            for o in scan_observations
        ],
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
                priority_score=actor.priority_score,
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
def get_actor_evidence(
    actor_id: str,
    start: Optional[datetime] = Query(
        None,
        description="Include observations at or after this timestamp (ISO 8601).",
    ),
    end: Optional[datetime] = Query(
        None,
        description="Include observations at or before this timestamp (ISO 8601).",
    ),
    db: Session = Depends(get_db),
):
    actor = db.query(Actor).filter(func.lower(Actor.actor_id) == actor_id.lower()).first()
    target_keys = {actor_id.lower()}

    if actor:
        handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == actor.actor_id).all()
        scan_targets = (
            db.query(ScanTarget)
            .filter(ScanTarget.actor_id == actor.actor_id)
            .all()
        )
        target_keys = build_observation_target_keys(
            actor.actor_id,
            actor.primary_handle,
            handles,
            scan_targets,
        )

    if start and end and start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The start timestamp must be earlier than or equal to the end timestamp.",
        )

    # Query filtered directly in SQL instead of doing a full table scan.
    evidence_query = db.query(Observation).filter(
        func.lower(Observation.target).in_(target_keys),
        Observation.detected.is_(True),
    )
    if start:
        evidence_query = evidence_query.filter(
            Observation.timestamp >= start
        )
    if end:
        evidence_query = evidence_query.filter(
            Observation.timestamp <= end
        )

    matched_observations = (
        evidence_query
        .order_by(Observation.timestamp.desc())
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

    scan_targets = (
        db.query(ScanTarget)
        .filter(ScanTarget.actor_id == actor.actor_id)
        .all()
    )
    observation_target_keys = build_observation_target_keys(
        actor.actor_id,
        actor.primary_handle,
        handles,
        scan_targets,
    )
    observations = (
        db.query(Observation)
        .filter(func.lower(Observation.target).in_(observation_target_keys))
        .all()
    )
    # Candidate entity matches are first-class graph evidence. They remain
    # separate from confirmed actor/handle ownership relationships.
    candidate_entity_links = (
        db.query(EntityLink, ExternalEntity)
        .join(ExternalEntity, ExternalEntity.id == EntityLink.entity_id)
        .filter(EntityLink.actor_id == actor.actor_id)
        .order_by(EntityLink.score.desc(), ExternalEntity.id.asc())
        .all()
    )

    actor_handle_ids = [h.id for h in handles]
    actor_trust_links = (
        db.query(TrustLink)
        .filter(
            (TrustLink.source_handle_id.in_(actor_handle_ids))
            | (TrustLink.target_handle_id.in_(actor_handle_ids))
        )
        .all()
        if actor_handle_ids
        else []
    )
    marketplace_names = {h.platform for h in handles if h.platform}
    related_marketplaces = (
        db.query(Marketplace)
        .filter(Marketplace.name.in_(marketplace_names))
        .all()
        if marketplace_names
        else []
    )
    related_handle_ids = set(actor_handle_ids)
    for link in actor_trust_links:
        # Include both sides of inbound and outbound trust relationships.
        # This keeps every projected trust endpoint on its canonical stable ID.
        related_handle_ids.add(link.source_handle_id)
        related_handle_ids.add(link.target_handle_id)

    graph_identity_handles = (
        db.query(DarkWebHandle)
        .filter(DarkWebHandle.id.in_(related_handle_ids))
        .all()
        if related_handle_ids
        else []
    )

    # ---------------------------------------------------------
    # Synchronize the current actor's PostgreSQL evidence into
    # Neo4j. This makes the graph usable even when the ingestion
    # pipeline has not explicitly populated Neo4j yet.
    # ---------------------------------------------------------

    neo4j_sync_ok = False

    try:
        graph_handle_id_by_db_id = {
            h.id: _graph_handle_id(h)
            for h in graph_identity_handles
        }
        handle_id_by_name = {}
        for handle in handles:
            if handle.handle:
                handle_id_by_name.setdefault(
                    handle.handle.strip().lower(),
                    _graph_handle_id(handle),
                )

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
                    "handle_id": _graph_handle_id(h),
                    "actor_id": h.actor_id,
                    "handle": h.handle,
                    "platform": h.platform,
                    "status": h.status,
                }
                for h in graph_identity_handles
            ],
            wallets=[
                {
                    "actor_id": w.actor_id,
                    "address": w.address,
                    "currency": w.currency,
                    "associated_handle": w.associated_handle,
                    "handle_id": (
                        handle_id_by_name.get(w.associated_handle.strip().lower())
                        or _resolve_graph_handle_id(
                            db,
                            w.associated_handle,
                            actor_id=w.actor_id,
                        )
                        if w.associated_handle
                        else None
                    ),
                }
                for w in wallets
            ],
        )

        graph_service.sync_pgp_and_trust_graph(
            [
                {
                    "handle_id": h.source_handle_id or f"legacy:{h.id}",
                    "actor_id": h.actor_id,
                    "handle": h.handle,
                    "pgp_fingerprint": (
                        h.pgp_keys[0].fingerprint
                        if h.pgp_keys
                        else None
                    ),
                }
                for h in graph_identity_handles
            ],
            [
                {
                    "source_handle_id": graph_handle_id_by_db_id.get(
                        link.source_handle_id,
                        f"legacy:{link.source_handle_id}",
                    ),
                    "target_handle_id": graph_handle_id_by_db_id.get(
                        link.target_handle_id,
                        f"legacy:{link.target_handle_id}",
                    ),
                    "relationship_type": link.relationship_type,
                    "confidence": link.confidence,
                    "source": link.source,
                    "first_seen": link.first_seen.isoformat() if link.first_seen else None,
                    "last_seen": link.last_seen.isoformat() if link.last_seen else None,
                }
                for link in actor_trust_links
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
        neo4j_sync_ok = True

    except Exception as exc:
        # Graph sync is additive. If Neo4j is unavailable,
        # the existing Postgres fallback still works.
        print(f"Neo4j sync warning: {exc}")

    # ---------------------------------------------------------
    # Prefer the rich Neo4j investigation graph.
    # ---------------------------------------------------------

    neo4j_graph = None
    if neo4j_sync_ok:
        try:
            neo4j_graph = graph_service.get_actor_subgraph(actor.actor_id)
        except Exception as exc:
            print(f"Neo4j read warning: {exc}")

    if neo4j_graph:
        nodes = [
            GraphNode(
                id=actor.actor_id,
                label="Actor",
                name=actor.primary_handle,
                category="Actor",
                properties={
                    "priority_score": actor.priority_score,
                    "confidence_score": actor.confidence_score,
                    "risk_category": actor.risk_category,
                },
            )
        ]

        links = []

        # Handles. Use stable handle IDs as graph node keys because names
        # may legitimately repeat across different marketplaces.
        for handle_node in neo4j_graph.get("handle_nodes", []):
            handle_id = handle_node.get("handle_id")
            handle = handle_node.get("handle")
            if not handle_id or not handle:
                continue
            nodes.append(
                GraphNode(
                    id=f"handle:{handle_id}",
                    label="Handle",
                    name=handle,
                    category="Handle",
                    properties={"platform": handle_node.get("platform")},
                )
            )
            links.append(
                GraphEdge(
                    source=actor.actor_id,
                    target=f"handle:{handle_id}",
                    relation="USES_HANDLE",
                )
            )

        # PGP keys
        for pgp_key in neo4j_graph.get("pgp_keys", []):
            fingerprint = pgp_key.get("fingerprint")
            if not fingerprint:
                continue

            nodes.append(
                GraphNode(
                    id=f"pgp:{fingerprint}",
                    label="PGP Key",
                    name=fingerprint,
                    category="PGPKey",
                )
            )

        for pair in neo4j_graph.get("handle_pgp_keys", []):
            handle_id = pair.get("handle_id")
            handle = pair.get("handle")
            fingerprint = pair.get("fingerprint")
            if not handle_id or not handle or not fingerprint:
                continue

            nodes.append(
                GraphNode(
                    id=f"pgp:{fingerprint}",
                    label="PGP Key",
                    name=fingerprint,
                    category="PGPKey",
                )
            )
            links.append(
                GraphEdge(
                    source=f"handle:{handle_id}",
                    target=f"pgp:{fingerprint}",
                    relation="HAS_PGP_KEY",
                )
            )

        # Trust links
        for trust in neo4j_graph.get("trust_links", []):
            source_id = trust.get("source_handle_id")
            source = trust.get("source")
            target_id = trust.get("target_handle_id")
            target = trust.get("target")
            if not source_id or not source or not target_id or not target:
                continue

            nodes.append(
                GraphNode(
                    id=f"handle:{source_id}",
                    label="Handle",
                    name=source,
                    category="Handle",
                )
            )
            nodes.append(
                GraphNode(
                    id=f"handle:{target_id}",
                    label="Handle",
                    name=target,
                    category="TrustedHandle",
                )
            )
            links.append(
                GraphEdge(
                    source=f"handle:{source_id}",
                    target=f"handle:{target_id}",
                    relation="TRUSTS",
                )
            )

        # Trust links are authoritative evidence from PostgreSQL. If the
        # Neo4j projection is missing one, enrich the response from the
        # normalized SQL relationship instead of silently dropping it.
        neo4j_trust_edges = {
            (
                link.source_handle_id,
                link.target_handle_id,
                link.relationship_type,
            )
            for link in actor_trust_links
        }
        rendered_trust_edges = {
            (link.source, link.target, link.relation)
            for link in links
            if link.relation == "TRUSTS"
        }
        for trust in actor_trust_links:
            source = trust.source_handle
            target = trust.target_handle
            if not source or not target:
                continue

            source_graph_id = _graph_handle_id(source)
            target_graph_id = _graph_handle_id(target)
            edge_key = (source.id, target.id, trust.relationship_type)
            rendered_key = (
                f"handle:{source_graph_id}",
                f"handle:{target_graph_id}",
                "TRUSTS",
            )
            if edge_key in neo4j_trust_edges or rendered_key in rendered_trust_edges:
                continue

            nodes.append(
                GraphNode(
                    id=f"handle:{source_graph_id}",
                    label="Handle",
                    name=source.handle,
                    category="Handle",
                )
            )
            nodes.append(
                GraphNode(
                    id=f"handle:{target_graph_id}",
                    label="Handle",
                    name=target.handle,
                    category="TrustedHandle",
                )
            )
            links.append(
                GraphEdge(
                    source=f"handle:{source_graph_id}",
                    target=f"handle:{target_graph_id}",
                    relation="TRUSTS",
                )
            )
            rendered_trust_edges.add(rendered_key)

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
            other_handle_id = pair.get("handle_id")
            other_handle = pair.get("handle")

            if not wallet or not other_handle_id or not other_handle:
                continue

            nodes.append(
                GraphNode(
                    id=f"handle:{other_handle_id}",
                    label="Handle",
                    name=other_handle,
                    category="CorrelatedHandle",
                )
            )

            links.append(
                GraphEdge(
                    source=f"wallet:{wallet}",
                    target=f"handle:{other_handle_id}",
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
            handle_id = pair.get("handle_id")
            handle = pair.get("handle")
            marketplace = pair.get("marketplace")

            if not handle_id or not handle or not marketplace:
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
                    source=f"handle:{handle_id}",
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

        # Source-derived exact identifier matches are displayed as candidate
        # links, never as confirmed identity relationships.
        for entity_link, entity in candidate_entity_links:
            entity_node_id = f"external:{entity.source}:{entity.entity_type}:{entity.canonical_value}"
            nodes.append(GraphNode(
                id=entity_node_id,
                label="External Entity",
                name=entity.canonical_value,
                category="ExternalEntity",
                properties={
                    "entity_type": entity.entity_type,
                    "source": entity.source,
                    "score": entity_link.score,
                    "match_type": entity_link.match_type,
                    "identity_status": "candidate_only",
                },
            ))
            links.append(GraphEdge(
                source=actor.actor_id,
                target=entity_node_id,
                relation="POSSIBLE_MATCH",
            ))

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
            properties={
                "priority_score": actor.priority_score,
                "confidence_score": actor.confidence_score,
                "risk_category": actor.risk_category,
            },
        )
    ]

    links = []

    for h in handles:
        nodes.append(
            GraphNode(
                id=f"handle:{_graph_handle_id(h)}",
                label="Handle",
                name=h.handle,
                category="Handle",
            )
        )

        links.append(
            GraphEdge(
                source=actor.actor_id,
                target=f"handle:{_graph_handle_id(h)}",
                relation="USES_HANDLE",
            )
        )

    for key in sorted({
        key.fingerprint
        for h in handles
        for key in h.pgp_keys
        if key.fingerprint
    }):
        nodes.append(
            GraphNode(
                id=f"pgp:{key}",
                label="PGP Key",
                name=key,
                category="PGPKey",
            )
        )

    for h in handles:
        for key in h.pgp_keys:
            links.append(
                GraphEdge(
                    source=f"handle:{_graph_handle_id(h)}",
                    target=f"pgp:{key.fingerprint}",
                    relation="HAS_PGP_KEY",
                )
            )

    # Include both inbound and outbound trust edges so the PostgreSQL
    # fallback matches the richer Neo4j graph semantics.
    for link in actor_trust_links:
        source = link.source_handle
        target = link.target_handle
        if not source or not target:
            continue

        nodes.append(
            GraphNode(
                id=f"handle:{_graph_handle_id(source)}",
                label="Handle",
                name=source.handle,
                category="Handle",
            )
        )
        nodes.append(
            GraphNode(
                id=f"handle:{_graph_handle_id(target)}",
                label="Handle",
                name=target.handle,
                category="TrustedHandle",
            )
        )
        links.append(
            GraphEdge(
                source=f"handle:{_graph_handle_id(source)}",
                target=f"handle:{_graph_handle_id(target)}",
                relation="TRUSTS",
            )
        )

    wallet_addresses = {w.address for w in wallets if w.address}
    reused_wallet_rows = (
        db.query(Wallet)
        .filter(
            Wallet.address.in_(wallet_addresses),
            Wallet.actor_id != actor.actor_id,
        )
        .all()
        if wallet_addresses
        else []
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

    # Surface wallet reuse even when Neo4j is unavailable.
    for reused in reused_wallet_rows:
        if reused.associated_handle and reused.address:
            reused_handle_id = _resolve_graph_handle_id(
                db,
                reused.associated_handle,
                actor_id=reused.actor_id,
            )
            if not reused_handle_id:
                continue
            nodes.append(
                GraphNode(
                    id=f"handle:{reused_handle_id}",
                    label="Handle",
                    name=reused.associated_handle,
                    category="CorrelatedHandle",
                )
            )
            links.append(
                GraphEdge(
                    source=f"wallet:{reused.address}",
                    target=f"handle:{reused_handle_id}",
                    relation="ALSO_USED_BY",
                )
            )

    # Marketplace nodes from the actual handle-platform relationships.
    for marketplace in related_marketplaces:
        nodes.append(
            GraphNode(
                id=f"marketplace:{marketplace.name}",
                label="Marketplace",
                name=marketplace.name,
                category="Marketplace",
            )
        )
        for handle in handles:
            if handle.platform == marketplace.name:
                links.append(
                    GraphEdge(
                        source=f"handle:{_graph_handle_id(handle)}",
                        target=f"marketplace:{marketplace.name}",
                        relation="USES_MARKETPLACE",
                    )
                )

    # Infrastructure/observation nodes from PostgreSQL evidence.
    for observation in observations:
        nodes.append(
            GraphNode(
                id=f"observation:{observation.observation_id}",
                label="Observation",
                name=observation.description or observation.value or observation.indicator_type,
                category="Observation",
            )
        )
        links.append(
            GraphEdge(
                source=actor.actor_id,
                target=f"observation:{observation.observation_id}",
                relation="HAS_OBSERVATION",
            )
        )
        if observation.value:
            infra_id = f"infrastructure:{observation.value}"
            nodes.append(
                GraphNode(
                    id=infra_id,
                    label="Infrastructure",
                    name=observation.value,
                    category="Infrastructure",
                )
            )
            links.append(
                GraphEdge(
                    source=f"observation:{observation.observation_id}",
                    target=infra_id,
                    relation="EVIDENCE_OF",
                )
            )

    # Remove duplicate nodes/edges in the PostgreSQL fallback too.
    unique_nodes = {}
    for node in nodes:
        unique_nodes[node.id] = node
    unique_links = {}
    for link in links:
        unique_links[(link.source, link.target, link.relation)] = link

    # Keep candidate entity evidence visible even when Neo4j is unavailable.
    for entity_link, entity in candidate_entity_links:
        entity_node_id = f"external:{entity.source}:{entity.entity_type}:{entity.canonical_value}"
        nodes.append(GraphNode(
            id=entity_node_id,
            label="External Entity",
            name=entity.canonical_value,
            category="ExternalEntity",
            properties={
                "entity_type": entity.entity_type,
                "source": entity.source,
                "score": entity_link.score,
                "match_type": entity_link.match_type,
                "identity_status": "candidate_only",
            },
        ))
        links.append(GraphEdge(
            source=actor.actor_id,
            target=entity_node_id,
            relation="POSSIBLE_MATCH",
        ))

    unique_nodes = {node.id: node for node in nodes}
    unique_links = {
        (link.source, link.target, link.relation): link for link in links
    }
    return GraphPayload(
        nodes=list(unique_nodes.values()),
        links=list(unique_links.values()),
    )