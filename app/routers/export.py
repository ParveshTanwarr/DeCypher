import io
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
import pandas as pd
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import Actor, DarkWebHandle, Wallet

router = APIRouter(prefix="/export", tags=["Export"])


def _get_live_actor_records(db: Session) -> List[Dict[str, Any]]:
    actors = db.query(Actor).all()
    records = []

    for a in actors:
        handles = db.query(DarkWebHandle).filter(DarkWebHandle.actor_id == a.actor_id).all()
        wallets = db.query(Wallet).filter(Wallet.actor_id == a.actor_id).all()

        handle_list = [h.handle for h in handles]
        wallet_list = [w.address for w in wallets]

        first_dates = [h.first_seen for h in handles if h.first_seen]
        last_dates = [h.last_seen for h in handles if h.last_seen]

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

    # Flatten nested arrays for CSV serialization
    csv_rows = []
    for r in records:
        csv_rows.append({
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

    df = pd.DataFrame(csv_rows)

    stream = io.StringIO()
    df.to_csv(stream, index=False)

    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=threat_actors.csv"},
    )