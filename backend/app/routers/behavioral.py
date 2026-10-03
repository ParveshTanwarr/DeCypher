from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor
from app.routers.auth import get_current_user, require_role
from app.services.behavioral_profile_service import BehavioralProfileService

router = APIRouter(
    prefix="/actors",
    tags=["Behavioural Profiling"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/{actor_id}/behavioral-profile/refresh",
    dependencies=[Depends(require_role("admin", "investigator"))],
)
def refresh_behavioral_profile(actor_id: str, db: Session = Depends(get_db)):
    actor = (
        db.query(Actor)
        .filter(func.lower(Actor.actor_id) == actor_id.lower())
        .first()
    )
    if actor is None:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")
    return BehavioralProfileService(db).refresh(actor)


@router.get("/{actor_id}/behavioral-profile")
def get_behavioral_profile(actor_id: str, db: Session = Depends(get_db)):
    actor = (
        db.query(Actor)
        .filter(func.lower(Actor.actor_id) == actor_id.lower())
        .first()
    )
    if actor is None:
        raise HTTPException(status_code=404, detail=f"Actor '{actor_id}' not found")
    profile = BehavioralProfileService(db).latest(actor.actor_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="No behavioural profile has been generated yet. Refresh the profile first.",
        )
    return profile
