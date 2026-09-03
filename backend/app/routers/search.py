from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet

router = APIRouter(prefix="/search", tags=["Search"])


class SearchResultItem(BaseModel):
    type: str
    id: str
    matched_value: str
    risk_category: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    results: List[SearchResultItem]


@router.get("", response_model=SearchResponse)
def global_search(
    q: str = Query(..., min_length=2, description="Search term (handle, wallet, or actor ID)"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    db: Session = Depends(get_db),
):
    search_pattern = f"%{q}%"
    results: List[SearchResultItem] = []
    seen_actor_ids = set()

    # 1. Search matching Actor IDs or Primary Handles
    direct_actors = (
        db.query(Actor)
        .filter(
            (Actor.actor_id.ilike(search_pattern))
            | (Actor.primary_handle.ilike(search_pattern))
        )
        .limit(limit)
        .all()
    )
    for actor in direct_actors:
        seen_actor_ids.add(actor.actor_id)
        results.append(
            SearchResultItem(
                type="actor",
                id=actor.actor_id,
                matched_value=actor.primary_handle,
                risk_category=actor.risk_category,
            )
        )

    # 2. Search DarkWeb handles via JOIN (single query, no N+1)
    if len(results) < limit:
        remaining = limit - len(results)
        matched_handles = (
            db.query(DarkWebHandle, Actor)
            .join(Actor, DarkWebHandle.actor_id == Actor.actor_id)
            .filter(DarkWebHandle.handle.ilike(search_pattern))
            .limit(remaining)
            .all()
        )
        for handle, actor in matched_handles:
            if actor.actor_id not in seen_actor_ids:
                seen_actor_ids.add(actor.actor_id)
                results.append(
                    SearchResultItem(
                        type="handle",
                        id=actor.actor_id,
                        matched_value=handle.handle,
                        risk_category=actor.risk_category,
                    )
                )

    # 3. Search Wallets via JOIN (single query, no N+1)
    if len(results) < limit:
        remaining = limit - len(results)
        matched_wallets = (
            db.query(Wallet, Actor)
            .join(Actor, Wallet.actor_id == Actor.actor_id)
            .filter(Wallet.address.ilike(search_pattern))
            .limit(remaining)
            .all()
        )
        for wallet, actor in matched_wallets:
            if actor.actor_id not in seen_actor_ids:
                seen_actor_ids.add(actor.actor_id)
                results.append(
                    SearchResultItem(
                        type="wallet",
                        id=actor.actor_id,
                        matched_value=wallet.address,
                        risk_category=actor.risk_category,
                    )
                )

    return SearchResponse(query=q, total_matches=len(results), results=results)