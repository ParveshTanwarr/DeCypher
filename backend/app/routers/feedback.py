from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, InvestigatorFeedback
from app.services.correlation_service import CorrelationService
from app.models.schemas import FeedbackRequest, FeedbackResponse
from app.routers.auth import get_current_user, TokenData

# Matches the originally agreed API contract (POST /investigator/feedback) --
# this router used to be mounted at plain "/feedback" instead.
router = APIRouter(
    prefix="/investigator/feedback",
    tags=["Investigator Feedback"],
    dependencies=[Depends(get_current_user)],
)


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
        query = query.filter(func.lower(InvestigatorFeedback.actor_id) == actor_id.lower())

    records = (
        query.order_by(InvestigatorFeedback.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return records


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    data: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    # Verify actor existence first to avoid raw database IntegrityError crashes
    actor = db.query(Actor).filter(func.lower(Actor.actor_id) == data.actor_id.lower()).first()
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot submit feedback: Actor '{data.actor_id}' does not exist.",
        )

    # investigator_id comes from the verified token, not the request body --
    # previously it was a free-text field the caller supplied directly, so
    # anyone with valid credentials could submit feedback "as" any
    # investigator name they typed in, with no link to who was actually
    # logged in.
    # Preserve the persisted confidence before recalculation so the
    # investigator verdict remains an adjustment to the actor's current
    # triage state rather than being lost when evidence is recomputed.
    previous_confidence = actor.confidence_score if actor.confidence_score is not None else 0.85

    feedback_record = InvestigatorFeedback(
        actor_id=actor.actor_id,
        verdict=data.verdict,
        investigator_id=current_user.username,
        notes=data.notes,
    )
    db.add(feedback_record)
    db.commit()
    db.refresh(feedback_record)

    # Recompute through the same correlation path used by the dashboard.
    # The latest verdict is kept as a separate human-input triage adjustment.
    correlation_service = CorrelationService(db)
    correlation_service.correlate_actor(actor.actor_id, persist=True)

    # Correlation recomputation can legitimately produce a different
    # evidence-only score. Human feedback is intentionally applied on top
    # of the persisted pre-feedback confidence so a confirmed verdict
    # cannot be erased by that recalculation.
    confidence_adjustment = correlation_service._feedback_confidence_adjustment(actor.actor_id)
    actor.confidence_score = round(
        max(0.0, min(1.0, previous_confidence + confidence_adjustment["confidence_delta"])),
        4,
    )
    db.commit()

    return FeedbackResponse(
        status="success",
        message=f"Recorded verdict '{data.verdict}' for actor {actor.actor_id}",
        timestamp=datetime.now(timezone.utc),
    )