from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import InvestigatorFeedback
from app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/investigator", tags=["Investigator Feedback"])


@router.get("/feedback", status_code=status.HTTP_200_OK)
def get_feedback(
    actor_id: Optional[str] = Query(None, description="Filter feedback by target actor ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(InvestigatorFeedback)
    if actor_id:
        query = query.filter(InvestigatorFeedback.actor_id == actor_id)

    records = query.order_by(InvestigatorFeedback.id.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "verdict": r.verdict,
            "investigator_id": r.investigator_id,
            "notes": r.notes,
        }
        for r in records
    ]


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    feedback_record = InvestigatorFeedback(
        actor_id=data.actor_id,
        verdict=data.verdict,
        investigator_id=data.investigator_id,
        notes=data.notes,
    )
    db.add(feedback_record)
    db.commit()
    db.refresh(feedback_record)

    return FeedbackResponse(
        status="success",
        message=f"Recorded verdict '{data.verdict}' for actor {data.actor_id}",
        timestamp=datetime.now(timezone.utc),
    )