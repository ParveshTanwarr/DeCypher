from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Observation
from app.models.schemas import (
    ObservationBatchCreate,
    BatchIngestionResponse,
    ObservationResponse,
)

router = APIRouter(prefix="/scanner", tags=["Scanner Ingestion"])


@router.get(
    "/observations",
    response_model=List[ObservationResponse],
    status_code=status.HTTP_200_OK,
)
def get_observations(
    limit: int = Query(50, ge=1, le=500),
    target: Optional[str] = Query(None, description="Filter by target host or onion address"),
    indicator_type: Optional[str] = Query(None, description="Filter by indicator type"),
    db: Session = Depends(get_db),
):
    query = db.query(Observation)
    if target:
        query = query.filter(Observation.target.ilike(f"%{target}%"))
    if indicator_type:
        query = query.filter(Observation.indicator_type.ilike(f"%{indicator_type}%"))

    return query.order_by(Observation.timestamp.desc()).limit(limit).all()


@router.post(
    "/observations",
    response_model=BatchIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_observations(
    payload: ObservationBatchCreate,
    db: Session = Depends(get_db),
):
    inserted = 0
    for obs in payload.observations:
        exists = (
            db.query(Observation)
            .filter(Observation.observation_id == obs.observation_id)
            .first()
        )
        if not exists:
            db_obs = Observation(
                observation_id=obs.observation_id,
                indicator_type=obs.indicator_type,
                detected=obs.detected,
                value=obs.value,
                target=obs.target,
                source=obs.source,
                timestamp=obs.timestamp or datetime.now(timezone.utc),
                confidence=obs.confidence,
                description=obs.description,
            )
            db.add(db_obs)
            inserted += 1

    db.commit()
    return BatchIngestionResponse(
        status="success",
        inserted_count=inserted,
        message=f"Successfully ingested {inserted} new scanner observation(s).",
    )