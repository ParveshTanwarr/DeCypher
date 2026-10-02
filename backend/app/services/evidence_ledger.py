from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.sql_models import EvidenceLedgerEntry, Observation


GENESIS_HASH = hashlib.sha256(
    b"DECYPHER-EVIDENCE-LEDGER-GENESIS-v1"
).hexdigest()
LEDGER_LOCK_KEY = "decypher:evidence-ledger:v1"


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def hash_record(
    *,
    sequence_id: int,
    previous_hash: str,
    event_type: str,
    observation_id: Optional[str],
    actor_id: Optional[str],
    created_by: str,
    created_at: str,
    payload: Mapping[str, Any],
) -> str:
    canonical = canonical_json(
        {
            "sequence_id": sequence_id,
            "previous_hash": previous_hash,
            "event_type": event_type,
            "observation_id": observation_id,
            "actor_id": actor_id,
            "created_by": created_by,
            "created_at": created_at,
            "payload": dict(payload),
        }
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class EvidenceLedgerService:
    """Append-only, tamper-evident hash chain for structured evidence."""

    def __init__(self, db: Session):
        self.db = db

    def _lock_chain(self) -> None:
        bind = self.db.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": LEDGER_LOCK_KEY},
            )

    @staticmethod
    def observation_payload(observation: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "observation_id": observation.get("observation_id"),
            "indicator_type": observation.get("indicator_type"),
            "detected": bool(observation.get("detected", True)),
            "value": observation.get("value"),
            "target": observation.get("target"),
            "source": observation.get("source"),
            "timestamp": _iso(observation.get("timestamp")),
            "confidence": observation.get("confidence"),
            "description": observation.get("description"),
        }

    def append_missing_for_observations(
        self,
        observations: Iterable[Mapping[str, Any]],
        *,
        actor_id: Optional[str] = None,
        created_by: str = "system",
    ) -> int:
        incoming = [
            dict(observation)
            for observation in observations
            if observation.get("observation_id")
        ]
        if not incoming:
            return 0

        self._lock_chain()

        observation_ids = {str(item["observation_id"]) for item in incoming}
        existing = {
            str(observation_id)
            for (observation_id,) in self.db.query(EvidenceLedgerEntry.observation_id)
            .filter(EvidenceLedgerEntry.observation_id.in_(observation_ids))
            .all()
            if observation_id
        }

        last_entry = (
            self.db.query(EvidenceLedgerEntry)
            .order_by(EvidenceLedgerEntry.id.desc())
            .first()
        )
        previous_hash = last_entry.record_hash if last_entry else GENESIS_HASH
        appended = 0

        for observation in sorted(
            incoming,
            key=lambda item: (
                _iso(item.get("timestamp")) or "",
                str(item.get("observation_id")),
            ),
        ):
            observation_id = str(observation["observation_id"])
            if observation_id in existing:
                continue

            payload = self.observation_payload(observation)
            entry = EvidenceLedgerEntry(
                observation_id=observation_id,
                actor_id=actor_id,
                event_type="observation_ingested",
                created_by=created_by,
                payload=payload,
                previous_hash=previous_hash,
                record_hash=hashlib.sha256(
                    f"pending:{observation_id}".encode("utf-8")
                ).hexdigest(),
            )
            self.db.add(entry)
            self.db.flush()

            created_at = _iso(entry.created_at) or datetime.now(timezone.utc).isoformat()
            entry.record_hash = hash_record(
                sequence_id=entry.id,
                previous_hash=previous_hash,
                event_type=entry.event_type,
                observation_id=entry.observation_id,
                actor_id=entry.actor_id,
                created_by=entry.created_by,
                created_at=created_at,
                payload=entry.payload or {},
            )
            previous_hash = entry.record_hash
            existing.add(observation_id)
            appended += 1

        return appended

    def backfill_missing_observations(self) -> int:
        observations = (
            self.db.query(Observation)
            .order_by(Observation.timestamp.asc(), Observation.id.asc())
            .all()
        )
        rows = [
            {
                "observation_id": observation.observation_id,
                "indicator_type": observation.indicator_type,
                "detected": observation.detected,
                "value": observation.value,
                "target": observation.target,
                "source": observation.source,
                "timestamp": observation.timestamp,
                "confidence": observation.confidence,
                "description": observation.description,
            }
            for observation in observations
        ]
        return self.append_missing_for_observations(rows)

    def verify_chain(self) -> dict[str, Any]:
        entries = (
            self.db.query(EvidenceLedgerEntry)
            .order_by(EvidenceLedgerEntry.id.asc())
            .all()
        )

        previous_hash = GENESIS_HASH
        for index, entry in enumerate(entries):
            created_at = _iso(entry.created_at)
            expected = hash_record(
                sequence_id=entry.id,
                previous_hash=entry.previous_hash,
                event_type=entry.event_type,
                observation_id=entry.observation_id,
                actor_id=entry.actor_id,
                created_by=entry.created_by,
                created_at=created_at or "",
                payload=entry.payload or {},
            )
            if entry.previous_hash != previous_hash:
                return {
                    "valid": False,
                    "entry_count": len(entries),
                    "verified_entries": index,
                    "head_hash": entries[-1].record_hash if entries else GENESIS_HASH,
                    "broken_sequence_id": entry.id,
                    "reason": "Previous-hash link does not match the preceding committed record.",
                }
            if entry.record_hash != expected:
                return {
                    "valid": False,
                    "entry_count": len(entries),
                    "verified_entries": index,
                    "head_hash": entries[-1].record_hash if entries else GENESIS_HASH,
                    "broken_sequence_id": entry.id,
                    "reason": "Record hash does not match the stored record contents.",
                }
            previous_hash = entry.record_hash

        return {
            "valid": True,
            "entry_count": len(entries),
            "verified_entries": len(entries),
            "head_hash": previous_hash,
            "broken_sequence_id": None,
            "reason": "Hash chain verified against the canonical stored record representation.",
        }

    def status(self) -> dict[str, Any]:
        latest = (
            self.db.query(EvidenceLedgerEntry)
            .order_by(EvidenceLedgerEntry.id.desc())
            .first()
        )
        count = int(self.db.query(EvidenceLedgerEntry.id).count())
        return {
            "mode": "internal_hash_chain",
            "blockchain_anchor_configured": False,
            "entry_count": count,
            "head_hash": latest.record_hash if latest else GENESIS_HASH,
            "genesis_hash": GENESIS_HASH,
        }

    def latest(
        self,
        *,
        limit: int = 25,
        actor_id: Optional[str] = None,
    ) -> list[EvidenceLedgerEntry]:
        query = self.db.query(EvidenceLedgerEntry)
        if actor_id:
            query = query.filter(EvidenceLedgerEntry.actor_id == actor_id)
        return query.order_by(EvidenceLedgerEntry.id.desc()).limit(limit).all()
