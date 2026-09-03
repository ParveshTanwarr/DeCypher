import os
import logging
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.postgres import engine, Base, SessionLocal
from app.models.sql_models import DarkWebHandle, Wallet, Marketplace, Actor

logger = logging.getLogger(__name__)


def _upsert_actors(session: Session, df: pd.DataFrame):
    df_deduped = df.drop_duplicates(subset=["actor_id"], keep="last")
    valid_cols = ["actor_id", "primary_handle", "risk_category", "confidence_score", "priority_score"]
    df_filtered = df_deduped[[c for c in valid_cols if c in df_deduped.columns]]
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0

    stmt = insert(Actor).values(records)
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
    return len(records)


def _upsert_darkweb_handles(session: Session, df: pd.DataFrame):
    valid_cols = ["handle", "platform", "actor_id", "first_seen", "last_seen", "registration_date", "status"]
    df_filtered = df[[c for c in valid_cols if c in df.columns]].copy()
    
    # Deduplicate composite unique constraint (handle, platform)
    if "handle" in df_filtered.columns and "platform" in df_filtered.columns:
        df_filtered = df_filtered.drop_duplicates(subset=["handle", "platform"], keep="last")
        
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
    rename_map = {"wallet_address": "address"}
    df_renamed = df.rename(columns=rename_map)
    df_deduped = df_renamed.drop_duplicates(subset=["address"], keep="last")

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
    rename_map = {
        "market_name": "name",
        "url_onion": "onion_url",
    }
    df_renamed = df.rename(columns=rename_map)
    df_deduped = df_renamed.drop_duplicates(subset=["name"], keep="last")

    valid_cols = ["name", "onion_url", "status"]
    df_filtered = df_deduped[[c for c in valid_cols if c in df_deduped.columns]]
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


# Correct relative data paths based on project structure
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

LOADERS = [
    ("actors", os.path.join(DATA_DIR, "actors.csv"), _upsert_actors),
    ("marketplaces", os.path.join(DATA_DIR, "marketplaces.csv"), _upsert_marketplaces),
    ("darkweb_handles", os.path.join(DATA_DIR, "handles.csv"), _upsert_darkweb_handles),
    ("wallets", os.path.join(DATA_DIR, "wallets.csv"), _upsert_wallets),
]


def init_db_and_load_csvs(reset_tables: bool = False):
    if reset_tables:
        print("[*] Resetting old tables to apply updated schema...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    print("[+] SQL Tables verified/created with latest schema.")

    session = SessionLocal()
    try:
        for table_name, file_path, loader_func in LOADERS:
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
    init_db_and_load_csvs(reset_tables=False)