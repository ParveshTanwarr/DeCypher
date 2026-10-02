from datetime import datetime, timezone
from typing import List, Optional

from celery.exceptions import CeleryError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Observation, ScanJob, ScanTarget
from app.models.schemas import ObservationBatchCreate, BatchIngestionResponse, ObservationResponse
from app.routers.auth import get_current_user, require_role
from app.workers.tasks import run_authorized_scan_task, validate_authorized_target

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"],
    dependencies=[Depends(get_current_user)],
)


class ScanTargetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    target_url: str = Field(..., min_length=8, max_length=512)
    actor_id: Optional[str] = Field(None, max_length=64)
    interval_minutes: int = Field(180, ge=5, le=10080)
    priority_aware: bool = True
    enabled: bool = True


class ScanTargetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    target_url: str
    actor_id: Optional[str]
    enabled: bool
    interval_minutes: int
    priority_aware: bool
    next_run_at: datetime
    last_scan_at: Optional[datetime]
    last_status: str
    last_error: Optional[str]
    consecutive_failures: int


class ScanJobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    target_id: int
    actor_id: Optional[str]
    celery_task_id: Optional[str]
    status: str
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    findings_count: int
    correlation_score: Optional[float]
    priority_score: Optional[int]
    error: Optional[str]


@router.get(
    "/observations",
    response_model=List[ObservationResponse],
    status_code=status.HTTP_200_OK,
)
def get_observations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    target: Optional[str] = Query(None),
    indicator_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Observation)
    if target:
        query = query.filter(Observation.target.ilike(f"%{target}%"))
    if indicator_type:
        query = query.filter(Observation.indicator_type.ilike(f"%{indicator_type}%"))
    return query.order_by(Observation.timestamp.desc()).offset(offset).limit(limit).all()


@router.post(
    "/observations",
    response_model=BatchIngestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "service"))],
)
def ingest_observations(
    payload: ObservationBatchCreate,
    db: Session = Depends(get_db),
):
    if not payload.observations:
        return BatchIngestionResponse(inserted_count=0, message="No observations provided in payload.")

    if payload.actor_id:
        from app.models.sql_models import Actor
        if not db.query(Actor).filter(Actor.actor_id == payload.actor_id).first():
            raise HTTPException(status_code=404, detail=f"Actor '{payload.actor_id}' not found.")

    deduped = {}
    for obs in payload.observations:
        deduped[obs.observation_id] = {
            "observation_id": obs.observation_id,
            "indicator_type": obs.indicator_type,
            "detected": obs.detected,
            "value": obs.value,
            "target": obs.target,
            "source": obs.source,
            "timestamp": obs.timestamp or datetime.now(timezone.utc),
            "confidence": obs.confidence,
            "description": obs.description,
        }

    stmt = insert(Observation).values(list(deduped.values()))
    stmt = stmt.on_conflict_do_nothing(index_elements=["observation_id"])
    result = db.execute(stmt)

    # Keep observation storage and its integrity record in one transaction.
    from app.services.evidence_ledger import EvidenceLedgerService
    EvidenceLedgerService(db).append_missing_for_observations(
        deduped.values(),
        actor_id=payload.actor_id,
        created_by="scanner_api",
    )
    db.commit()

    if payload.actor_id:
        from app.services import graph_service

        try:
            graph_service.sync_actor_observations(payload.actor_id, list(deduped.values()))
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Observations were stored in PostgreSQL but Neo4j synchronization failed: {exc}",
            )

    return BatchIngestionResponse(
        inserted_count=int(result.rowcount or 0),
        message=f"Successfully ingested {int(result.rowcount or 0)} new scanner observation(s).",
    )


@router.post(
    "/targets",
    response_model=ScanTargetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "service"))],
)
def create_scan_target(payload: ScanTargetCreate, db: Session = Depends(get_db)):
    try:
        validate_authorized_target(payload.target_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if payload.actor_id:
        from app.models.sql_models import Actor
        if not db.query(Actor).filter(Actor.actor_id == payload.actor_id).first():
            raise HTTPException(status_code=404, detail=f"Actor '{payload.actor_id}' not found.")

    if db.query(ScanTarget).filter(
        (ScanTarget.name == payload.name) | (ScanTarget.target_url == payload.target_url)
    ).first():
        raise HTTPException(status_code=409, detail="A scan target with this name or URL already exists.")

    now = datetime.now(timezone.utc)
    target = ScanTarget(
        name=payload.name,
        target_url=payload.target_url,
        actor_id=payload.actor_id,
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        priority_aware=payload.priority_aware,
        next_run_at=now,
        last_status="never",
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get(
    "/targets",
    response_model=List[ScanTargetResponse],
)
def list_scan_targets(db: Session = Depends(get_db)):
    return db.query(ScanTarget).order_by(ScanTarget.id.asc()).all()


@router.post(
    "/targets/{target_id}/run",
    response_model=ScanJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_role("admin", "service"))],
)
def queue_scan_target(target_id: int, db: Session = Depends(get_db)):
    target = db.query(ScanTarget).filter(ScanTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Scan target not found.")
    if not target.enabled:
        raise HTTPException(status_code=409, detail="Scan target is disabled.")

    try:
        validate_authorized_target(target.target_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    job = ScanJob(
        target_id=target.id,
        actor_id=target.actor_id,
        status="queued",
        queued_at=datetime.now(timezone.utc),
    )
    target.last_status = "queued"
    target.last_error = None
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        result = run_authorized_scan_task.delay(job.id)
    except (CeleryError, Exception) as exc:
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        job.error = f"Unable to queue Celery task: {exc}"[:2000]
        target.last_status = "failed"
        target.last_error = job.error
        db.commit()
        raise HTTPException(status_code=503, detail="Celery/Redis is unavailable. Start the worker infrastructure and retry.")

    job.celery_task_id = result.id
    db.commit()
    db.refresh(job)
    return job


@router.get(
    "/jobs",
    response_model=List[ScanJobResponse],
)
def list_scan_jobs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return db.query(ScanJob).order_by(ScanJob.id.desc()).limit(limit).all()


@router.get(
    "/jobs/{job_id}",
    response_model=ScanJobResponse,
)
def get_scan_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found.")
    return job
