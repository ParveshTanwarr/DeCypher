from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor
from app.routers.auth import get_current_user
from app.services.graph_anomaly_service import GraphAnomalyService
from app.services.temporal_events import get_actor_timeline, materialize_temporal_events

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/actors/{actor_id}/timeline")
def actor_timeline(
    actor_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(250, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if not db.query(Actor.actor_id).filter(Actor.actor_id == actor_id).first():
        raise HTTPException(status_code=404, detail="Actor not found.")
    materialize_temporal_events(db, actor_id=actor_id)
    db.commit()
    return get_actor_timeline(db, actor_id, start=start, end=end, limit=limit)


@router.get("/actors/{actor_id}/graph-anomaly")
def actor_graph_anomaly(
    actor_id: str,
    db: Session = Depends(get_db),
):
    try:
        return GraphAnomalyService(db).analyze(actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/graph-anomalies")
def graph_anomalies(
    limit: int = Query(25, ge=1, le=250),
    db: Session = Depends(get_db),
):
    return GraphAnomalyService(db).analyze_all(limit=limit)
