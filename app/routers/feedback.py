from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.postgres import get_db
from app.models.sql_models import InvestigatorFeedback
from app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/investigator", tags=["Investigator Feedback"])

@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    feedback_record = InvestigatorFeedback(
        actor_id=data.actor_id,
        verdict=data.verdict,
        investigator_id=data.investigator_id,
        notes=data.notes
    )
    db.add(feedback_record)
    db.commit()
    db.refresh(feedback_record)

    return FeedbackResponse(
        status="success",
        message=f"Recorded verdict '{data.verdict}' for actor {data.actor_id}",
        timestamp=datetime.utcnow()
    )