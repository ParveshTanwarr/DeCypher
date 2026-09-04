from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.database.postgres import get_db
from app.models.sql_models import Observation
from app.models.schemas import (
    ObservationBatchCreate,
    BatchIngestionResponse,
    ObservationResponse,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/scanner", tags=["Scanner Ingestion"], dependencies=[Depends(get_current_user)])


@router.get(
    "/observations",
    response_model=List[ObservationResponse],
    status_code=status.HTTP_200_OK,
)
def get_observations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    target: Optional[str] = Query(None, description="Filter by target host or onion address"),
    indicator_type: Optional[str] = Query(None, description="Filter by indicator type"),
    db: Session = Depends(get_db),
):
    query = db.query(Observation)
    if target:
        query = query.filter(Observation.target.ilike(f"%{target}%"))
    if indicator_type:
        query = query.filter(Observation.indicator_type.ilike(f"%{indicator_type}%"))

    return (
        query.order_by(Observation.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post(
    "/observations",
    response_model=BatchIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_observations(
    payload: ObservationBatchCreate,
    db: Session = Depends(get_db),
):
    if not payload.observations:
        return BatchIngestionResponse(
            status="success",
            inserted_count=0,
            message="No observations provided in payload.",
        )

    # 1. Deduplicate within the payload by observation_id
    deduped_map = {}
    for obs in payload.observations:
        deduped_map[obs.observation_id] = {
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

    records = list(deduped_map.values())

    # 2. Atomic bulk upsert with ON CONFLICT DO NOTHING
    stmt = insert(Observation).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=["observation_id"])
    
    result = db.execute(stmt)
    db.commit()

    # rowcount returns the exact number of new rows successfully inserted
    inserted = result.rowcount

    return BatchIngestionResponse(
        status="success",
        inserted_count=inserted,
        message=f"Successfully ingested {inserted} new scanner observation(s).",
    )