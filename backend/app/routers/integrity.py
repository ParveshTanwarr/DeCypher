from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.models.sql_models import EvidenceLedgerEntry
from app.routers.auth import get_current_user
from app.services.evidence_ledger import EvidenceLedgerService, GENESIS_HASH

router = APIRouter(
    prefix="/integrity",
    tags=["Evidence Integrity"],
    dependencies=[Depends(get_current_user)],
)


def _entry_response(entry: EvidenceLedgerEntry) -> dict:
    return {
        "sequence_id": entry.id,
        "observation_id": entry.observation_id,
        "actor_id": entry.actor_id,
        "event_type": entry.event_type,
        "created_by": entry.created_by,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "previous_hash": entry.previous_hash,
        "record_hash": entry.record_hash,
        "payload": entry.payload,
    }


@router.get("/status")
def ledger_status(db: Session = Depends(get_db)):
    return EvidenceLedgerService(db).status()


@router.get("/verify")
def verify_ledger(db: Session = Depends(get_db)):
    return EvidenceLedgerService(db).verify_chain()


@router.get("/ledger")
def get_ledger(
    limit: int = Query(25, ge=1, le=200),
    actor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    service = EvidenceLedgerService(db)
    entries = service.latest(limit=limit, actor_id=actor_id)
    return {
        "genesis_hash": GENESIS_HASH,
        "entries": [_entry_response(entry) for entry in entries],
    }
