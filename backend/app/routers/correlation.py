from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.services.correlation_service import CorrelationService


router = APIRouter(
    prefix="/correlation",
    tags=["correlation"],
)


@router.get("/actor/{actor_id}")
def correlate_actor(
    actor_id: str,
    handle_a: str | None = Query(default=None),
    handle_b: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Generate an evidence-correlation score for an actor.

    When handle_a and handle_b are supplied, the endpoint also runs
    the project's authorship/NLP engine and incorporates its score.
    """

    service = CorrelationService(db)

    try:
        return service.correlate_actor(
            actor_id,
            handle_a=handle_a,
            handle_b=handle_b,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.get("/actors")
def correlate_all_actors(
    db: Session = Depends(get_db),
):
    """
    Rank all actors by available correlation evidence.
    """

    service = CorrelationService(db)

    return {
        "results": service.correlate_all(),
    }