from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.routers.auth import get_current_user
from app.services.correlation_service import CorrelationService

router = APIRouter(
    prefix="/correlation",
    tags=["correlation"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/actor/{actor_id}")
def correlate_actor(
    actor_id: str,
    handle_a: str | None = Query(default=None),
    handle_b: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = CorrelationService(db)
    try:
        return service.correlate_actor(actor_id, handle_a=handle_a, handle_b=handle_b)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/actors")
def correlate_all_actors(db: Session = Depends(get_db)):
    service = CorrelationService(db)
    return {"results": service.correlate_all()}
