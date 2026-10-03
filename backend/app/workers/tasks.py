"""Background tasks for authorized autonomous infrastructure scanning."""

from __future__ import annotations
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from celery import Task
from sqlalchemy.dialects.postgresql import insert
from app.config import settings
from app.database.postgres import SessionLocal
from app.models.sql_models import Actor, Observation, ScanJob, ScanTarget
from app.services import graph_service
from app.services.correlation_service import CorrelationService
from app.workers.celery_app import celery_app
from infra.target_policy import validate_scan_target

PROJECT_ROOT = Path(__file__).resolve().parents[3]

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _allowed_hosts() -> set[str]:
    return {x.strip().lower() for x in settings.AUTOSCAN_ALLOWED_HOSTS.split(",") if x.strip()}

def validate_authorized_target(target_url: str) -> None:
    validate_scan_target(target_url, _allowed_hosts())

def effective_scan_interval_minutes(target: ScanTarget, priority_score: int | None) -> int:
    base = max(5, int(target.interval_minutes or settings.AUTOSCAN_DEFAULT_INTERVAL_MINUTES))
    if not target.priority_aware or priority_score is None:
        return base
    if priority_score >= 85:
        priority_interval = 15
    elif priority_score >= 70:
        priority_interval = 30
    elif priority_score >= 50:
        priority_interval = 60
    else:
        priority_interval = 180
    return max(5, min(base, priority_interval))

def _load_scanner():
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from infra.scanner import scan_target
    return scan_target

def run_authorized_scan(target_url: str, actor_id: str | None) -> list[dict[str, Any]]:
    validate_authorized_target(target_url)
    raw_observations = _load_scanner()(target_url)
    mapped = []
    for raw in raw_observations:
        actual_target = str(raw.get("target") or target_url)
        description = str(raw.get("evidence") or "").strip()
        if actual_target and actual_target not in description:
            description = f"{description} Target: {actual_target}.".strip()
        if raw.get("clearnet_match_domain"):
            description = f"{description} Clearnet match: {raw['clearnet_match_domain']}.".strip()
        mapped.append({
            "observation_id": raw.get("observation_id"),
            "indicator_type": raw.get("indicator_type", "infrastructure"),
            "detected": bool(raw.get("detected", False)),
            "value": raw.get("observed_value"),
            "target": actor_id or target_url,
            "source": raw.get("source", "authorized-test-service"),
            "timestamp": (datetime.fromisoformat(str(raw.get("scan_date")).replace("Z", "+00:00")) if raw.get("scan_date") else utc_now()),
            "confidence": raw.get("confidence", 0.0),
            "description": description or "Authorized infrastructure scan result.",
        })
    return mapped

def _persist_observations(db, observations: list[dict[str, Any]]) -> int:
    if not observations:
        return 0
    stmt = insert(Observation).values(observations).on_conflict_do_nothing(index_elements=["observation_id"])
    result = db.execute(stmt)
    return int(result.rowcount or 0)

@celery_app.task(bind=True, name="decypher.run_authorized_scan")
def run_authorized_scan_task(self: Task, job_id: int) -> dict[str, Any]:
    db = SessionLocal()
    job = None
    target = None
    try:
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job:
            raise ValueError(f"Scan job {job_id} does not exist.")
        target = db.query(ScanTarget).filter(ScanTarget.id == job.target_id).first()
        if not target:
            raise ValueError(f"Scan target {job.target_id} does not exist.")
        if not target.enabled:
            job.status = "cancelled"
            job.completed_at = utc_now()
            job.error = "Scan target is disabled."
            db.commit()
            return {"job_id": job.id, "status": "cancelled", "findings_count": 0}

        job.status = "running"
        job.started_at = utc_now()
        job.celery_task_id = self.request.id
        target.last_status = "running"
        target.last_error = None
        db.commit()

        observations = run_authorized_scan(target.target_url, target.actor_id)
        inserted = _persist_observations(db, observations)

        # Keep the evidence row and its tamper-evident ledger record in the
        # same PostgreSQL transaction. A later failure rolls both back.
        from app.services.evidence_ledger import EvidenceLedgerService
        EvidenceLedgerService(db).append_missing_for_observations(
            observations,
            actor_id=target.actor_id,
            created_by="autoscan_worker",
        )

        if target.actor_id:
            try:
                graph_service.sync_actor_observations(target.actor_id, observations)
            except Exception as exc:
                print(f"[autoscan] Neo4j sync warning: {exc}")

        priority_score = None
        correlation_score = None
        if target.actor_id:
            correlation = CorrelationService(db).correlate_actor(target.actor_id)
            correlation_score = correlation.get("overall_confidence")
            priority_score = (correlation.get("priority") or {}).get("score")

        now = utc_now()
        job.status = "completed"
        job.completed_at = now
        job.findings_count = inserted
        job.correlation_score = correlation_score
        job.priority_score = priority_score
        job.error = None
        target.last_scan_at = now
        target.last_status = "completed"
        target.last_error = None
        target.consecutive_failures = 0
        target.next_run_at = now + timedelta(minutes=effective_scan_interval_minutes(target, priority_score))
        db.commit()

        return {"job_id": job.id, "status": "completed", "findings_count": inserted,
                "correlation_score": correlation_score, "priority_score": priority_score}
    except Exception as exc:
        db.rollback()
        now = utc_now()
        if job is not None:
            job = db.query(ScanJob).filter(ScanJob.id == job.id).first()
            if job:
                job.status = "failed"
                job.completed_at = now
                job.error = str(exc)[:2000]
        if target is not None:
            target = db.query(ScanTarget).filter(ScanTarget.id == target.id).first()
            if target:
                target.last_scan_at = now
                target.last_status = "failed"
                target.last_error = str(exc)[:2000]
                target.consecutive_failures = int(target.consecutive_failures or 0) + 1
                target.next_run_at = now + timedelta(minutes=5)
        db.commit()
        raise
    finally:
        db.close()

@celery_app.task(name="decypher.dispatch_due_scans")
def dispatch_due_scans() -> dict[str, Any]:
    if not settings.AUTOSCAN_ENABLED:
        return {"status": "disabled", "queued": 0, "failures": 0}

    db = SessionLocal()
    queued = 0
    failures = 0
    now = utc_now()
    try:
        targets = (
            db.query(ScanTarget)
            .filter(ScanTarget.enabled.is_(True), ScanTarget.next_run_at <= now)
            .order_by(ScanTarget.next_run_at.asc(), ScanTarget.id.asc())
            .with_for_update(skip_locked=True)
            .limit(25)
            .all()
        )
        for target in targets:
            try:
                validate_authorized_target(target.target_url)
                actor = db.query(Actor).filter(Actor.actor_id == target.actor_id).first() if target.actor_id else None
                priority = actor.priority_score if actor else None
                target.next_run_at = now + timedelta(minutes=effective_scan_interval_minutes(target, priority))
                target.last_status = "queued"
                target.last_error = None
                job = ScanJob(target_id=target.id, actor_id=target.actor_id, status="queued", queued_at=now)
                db.add(job)
                db.flush()
                db.commit()
                try:
                    result = run_authorized_scan_task.delay(job.id)
                    job = db.query(ScanJob).filter(ScanJob.id == job.id).first()
                    if job:
                        job.celery_task_id = result.id
                        db.commit()
                    queued += 1
                except Exception as exc:
                    db.rollback()
                    job = db.query(ScanJob).filter(ScanJob.id == job.id).first()
                    target = db.query(ScanTarget).filter(ScanTarget.id == target.id).first()
                    if job:
                        job.status = "failed"
                        job.completed_at = utc_now()
                        job.error = f"Queue publish failed: {exc}"[:2000]
                    if target:
                        target.last_status = "failed"
                        target.last_error = "Unable to publish scan job to Redis/Celery."
                        target.next_run_at = utc_now() + timedelta(minutes=5)
                    db.commit()
                    failures += 1
            except Exception as exc:
                db.rollback()
                target = db.query(ScanTarget).filter(ScanTarget.id == target.id).first()
                if target:
                    target.last_status = "failed"
                    target.last_error = str(exc)[:2000]
                    target.next_run_at = now + timedelta(minutes=5)
                    db.commit()
                failures += 1
        return {"status": "ok", "queued": queued, "failures": failures}
    finally:
        db.close()
