from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Observation
from app.models.schemas import ObservationBatchCreate, BatchIngestionResponse

router = APIRouter(prefix="/scanner", tags=["Scanner Ingestion"])


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