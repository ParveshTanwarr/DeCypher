"""Temporal evidence graph materialization and timeline queries."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

from app.models.sql_models import (
    Actor,
    DarkWebHandle,
    InvestigatorFeedback,
    Observation,
    PGPKey,
    ScanTarget,
    TemporalEvent,
    TrustLink,
    Wallet,
)
from app.services.observation_scope import build_observation_target_keys


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _event(
    event_key: str,
    actor_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    timestamp: datetime | None,
    source: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if timestamp is None:
        return None
    return {
        "event_key": event_key,
        "actor_id": actor_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timestamp": timestamp,
        "source": source or "system",
        "payload": payload or {},
    }


def _collect_actor_events(db: Session, actor_ids: Iterable[str]) -> list[dict[str, Any]]:
    actor_ids = [str(actor_id) for actor_id in actor_ids]
    if not actor_ids:
        return []

    events: list[dict[str, Any]] = []

    handles = (
        db.query(DarkWebHandle)
        .options(joinedload(DarkWebHandle.pgp_keys))
        .filter(DarkWebHandle.actor_id.in_(actor_ids))
        .all()
    )
    for handle in handles:
        actor_id = str(handle.actor_id)
        handle_payload = {
            "handle": handle.handle,
            "platform": handle.platform,
            "status": handle.status,
        }
        for label, timestamp in (
            ("registered", handle.registration_date),
            ("first_seen", handle.first_seen),
            ("last_seen", handle.last_seen),
        ):
            payload = {
                **handle_payload,
                # Keep the DB entity_id for SQL compatibility, but carry the
                # canonical graph identity so Neo4j never has to infer it from
                # an integer primary key.
                "graph_handle_id": handle.source_handle_id or f"legacy:{handle.id}",
            }
            item = _event(
                f"handle:{handle.id}:{label}",
                actor_id,
                f"handle_{label}",
                "handle",
                str(handle.id),
                timestamp,
                "handles",
                payload,
            )
            if item:
                events.append(item)

        for key in handle.pgp_keys:
            for label, timestamp in (
                ("first_seen", key.first_seen),
                ("last_seen", key.last_seen),
            ):
                item = _event(
                    f"pgp:{key.id}:{label}:actor:{actor_id}",
                    actor_id,
                    f"pgp_{label}",
                    "pgp_key",
                    str(key.id),
                    timestamp,
                    key.source or "pgp",
                    {"fingerprint": key.fingerprint, "key_type": key.key_type},
                )
                if item:
                    events.append(item)

    wallets = (
        db.query(Wallet)
        .filter(Wallet.actor_id.in_(actor_ids))
        .all()
    )
    for wallet in wallets:
        item = _event(
            f"wallet:{wallet.id}:first_seen:actor:{wallet.actor_id}",
            str(wallet.actor_id),
            "wallet_first_seen",
            "wallet",
            str(wallet.id),
            wallet.first_seen,
            "wallets",
            {"address": wallet.address, "currency": wallet.currency, "associated_handle": wallet.associated_handle},
        )
        if item:
            events.append(item)

    handle_actor = {
        handle.id: str(handle.actor_id)
        for handle in db.query(DarkWebHandle.id, DarkWebHandle.actor_id)
        .filter(DarkWebHandle.actor_id.in_(actor_ids))
        .all()
    }
    trust_links = (
        db.query(TrustLink)
        .filter(
            (TrustLink.source_handle_id.in_(list(handle_actor)))
            | (TrustLink.target_handle_id.in_(list(handle_actor)))
        )
        .all()
        if handle_actor
        else []
    )
    for link in trust_links:
        actor_id = handle_actor.get(link.source_handle_id) or handle_actor.get(link.target_handle_id)
        if not actor_id:
            continue
        payload = {
            "relationship_type": link.relationship_type,
            "confidence": link.confidence,
            "source": link.source,
            "source_handle_id": link.source_handle_id,
            "target_handle_id": link.target_handle_id,
        }
        for label, timestamp in (
            ("first_seen", link.first_seen),
            ("last_seen", link.last_seen),
        ):
            item = _event(
                f"trust:{link.id}:{label}:actor:{actor_id}",
                actor_id,
                f"trust_{label}",
                "trust_link",
                str(link.id),
                timestamp,
                link.source or "trust",
                payload,
            )
            if item:
                events.append(item)

    observations = db.query(Observation).all()
    targets = db.query(ScanTarget).filter(
        ScanTarget.actor_id.in_(actor_ids)
    ).all()

    handles_by_actor: dict[str, list[DarkWebHandle]] = defaultdict(list)
    for handle in handles:
        if handle.actor_id:
            handles_by_actor[str(handle.actor_id)].append(handle)

    targets_by_actor: dict[str, list[ScanTarget]] = defaultdict(list)
    for target in targets:
        if target.actor_id:
            targets_by_actor[str(target.actor_id)].append(target)

    actor_by_target: dict[str, str] = {}
    actors_by_id = {
        str(actor.actor_id): actor
        for actor in db.query(Actor).filter(Actor.actor_id.in_(actor_ids)).all()
    }
    for actor_id in actor_ids:
        actor = actors_by_id.get(str(actor_id))
        if not actor:
            continue
        for key in build_observation_target_keys(
            actor.actor_id,
            actor.primary_handle,
            handles_by_actor.get(str(actor_id), []),
            targets_by_actor.get(str(actor_id), []),
        ):
            actor_by_target[key] = str(actor_id)

    for observation in observations:
        actor_id = actor_by_target.get((observation.target or "").strip().lower())
        if not actor_id:
            continue
        item = _event(
            f"observation:{observation.observation_id}",
            actor_id,
            "observation_recorded",
            "observation",
            observation.observation_id,
            observation.timestamp,
            observation.source,
            {
                "indicator_type": observation.indicator_type,
                "detected": observation.detected,
                "value": observation.value,
                "target": observation.target,
                "confidence": observation.confidence,
                "description": observation.description,
            },
        )
        if item:
            events.append(item)

    targets = [target for target in targets if target.last_scan_at is not None]
    for target in targets:
        item = _event(
            f"scan:{target.id}:last_scan",
            str(target.actor_id),
            "scan_completed",
            "scan_target",
            str(target.id),
            target.last_scan_at,
            "autoscan",
            {
                "name": target.name,
                "target_url": target.target_url,
                "last_status": target.last_status,
                "consecutive_failures": target.consecutive_failures,
            },
        )
        if item:
            events.append(item)

    return events


def backfill_temporal_events(db: Session, actor_id: str | None = None) -> int:
    """Materialize deterministic point-in-time events without duplicating rows."""
    actor_ids = (
        [actor_id]
        if actor_id
        else [row[0] for row in db.query(Actor.actor_id).order_by(Actor.actor_id.asc()).all()]
    )
    candidates = _collect_actor_events(db, actor_ids)
    if not candidates:
        return 0

    # Multiple source rows can legitimately describe the same normalized event
    # (for example, one PGP key attached to multiple handles of the same actor).
    # Collapse identical event keys before the bulk insert so idempotency is
    # guaranteed both across runs and within a single materialization batch.
    candidates_by_key = {}
    for row in candidates:
        candidates_by_key.setdefault(row["event_key"], row)
    candidates = list(candidates_by_key.values())

    keys = list(candidates_by_key)
    existing = {
        row[0]
        for row in db.query(TemporalEvent.event_key)
        .filter(TemporalEvent.event_key.in_(keys))
        .all()
    }
    missing = [row for row in candidates if row["event_key"] not in existing]
    if not missing:
        return 0

    # The pre-check above keeps the common path cheap, but concurrent workers
    # can still observe the same missing key. Let PostgreSQL enforce the unique
    # constraint atomically so materialization is idempotent under concurrency.
    stmt = insert(TemporalEvent).values(missing).on_conflict_do_nothing(
        index_elements=["event_key"]
    )
    result = db.execute(stmt)
    return int(result.rowcount or 0)


def sync_temporal_events_to_neo4j(db: Session, actor_id: str | None = None) -> int:
    """Project persisted temporal events into the Neo4j evidence graph."""
    from app.services import graph_service

    query = db.query(TemporalEvent).order_by(TemporalEvent.timestamp.asc(), TemporalEvent.id.asc())
    if actor_id:
        query = query.filter(TemporalEvent.actor_id == actor_id)
    events = query.all()
    if not events:
        return 0
    try:
        graph_service.sync_temporal_events(
            [
            {
                "event_id": event.event_key,
                "actor_id": event.actor_id,
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "timestamp": _iso(event.timestamp),
                "source": event.source,
                "payload": event.payload,
            }
                for event in events
            ]
        )
    except Exception as exc:
        # Postgres remains the source of truth when Neo4j is unavailable.
        logger.warning("Temporal Neo4j projection deferred: %s", exc)
    return len(events)


def materialize_temporal_events(db: Session, actor_id: str | None = None) -> int:
    count = backfill_temporal_events(db, actor_id=actor_id)
    db.flush()
    sync_temporal_events_to_neo4j(db, actor_id=actor_id)
    return count


def get_actor_timeline(
    db: Session,
    actor_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 250,
) -> dict[str, Any]:
    """Return a current timeline without mutating the database or graph."""
    candidates = _collect_actor_events(db, [actor_id])

    candidate_by_key: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        candidate_by_key.setdefault(candidate["event_key"], candidate)

    event_keys = list(candidate_by_key)
    persisted = (
        db.query(TemporalEvent)
        .filter(
            TemporalEvent.actor_id == actor_id,
            TemporalEvent.event_key.in_(event_keys),
        )
        .all()
        if event_keys
        else []
    )
    persisted_ids = {event.event_key: event.id for event in persisted}

    rows = []
    for candidate in candidate_by_key.values():
        timestamp = candidate["timestamp"]
        if start and timestamp < start:
            continue
        if end and timestamp > end:
            continue
        rows.append(
            {
                "id": persisted_ids.get(candidate["event_key"]),
                "event_key": candidate["event_key"],
                "event_type": candidate["event_type"],
                "entity_type": candidate["entity_type"],
                "entity_id": candidate["entity_id"],
                "timestamp": _iso(timestamp),
                "source": candidate["source"],
                "payload": candidate["payload"],
            }
        )

    rows.sort(
        key=lambda event: (event["timestamp"] or "", event["id"] or 0),
        reverse=True,
    )
    rows = rows[:limit]

    grouped: dict[str, int] = defaultdict(int)
    for event in rows:
        grouped[event["event_type"]] += 1

    return {
        "actor_id": actor_id,
        "total_events": len(rows),
        "event_types": dict(sorted(grouped.items())),
        "events": rows,
        "methodology": (
            "Events are normalized from observed handle lifecycle, wallet, PGP, "
            "trust-link, scanner observation, and scan-target timestamps. "
            "The GET timeline performs no materialization, database writes, or graph synchronization."
        ),
    }
