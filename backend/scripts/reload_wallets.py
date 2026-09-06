"""Reload wallet seed data without collapsing reused addresses.

Run from the repository root with the project Python environment active:
    python backend/scripts/reload_wallets.py

The CSV is the source of truth for wallet-to-handle relationships.  A wallet
address is deliberately allowed to occur more than once because address reuse
is a correlation signal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import delete

from app.database.postgres import SessionLocal
from app.models.sql_models import DarkWebHandle, Wallet


ROOT = Path(__file__).resolve().parents[2]
WALLETS_CSV = ROOT / "data" / "wallets.csv"


def main() -> None:
    wallets_df = pd.read_csv(WALLETS_CSV, dtype=str).fillna("")

    required = {"wallet_address", "handle_id", "currency", "first_seen"}
    missing = required - set(wallets_df.columns)
    if missing:
        raise RuntimeError(f"wallets.csv missing columns: {sorted(missing)}")

    db = SessionLocal()
    try:
        handle_rows = db.query(DarkWebHandle).all()
        by_name = {row.handle: row for row in handle_rows}
        by_id = {str(row.id): row for row in handle_rows}

        # The SQL model stores the numeric handle row id, while the CSV uses
        # H00001-style handle IDs.  Existing seed data may have associated
        # handle names, so resolve by both the numeric DB id and handle name.
        # For H00001-style IDs, fall back to the handle ordering only if the
        # database already contains the expected number of rows.
        csv_handles = pd.read_csv(
            ROOT / "data" / "handles.csv", dtype=str
        ).fillna("")
        csv_handle_map = {
            row["handle_id"]: row
            for _, row in csv_handles.iterrows()
        }

        db_by_handle_name = {row.handle: row for row in handle_rows}

        db.execute(delete(Wallet))
        db.flush()

        inserted = 0
        unresolved = []

        for _, row in wallets_df.iterrows():
            csv_handle_id = row["handle_id"]
            csv_handle = csv_handle_map.get(csv_handle_id)

            if csv_handle is None:
                unresolved.append(csv_handle_id)
                continue

            handle_name = csv_handle["handle_name"]
            db_handle = db_by_handle_name.get(handle_name)

            actor_id = None
            if db_handle is not None:
                actor_id = db_handle.actor_id

            first_seen = None
            if row["first_seen"]:
                first_seen = datetime.fromisoformat(
                    row["first_seen"]
                ).replace(tzinfo=timezone.utc)

            db.add(
                Wallet(
                    actor_id=actor_id,
                    address=row["wallet_address"],
                    currency=row["currency"] or "BTC",
                    associated_handle=handle_name,
                    first_seen=first_seen,
                )
            )
            inserted += 1

        if unresolved:
            raise RuntimeError(
                "Could not resolve handle IDs: "
                + ", ".join(sorted(set(unresolved)))
            )

        db.commit()
        print(f"Reloaded {inserted} wallet rows.")
        print("Wallet addresses were inserted without deduplicating reuse.")

        duplicate_count = (
            db.query(Wallet.address)
            .group_by(Wallet.address)
            .having(__import__("sqlalchemy").func.count(Wallet.address) > 1)
            .count()
        )
        print(f"Reused wallet addresses detected: {duplicate_count}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
