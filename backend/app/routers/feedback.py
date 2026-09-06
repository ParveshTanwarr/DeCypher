from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, InvestigatorFeedback
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


def _apply_feedback_to_score(actor: Actor, verdict: str) -> None:
    """
    Nudges confidence_score/priority_score based on investigator feedback.

    Previously feedback was collected and stored but never affected these
    fields at all -- every actor sat at the same default confidence (0.85)
    and priority (70) regardless of how much investigator review it had
    received. This is a simple, clearly-adjustable starter heuristic (verdict
    is free text -- see FeedbackRequest's docs: "Confirmed", "False
    Positive", "High Risk", etc. -- so this matches on keywords rather than
    a fixed enum). Tune the step sizes/keywords to whatever scoring
    philosophy the team actually wants; the important part is that feedback
    now affects something instead of going nowhere.
    """
    v = (verdict or "").lower()
    confidence = actor.confidence_score if actor.confidence_score is not None else 0.85
    priority = actor.priority_score if actor.priority_score is not None else 70

    if "confirm" in v:
        confidence += 0.05
        priority += 5
    elif "false" in v or "reject" in v or "dismiss" in v:
        confidence -= 0.15
        priority -= 15

    if "high" in v and "risk" in v:
        priority += 10
    elif "low" in v and "risk" in v:
        priority -= 10

    actor.confidence_score = round(min(0.99, max(0.05, confidence)), 4)
    actor.priority_score = int(min(100, max(0, priority)))


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
    feedback_record = InvestigatorFeedback(
        actor_id=actor.actor_id,
        verdict=data.verdict,
        investigator_id=current_user.username,
        notes=data.notes,
    )
    db.add(feedback_record)
    _apply_feedback_to_score(actor, data.verdict)
    db.commit()
    db.refresh(feedback_record)

    return FeedbackResponse(
        status="success",
        message=f"Recorded verdict '{data.verdict}' for actor {actor.actor_id}",
        timestamp=datetime.now(timezone.utc),
    )