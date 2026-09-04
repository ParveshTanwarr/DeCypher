import csv
import io
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet
from app.routers.auth import require_role

# Bulk export of every actor's identity/correlation data is the single
# most sensitive action in this API, so it's restricted to "admin" rather
# than any authenticated user. This is a judgment call, not a spec
# requirement -- adjust the allowed role(s) if that doesn't match your
# actual policy (e.g. add "investigator" back if analysts need exports too).
router = APIRouter(prefix="/export", tags=["Export"], dependencies=[Depends(require_role("admin"))])

CSV_HEADERS = [
    "actor_id",
    "primary_handle",
    "risk_category",
    "confidence_score",
    "priority_score",
    "first_seen",
    "last_seen",
    "handles_count",
    "associated_handles",
    "wallets_count",
    "wallet_addresses",
]


def _get_live_actor_records(db: Session) -> List[Dict[str, Any]]:
    actors = db.query(Actor).all()
    if not actors:
        return []

    actor_ids = [a.actor_id for a in actors]

    # Pre-fetch handles and wallets in two batch queries (avoids 2N+1 query bottleneck)
    all_handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id.in_(actor_ids)).all()
    all_wallets = db.query(Wallet).filter(Wallet.actor_id.in_(actor_ids)).all()

    handles_by_actor: Dict[str, list] = {}
    for h in all_handles:
        handles_by_actor.setdefault(h.actor_id, []).append(h)

    wallets_by_actor: Dict[str, list] = {}
    for w in all_wallets:
        wallets_by_actor.setdefault(w.actor_id, []).append(w)

    records = []
    for a in actors:
        actor_handles = handles_by_actor.get(a.actor_id, [])
        actor_wallets = wallets_by_actor.get(a.actor_id, [])

        handle_list = [h.handle for h in actor_handles]
        wallet_list = [w.address for w in actor_wallets]

        first_dates = [h.first_seen for h in actor_handles if h.first_seen]
        last_dates = [h.last_seen for h in actor_handles if h.last_seen]

        first_seen_str = min(first_dates).strftime("%Y-%m-%d") if first_dates else "N/A"
        last_seen_str = max(last_dates).strftime("%Y-%m-%d") if last_dates else "N/A"

        records.append({
            "actor_id": a.actor_id,
            "primary_handle": a.primary_handle,
            "risk_category": a.risk_category,
            "confidence_score": a.confidence_score,
            "priority_score": a.priority_score,
            "first_seen": first_seen_str,
            "last_seen": last_seen_str,
            "handles": handle_list,
            "handles_count": len(handle_list),
            "wallets": wallet_list,
            "wallets_count": len(wallet_list),
        })

    return records


@router.get("/json")
def export_json(db: Session = Depends(get_db)):
    records = _get_live_actor_records(db)
    return JSONResponse(content=records)


@router.get("/csv")
def export_csv(db: Session = Depends(get_db)):
    records = _get_live_actor_records(db)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()

    for r in records:
        writer.writerow({
            "actor_id": r["actor_id"],
            "primary_handle": r["primary_handle"],
            "risk_category": r["risk_category"],
            "confidence_score": r["confidence_score"],
            "priority_score": r["priority_score"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "handles_count": r["handles_count"],
            "associated_handles": "; ".join(r["handles"]),
            "wallets_count": r["wallets_count"],
            "wallet_addresses": "; ".join(r["wallets"]),
        })








    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=threat_actors.csv"},
    )