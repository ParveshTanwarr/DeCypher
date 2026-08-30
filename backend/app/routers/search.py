from fastapi import APIRouter, Query
from typing import List, Dict, Any
from app.routers.actors import MOCK_ACTORS

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("")
def global_search(q: str = Query(..., min_length=2, description="Search term (handle, wallet, or actor ID)")):
    results: List[Dict[str, Any]] = []
    term = q.lower()

    for actor in MOCK_ACTORS:
        if term in actor.actor_id.lower() or any(term in h.lower() for h in actor.handles) or any(term in w.lower() for w in actor.wallets):
            results.append({
                "type": "actor",
                "id": actor.actor_id,
                "matched_handle": actor.primary_handle,
                "risk_category": actor.risk_category
            })

    return {"query": q, "total_matches": len(results), "results": results}