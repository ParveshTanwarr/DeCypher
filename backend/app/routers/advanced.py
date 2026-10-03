from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database.postgres import get_db
from app.models.advanced_models import Alert, CollectionSource, ExternalEntity, EntityLink
from app.models.sql_models import Actor
from app.routers.auth import get_current_user, require_role
from app.services.advanced_intelligence import (
    AlertService,
    CollectionService,
    EntityLinkageService,
    EvaluationService,
    MediaCorrelationService,
    MerkleEvidenceService,
    StylometryDiscoveryService,
    TorIntelligenceService,
)
from app.services.correlation_service import CorrelationService
from app.services.nlp_service import nlp_service
from app.services.historical_cases import HistoricalCaseService

router = APIRouter(tags=["Advanced Intelligence"])


class CollectionSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    kind: str = Field(..., pattern="^(json|rss|html|tor_http)$")
    url: str = Field(..., min_length=8, max_length=1024)
    actor_id: Optional[str] = Field(None, max_length=64)
    enabled: bool = True
    interval_minutes: int = Field(15, ge=1, le=10080)
    headers: dict[str, str] = Field(default_factory=dict)
    parser_config: dict[str, Any] = Field(default_factory=dict)


class HistoricalCase(BaseModel):
    case_id: str
    handle_a: str
    handle_b: str
    expected_same_actor: bool
    threshold: float = Field(0.65, ge=0.0, le=1.0)


class MediaFingerprintRequest(BaseModel):
    media_id: str = Field(..., min_length=1, max_length=128)
    data_url: str = Field(..., min_length=32)
    source: str = Field("investigator_upload", min_length=1, max_length=128)
    actor_id: Optional[str] = Field(None, max_length=64)


class MediaCompareRequest(BaseModel):
    media_a: str
    media_b: str


class AblationRequest(BaseModel):
    disabled_signals: list[str] = Field(default_factory=list)


def _require_actor(db: Session, actor_id: str) -> Actor:
    actor = db.query(Actor).filter(Actor.actor_id == actor_id).first()
    if actor is None:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found.")
    return actor


@router.get(
    "/integrity/merkle-status",
    dependencies=[Depends(get_current_user)],
)
def merkle_status(db: Session = Depends(get_db)):
    verification = MerkleEvidenceService(db).verify()
    return {
        "blockchain_mode": "internal_merkle_blockchain_style_ledger",
        "external_anchor_configured": bool(
            settings.BLOCKCHAIN_ANCHOR_RPC_URL and settings.BLOCKCHAIN_ANCHOR_CONTRACT
        ),
        **verification,
    }


@router.get(
    "/historical-cases",
    dependencies=[Depends(get_current_user)],
)
def list_historical_cases():
    return HistoricalCaseService.list_cases()


@router.get(
    "/historical-cases/{case_id}",
    dependencies=[Depends(get_current_user)],
)
def get_historical_case(case_id: str):
    case = HistoricalCaseService.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Historical case '{case_id}' not found.")
    return case


@router.get(
    "/historical-cases/context/actor/{actor_id}",
    dependencies=[Depends(get_current_user)],
)
def historical_case_context_for_actor(actor_id: str, db: Session = Depends(get_db)):
    if db.query(Actor.actor_id).filter(Actor.actor_id == actor_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found.")
    return {
        "actor_id": actor_id,
        "matches": HistoricalCaseService.match_actor(db, actor_id),
        "note": "Historical-case context is read-only provenance metadata. It is shown only when the actor's recorded handles match documented case aliases.",
    }


@router.get(
    "/historical-cases/context",
    dependencies=[Depends(get_current_user)],
)
def historical_case_context(
    handles: list[str] = Query(default=[]),
):
    return {
        "matches": HistoricalCaseService.match_handles(handles),
        "note": "Historical-case context is read-only provenance metadata. It is shown only when supplied handles match documented case aliases.",
    }


@router.post(
    "/integrity/merkle-seal",
    dependencies=[Depends(require_role("admin"))],
)
def merkle_seal(db: Session = Depends(get_db)):
    created = MerkleEvidenceService(db).seal_pending()
    db.commit()
    return {"blocks_created": created, **MerkleEvidenceService(db).verify()}


@router.get(
    "/integrity/merkle-verify",
    dependencies=[Depends(get_current_user)],
)
def merkle_verify(db: Session = Depends(get_db)):
    return MerkleEvidenceService(db).verify()


@router.post(
    "/collection/sources",
    dependencies=[Depends(require_role("admin"))],
)
def create_collection_source(payload: CollectionSourceCreate, db: Session = Depends(get_db)):
    if payload.actor_id:
        _require_actor(db, payload.actor_id)
    existing = db.query(CollectionSource).filter(CollectionSource.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Collection source name already exists.")
    source = CollectionSource(
        name=payload.name,
        kind=payload.kind,
        url=payload.url,
        actor_id=payload.actor_id,
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        headers=payload.headers,
        parser_config=payload.parser_config,
        next_run_at=datetime.now(timezone.utc),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get(
    "/collection/sources",
    dependencies=[Depends(get_current_user)],
)
def list_collection_sources(db: Session = Depends(get_db)):
    return db.query(CollectionSource).order_by(CollectionSource.id.asc()).all()


@router.post(
    "/collection/sources/{source_id}/run",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def run_collection_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(CollectionSource).filter(CollectionSource.id == source_id).first()
    if source is None:
        raise HTTPException(status_code=404, detail="Collection source not found.")
    try:
        return CollectionService(db).run_source(source)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get(
    "/collection/runs",
    dependencies=[Depends(get_current_user)],
)
def collection_runs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    from app.models.advanced_models import CollectionRun
    return db.query(CollectionRun).order_by(CollectionRun.id.desc()).limit(limit).all()


@router.get(
    "/collection/status",
    dependencies=[Depends(get_current_user)],
)
def collection_status(db: Session = Depends(get_db)):
    sources = db.query(CollectionSource).all()
    return {
        "enabled": settings.COLLECTION_ENABLED,
        "poll_interval_minutes": settings.COLLECTION_POLL_INTERVAL_MINUTES,
        "sources": len(sources),
        "enabled_sources": sum(1 for source in sources if source.enabled),
        "continuous_collection": "celery_beat + redis",
    }


@router.post(
    "/tor/inspect",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def inspect_tor(url: str, db: Session = Depends(get_db)):
    try:
        result = TorIntelligenceService().inspect_onion(url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    AlertService(db).create(
        alert_type="tor_observation",
        severity="medium",
        title="Tor target inspected",
        message=f"Authorized Tor observation completed for {urlparse(url).hostname}.",
        payload=result,
    )
    db.commit()
    return result


@router.post(
    "/tor/descriptor/parse",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def parse_tor_descriptor(descriptor: str):
    return TorIntelligenceService.parse_descriptor(descriptor)


@router.post(
    "/correlation/stylometry-discovery",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def stylometry_discovery(
    limit: int = Query(100, ge=1, le=500),
    actor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return {
        "results": StylometryDiscoveryService(db).discover(limit=limit, actor_id=actor_id),
        "model_status": nlp_service.engine_status,
    }


@router.post(
    "/correlation/actor/{actor_id}/ablation",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def evidence_ablation(
    actor_id: str,
    payload: AblationRequest,
    db: Session = Depends(get_db),
):
    actor = _require_actor(db, actor_id)
    base = CorrelationService(db).correlate_actor(actor.actor_id, persist=False)
    disabled = {name.strip() for name in payload.disabled_signals if name.strip()}
    remaining = [signal for signal in base["signals"] if signal["type"] not in disabled]
    score = CorrelationService(db)._weighted_score(remaining)
    if base.get("deconfliction", {}).get("contradiction_flag"):
        score = max(0.0, score - 0.15)
    priority = CorrelationService(db).calculate_priority(actor, score, remaining)
    return {
        "actor_id": actor_id,
        "disabled_signals": sorted(disabled),
        "baseline_score": base["overall_confidence"],
        "ablated_score": round(score, 4),
        "delta": round(score - base["overall_confidence"], 4),
        "remaining_signals": remaining,
        "priority": priority,
        "interpretation": "Interactive evidence ablation recomputes the current evidence-fusion score with selected signals disabled. It is sensitivity analysis, not a causal effect or identity proof.",
    }


@router.get(
    "/evaluation/calibration",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def calibration(
    pairs: int = Query(100, ge=20, le=500),
    db: Session = Depends(get_db),
):
    return EvaluationService(db).calibration(pairs=pairs)


@router.post(
    "/evaluation/historical-cases",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def historical_case_validation(cases: list[HistoricalCase], db: Session = Depends(get_db)):
    return EvaluationService(db).historical_cases([case.model_dump() for case in cases])


@router.get(
    "/entities",
    dependencies=[Depends(get_current_user)],
)
def list_entities(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(ExternalEntity)
    if entity_type:
        query = query.filter(ExternalEntity.entity_type == entity_type)
    return query.order_by(ExternalEntity.id.desc()).limit(limit).all()


@router.post(
    "/entities/link/actor/{actor_id}",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def link_entities(actor_id: str, db: Session = Depends(get_db)):
    _require_actor(db, actor_id)
    return {"actor_id": actor_id, "links": EntityLinkageService(db).link_actor(actor_id)}


@router.get(
    "/entities/actor/{actor_id}",
    dependencies=[Depends(get_current_user)],
)
def actor_entity_links(actor_id: str, db: Session = Depends(get_db)):
    _require_actor(db, actor_id)
    rows = (
        db.query(EntityLink, ExternalEntity)
        .join(ExternalEntity, EntityLink.entity_id == ExternalEntity.id)
        .filter(EntityLink.actor_id == actor_id)
        .order_by(EntityLink.score.desc())
        .all()
    )
    return [
        {
            "entity_id": entity.id,
            "entity_type": entity.entity_type,
            "canonical_value": entity.canonical_value,
            "source": entity.source,
            "score": link.score,
            "match_type": link.match_type,
            "explanation": link.explanation,
        }
        for link, entity in rows
    ]


@router.post(
    "/media/fingerprint",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def media_fingerprint(payload: MediaFingerprintRequest, db: Session = Depends(get_db)):
    try:
        return MediaCorrelationService(db).ingest(
            payload.media_id,
            payload.data_url,
            payload.source,
            payload.actor_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/media/compare",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def media_compare(payload: MediaCompareRequest, db: Session = Depends(get_db)):
    try:
        return MediaCorrelationService(db).compare(payload.media_a, payload.media_b)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/alerts",
    dependencies=[Depends(get_current_user)],
)
def recent_alerts(
    since_id: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": alert.id,
            "actor_id": alert.actor_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "payload": alert.payload,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }
        for alert in (
            db.query(Alert)
            .filter(Alert.id > since_id)
            .order_by(Alert.id.asc())
            .limit(limit)
            .all()
        )
    ]


@router.websocket("/alerts/ws")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    db: Session | None = None
    try:
        token_message = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        from jose import JWTError, jwt
        from app.config import settings as app_settings
        try:
            payload = jwt.decode(token_message.strip(), app_settings.SECRET_KEY, algorithms=[app_settings.ALGORITHM])
            if not payload.get("sub"):
                raise JWTError()
        except JWTError:
            await websocket.send_json({"error": "invalid_token"})
            await websocket.close(code=1008)
            return
        from app.database.postgres import SessionLocal
        db = SessionLocal()
        last_id = 0
        while True:
            rows = (
                db.query(Alert)
                .filter(Alert.id > last_id)
                .order_by(Alert.id.asc())
                .limit(50)
                .all()
            )
            for alert in rows:
                await websocket.send_json({
                    "id": alert.id,
                    "actor_id": alert.actor_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "message": alert.message,
                    "payload": alert.payload,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                })
                last_id = alert.id
            await asyncio.sleep(2)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        return
    finally:
        if db:
            db.close()
