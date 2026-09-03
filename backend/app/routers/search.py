from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("")
def global_search(
    q: str = Query(..., min_length=2, description="Search term (handle, wallet, or actor ID)"),
    db: Session = Depends(get_db),
):
    search_pattern = f"%{q}%"
    results: List[Dict[str, Any]] = []
    seen_actor_ids = set()

    # 1. Search matching Actor IDs or Primary Handles
    direct_actors = (
        db.query(Actor)
        .filter(
            (Actor.actor_id.ilike(search_pattern))
            | (Actor.primary_handle.ilike(search_pattern))
        )
        .all()
    )
    for actor in direct_actors:
        seen_actor_ids.add(actor.actor_id)
        results.append({
            "type": "actor",
            "id": actor.actor_id,
            "matched_handle": actor.primary_handle,
            "risk_category": actor.risk_category,
        })

    # 2. Search DarkWeb handles
    matched_handles = (
        db.query(DarkWebHandle)
        .filter(DarkWebHandle.handle.ilike(search_pattern))
        .all()
    )
    for h in matched_handles:
        if h.actor_id and h.actor_id not in seen_actor_ids:
            actor = db.query(Actor).filter(Actor.actor_id == h.actor_id).first()
            if actor:
                seen_actor_ids.add(actor.actor_id)
                results.append({
                    "type": "actor",
                    "id": actor.actor_id,
                    "matched_handle": h.handle,
                    "risk_category": actor.risk_category,
                })

    # 3. Search Wallets
    matched_wallets = (
        db.query(Wallet)
        .filter(Wallet.address.ilike(search_pattern))
        .all()
    )
    for w in matched_wallets:
        if w.actor_id and w.actor_id not in seen_actor_ids:
            actor = db.query(Actor).filter(Actor.actor_id == w.actor_id).first()
            if actor:
                seen_actor_ids.add(actor.actor_id)
                results.append({
                    "type": "actor",
                    "id": actor.actor_id,
                    "matched_handle": actor.primary_handle,
                    "risk_category": actor.risk_category,
                })

    return {"query": q, "total_matches": len(results), "results": results}