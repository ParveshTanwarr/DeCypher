from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, InvestigatorFeedback
from app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Investigator Feedback"])


class FeedbackItem(BaseModel):
    id: int
    actor_id: str
    verdict: str
    investigator_id: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[FeedbackItem], status_code=status.HTTP_200_OK)
def get_feedback(
    actor_id: Optional[str] = Query(None, description="Filter feedback by target actor ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(InvestigatorFeedback)
    if actor_id:
        query = query.filter(InvestigatorFeedback.actor_id.ilike(actor_id))

    records = (
        query.order_by(InvestigatorFeedback.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return records


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    # Verify actor existence first to avoid raw database IntegrityError crashes
    actor = db.query(Actor).filter(Actor.actor_id.ilike(data.actor_id)).first()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot submit feedback: Actor '{data.actor_id}' does not exist.",
        )

    feedback_record = InvestigatorFeedback(
        actor_id=actor.actor_id,
        verdict=data.verdict,
        investigator_id=data.investigator_id,
        notes=data.notes,
    )
    db.add(feedback_record)
    db.commit()
    db.refresh(feedback_record)

    return FeedbackResponse(
        status="success",
        message=f"Recorded verdict '{data.verdict}' for actor {actor.actor_id}",
        timestamp=datetime.now(timezone.utc),
    )