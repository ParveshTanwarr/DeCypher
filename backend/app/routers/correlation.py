from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.routers.auth import get_current_user, require_role
from app.services.correlation_service import CorrelationService

router = APIRouter(
    prefix="/correlation",
    tags=["correlation"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/actor/{actor_id}")
def correlate_actor(
    actor_id: str,
    handle_a: Optional[str] = Query(default=None),
    handle_b: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    service = CorrelationService(db)
    try:
        return service.correlate_actor(actor_id, handle_a=handle_a, handle_b=handle_b, persist=False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))



@router.get("/actor/{actor_id}/counterfactual")
def correlate_actor_counterfactual(
    actor_id: str,
    handle_a: Optional[str] = Query(default=None),
    handle_b: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    service = CorrelationService(db)
    try:
        result = service.correlate_actor(
            actor_id,
            handle_a=handle_a,
            handle_b=handle_b,
            persist=False,
        )
        return {
            "candidate_actor": result["candidate_actor"],
            "counterfactual": result["counterfactual"],
            "source_reliability": result.get("source_reliability", {}),
            "interpretation": (
                "Counterfactual output is leave-one-signal-out sensitivity "
                "analysis of the current weighted evidence set. It is not a "
                "causal effect or identity determination."
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))



@router.post("/actor/{actor_id}/refresh")
def refresh_actor_correlation(
    actor_id: str,
    handle_a: Optional[str] = Query(default=None),
    handle_b: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _current_user = Depends(require_role("admin", "investigator")),
):
    service = CorrelationService(db)
    try:
        return service.correlate_actor(
            actor_id,
            handle_a=handle_a,
            handle_b=handle_b,
            persist=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/actors/refresh")
def refresh_all_correlations(
    db: Session = Depends(get_db),
    _current_user = Depends(require_role("admin", "investigator")),
):
    return {"results": CorrelationService(db).correlate_all(persist=True)}


@router.get("/actors")
def correlate_all_actors(db: Session = Depends(get_db)):
    service = CorrelationService(db)
    return {"results": service.correlate_all(persist=False)}
