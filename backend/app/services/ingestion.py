import os
import logging
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.postgres import engine, Base, SessionLocal
from app.models.sql_models import DarkWebHandle, Wallet, Marketplace, Actor

logger = logging.getLogger(__name__)


def _seed_default_actors(session: Session):
    default_actors = [
        {
            "actor_id": "ACT-1001",
            "primary_handle": "dark_shadow",
            "risk_category": "Critical",
            "confidence_score": 0.94,
            "priority_score": 92,
        },
        {
            "actor_id": "ACT-1002",
            "primary_handle": "byte_bandit",
            "risk_category": "High",
            "confidence_score": 0.82,
            "priority_score": 78,
        },
        {
            "actor_id": "ACT-1003",
            "primary_handle": "crypto_phantom",
            "risk_category": "Critical",
            "confidence_score": 0.91,
            "priority_score": 88,
        },
    ]
    for act in default_actors:
        stmt = insert(Actor).values(act)
        stmt = stmt.on_conflict_do_update(
            index_elements=["actor_id"],
            set_={
                "primary_handle": stmt.excluded.primary_handle,
                "risk_category": stmt.excluded.risk_category,
                "confidence_score": stmt.excluded.confidence_score,
                "priority_score": stmt.excluded.priority_score,
            },
        )
        session.execute(stmt)
    session.commit()
    print(f"[+] Safely seeded {len(default_actors)} core actor profiles into 'actors'")


def _upsert_darkweb_handles(session: Session, df: pd.DataFrame):
    # Only keep columns matching the DarkWebHandle model
    valid_cols = ["handle", "platform", "actor_id", "first_seen", "last_seen", "registration_date", "status"]
    df_filtered = df[[c for c in valid_cols if c in df.columns]]
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0

    stmt = insert(DarkWebHandle).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_handle_platform",
        set_={
            "actor_id": stmt.excluded.actor_id,
            "status": stmt.excluded.status,
            "last_seen": stmt.excluded.last_seen,
        },
    )
    session.execute(stmt)
    return len(records)


def _upsert_wallets(session: Session, df: pd.DataFrame):
    # 1. Rename wallet_address to match the Wallet model's address column
    rename_map = {
        "wallet_address": "address",
    }
    df_renamed = df.rename(columns=rename_map)

    # 2. Deduplicate by address within the CSV batch to prevent Postgres batch conflict error
    df_deduped = df_renamed.drop_duplicates(subset=["address"], keep="last")

    # 3. Filter only valid columns that exist in the Wallet ORM model
    valid_cols = ["address", "currency", "actor_id", "associated_handle", "first_seen"]
    df_filtered = df_deduped[[c for c in valid_cols if c in df_deduped.columns]]
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0

    stmt = insert(Wallet).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["address"],
        set_={
            "currency": stmt.excluded.currency,
            "actor_id": stmt.excluded.actor_id,
            "associated_handle": stmt.excluded.associated_handle,
        },
    )
    session.execute(stmt)
    return len(records)


def _upsert_marketplaces(session: Session, df: pd.DataFrame):
    # Map CSV column headers to Marketplace model field names
    rename_map = {
        "market_name": "name",
        "url_onion": "onion_url",
    }
    df_renamed = df.rename(columns=rename_map)

    valid_cols = ["name", "onion_url", "status"]
    df_filtered = df_renamed[[c for c in valid_cols if c in df_renamed.columns]]
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0

    stmt = insert(Marketplace).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={
            "onion_url": stmt.excluded.onion_url,
        },
    )
    session.execute(stmt)
    return len(records)


LOADERS = {
    "darkweb_handles": ("data/datahandles.csv", _upsert_darkweb_handles),
    "wallets": ("data/datawallets.csv", _upsert_wallets),
    "marketplaces": ("data/datamarketplaces.csv", _upsert_marketplaces),
}


def init_db_and_load_csvs(reset_tables: bool = False):
    if reset_tables:
        print("[*] Resetting old tables to apply updated schema...")
        Base.metadata.drop_all(bind=engine)

    # 1. Create tables with new columns and constraints
    Base.metadata.create_all(bind=engine)
    print("[+] SQL Tables verified/created with latest schema.")

    # 2. Ingest CSVs safely via Session and upsert
    session = SessionLocal()
    try:
        # Seed core threat actors first
        _seed_default_actors(session)

        for table_name, (file_path, loader_func) in LOADERS.items():
            if not os.path.exists(file_path):
                print(f"[*] Notice: {file_path} not found. Skipping auto-load.")
                continue

            try:
                df = pd.read_csv(file_path)
                count = loader_func(session, df)
                session.commit()
                print(f"[+] Safely upserted {count} records into '{table_name}' from {file_path}")
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading {file_path} into '{table_name}': {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("[*] Starting manual database ingestion...")
    init_db_and_load_csvs(reset_tables=True)