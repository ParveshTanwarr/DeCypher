import os
import logging
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.postgres import engine, Base, SessionLocal
from app.models.sql_models import DarkWebHandle, Wallet, Marketplace, Actor, Observation
from app.services import graph_service

logger = logging.getLogger(__name__)

# services -> app -> backend -> project root -> data
# (previous version only went up two levels, which resolved to a
# nonexistent backend/data/ folder and silently skipped every file)
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))


def _prepare_handles(df: pd.DataFrame) -> pd.DataFrame:
    """
    handles.csv uses different column names than the DarkWebHandle model
    (actor_id_ground_truth / handle_name / marketplace / created_date /
    last_active_date instead of actor_id / handle / platform /
    registration_date / last_seen). Normalize once so every function
    below can just use the model's names.
    """
    renamed = df.rename(
        columns={
            "actor_id_ground_truth": "actor_id",
            "handle_name": "handle",
            "marketplace": "platform",
        }
    ).copy()
    renamed["registration_date"] = pd.to_datetime(df.get("created_date"), errors="coerce")
    renamed["first_seen"] = renamed["registration_date"]
    renamed["last_seen"] = pd.to_datetime(df.get("last_active_date"), errors="coerce")
    return renamed


def _derive_primary_handles(prepared_handles: pd.DataFrame) -> pd.DataFrame:
    """
    actors.csv has no primary_handle column at all, so Actor.primary_handle
    (NOT NULL) can never be populated straight from it. Derive one per
    actor as their earliest-registered handle instead.
    """
    df = prepared_handles.dropna(subset=["actor_id", "handle"]).copy()
    df = df.sort_values("registration_date", na_position="last")
    primary = df.groupby("actor_id", as_index=False).first()[["actor_id", "handle"]]
    return primary.rename(columns={"handle": "primary_handle"})


def _upsert_actors(session: Session, df: pd.DataFrame, primary_handles: pd.DataFrame):
    merged = df.merge(primary_handles, on="actor_id", how="left")
    # Last-resort fallback if an actor somehow has no handles at all.
    merged["primary_handle"] = merged["primary_handle"].fillna(merged["actor_id"])
    df_deduped = merged.drop_duplicates(subset=["actor_id"], keep="last")

    valid_cols = ["actor_id", "primary_handle", "risk_category", "confidence_score", "priority_score"]
    df_filtered = df_deduped[[c for c in valid_cols if c in df_deduped.columns]]
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0, []

    stmt = insert(Actor).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["actor_id"],
        set_={
            "primary_handle": stmt.excluded.primary_handle,
            "risk_category": stmt.excluded.risk_category,
        },
    )
    session.execute(stmt)
    return len(records), records


def _upsert_darkweb_handles(session: Session, prepared_handles: pd.DataFrame):
    valid_cols = ["handle", "platform", "actor_id", "first_seen", "last_seen", "registration_date", "status"]
    df_filtered = prepared_handles[[c for c in valid_cols if c in prepared_handles.columns]].copy()
    df_filtered = df_filtered.dropna(subset=["handle"])

    if "handle" in df_filtered.columns and "platform" in df_filtered.columns:
        df_filtered = df_filtered.drop_duplicates(subset=["handle", "platform"], keep="last")

    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0, []

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
    return len(records), records


def _upsert_wallets(session: Session, wallets_df: pd.DataFrame, prepared_handles: pd.DataFrame):
    """
    wallets.csv only has handle_id (not actor_id), so join it through
    handles.csv before inserting. Wallet addresses are deliberately
    non-unique because address reuse is itself a correlation signal.

    Unlike actors/handles, Wallet has no natural unique conflict target:
    the same address may legitimately belong to several handle rows.
    Therefore this loader replaces the seed wallet snapshot on each
    ingestion run instead of using ON CONFLICT(address).
    """
    handle_lookup = prepared_handles[["handle_id", "handle", "actor_id"]].dropna(subset=["handle_id"])
    merged = wallets_df.rename(columns={"wallet_address": "address"}).merge(
        handle_lookup, on="handle_id", how="left"
    )
    merged = merged.rename(columns={"handle": "associated_handle"})
    merged["first_seen"] = pd.to_datetime(merged.get("first_seen"), errors="coerce")

    unresolved = merged[merged["associated_handle"].isna()]["handle_id"].dropna().unique().tolist()
    if unresolved:
        raise ValueError(
            "Could not resolve wallet handle IDs through handles.csv: "
            + ", ".join(map(str, unresolved[:20]))
            + (" ..." if len(unresolved) > 20 else "")
        )

    # Keep every wallet row. Duplicate addresses are intentional and must
    # remain separate so reuse across handles is queryable in PostgreSQL.
    valid_cols = ["address", "currency", "actor_id", "associated_handle", "first_seen"]
    df_filtered = merged[[c for c in valid_cols if c in merged.columns]].copy()
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0, [], []

    # Re-ingestion is idempotent by replacing the deterministic CSV-backed
    # wallet snapshot. This is necessary because address itself is not unique.
    session.query(Wallet).delete(synchronize_session=False)
    session.flush()

    session.add_all([Wallet(**record) for record in records])

    # Full handle<->wallet pairing list for Neo4j. This intentionally
    # includes every repeated address/handle pairing from the CSV.
    pair_cols = [c for c in ["address", "associated_handle", "currency"] if c in merged.columns]
    all_pairs = merged[pair_cols].dropna(subset=["address", "associated_handle"]).to_dict(orient="records")

    return len(records), records, all_pairs


def _upsert_infrastructure_observations(session: Session, df: pd.DataFrame):
    """
    data/infrastructure_indicators.csv was never loaded anywhere -- the
    `observations` table (which GET /actors/{id}/evidence reads from)
    started out permanently empty for every actor. This seeds it from the
    OSINT indicator dataset so that endpoint actually has data to return.
    `target` is set to the actor_id directly (not a handle) since
    get_actor_evidence's target_keys always includes actor_id.lower().
    """
    df = df.rename(columns={
        "indicator_id": "observation_id",
        "actor_id_ground_truth": "target",
        "onion_address": "value",
        "leak_type": "indicator_type",
    }).copy()
    df["confidence"] = df.get("confidence_hint")
    df["timestamp"] = pd.to_datetime(df.get("scan_date"), errors="coerce")
    df["source"] = "osint_indicator_scan"
    df["detected"] = True

    def _describe(row):
        extra = []
        if pd.notna(row.get("cert_fingerprint")):
            extra.append(f"cert {row['cert_fingerprint']}")
        if pd.notna(row.get("clearnet_match_domain")):
            extra.append(f"clearnet match {row['clearnet_match_domain']}")
        base = f"{row['indicator_type']} at {row['value']}"
        return base + (" (" + "; ".join(extra) + ")" if extra else "")

    df["description"] = df.apply(_describe, axis=1)

    valid_cols = [
        "observation_id", "indicator_type", "detected", "value", "target",
        "source", "timestamp", "confidence", "description",
    ]
    df_filtered = df[[c for c in valid_cols if c in df.columns]]
    df_filtered = df_filtered.drop_duplicates(subset=["observation_id"], keep="last")
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0

    stmt = insert(Observation).values(records)
    # Insert-only: these are immutable historical scan results, not
    # something we expect to need updating on re-ingest.
    stmt = stmt.on_conflict_do_nothing(index_elements=["observation_id"])
    session.execute(stmt)
    return len(records)


def _upsert_marketplaces(session: Session, df: pd.DataFrame):
    rename_map = {
        "market_name": "name",
        "url_onion": "onion_url",
        "active_status": "status",
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
        set_={"onion_url": stmt.excluded.onion_url, "status": stmt.excluded.status},
    )
    session.execute(stmt)
    return len(records)


def init_db_and_load_csvs(reset_tables: bool = False, sync_neo4j: bool = True):
    if reset_tables:
        print("[*] Resetting old tables to apply updated schema...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    print("[+] SQL Tables verified/created with latest schema.")

    actors_path = os.path.join(DATA_DIR, "actors.csv")
    handles_path = os.path.join(DATA_DIR, "handles.csv")
    wallets_path = os.path.join(DATA_DIR, "wallets.csv")
    marketplaces_path = os.path.join(DATA_DIR, "marketplaces.csv")
    infra_indicators_path = os.path.join(DATA_DIR, "infrastructure_indicators.csv")

    # handles.csv is loaded once up front (in memory only, nothing written
    # yet) because both actors (primary_handle) and wallets (actor_id
    # linkage) need to be derived from it.
    prepared_handles = None
    if os.path.exists(handles_path):
        prepared_handles = _prepare_handles(pd.read_csv(handles_path))
    else:
        print(f"[*] Notice: {handles_path} not found. Skipping.")

    actor_records, handle_records, wallet_records = [], [], []
    wallet_pairs_for_neo4j = []

    session = SessionLocal()
    try:
        # Order matters: actors before handles (FK), handles before wallets
        # (wallets need the handle->actor_id lookup).
        if os.path.exists(marketplaces_path):
            try:
                count = _upsert_marketplaces(session, pd.read_csv(marketplaces_path))
                session.commit()
                print(f"[+] Upserted {count} records into 'marketplaces'")
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading {marketplaces_path} into 'marketplaces': {e}")
        else:
            print(f"[*] Notice: {marketplaces_path} not found. Skipping auto-load.")

        if os.path.exists(actors_path) and prepared_handles is not None:
            try:
                primary_handles = _derive_primary_handles(prepared_handles)
                count, actor_records = _upsert_actors(session, pd.read_csv(actors_path), primary_handles)
                session.commit()
                print(f"[+] Upserted {count} records into 'actors'")
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading {actors_path} into 'actors': {e}")

        else:
            print("[*] Notice: actors.csv and/or handles.csv missing. Skipping actors.")

        if prepared_handles is not None:
            try:
                count, handle_records = _upsert_darkweb_handles(session, prepared_handles)
                session.commit()
                print(f"[+] Upserted {count} records into 'darkweb_handles'")
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading {handles_path} into 'darkweb_handles': {e}")

        if os.path.exists(wallets_path) and prepared_handles is not None:
            try:
                count, wallet_records, wallet_pairs_for_neo4j = _upsert_wallets(
                    session, pd.read_csv(wallets_path), prepared_handles
                )
                session.commit()
                print(f"[+] Loaded {count} records into 'wallets'")
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading {wallets_path} into 'wallets': {e}")
        else:
            print(f"[*] Notice: {wallets_path} not found. Skipping auto-load.")

        if os.path.exists(infra_indicators_path):
            try:
                count = _upsert_infrastructure_observations(session, pd.read_csv(infra_indicators_path))
                session.commit()
                print(f"[+] Upserted {count} records into 'observations'")
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading {infra_indicators_path} into 'observations': {e}")
        else:
            print(f"[*] Notice: {infra_indicators_path} not found. Skipping auto-load.")
    finally:
        session.close()

    if sync_neo4j and (actor_records or handle_records or wallet_pairs_for_neo4j):
        try:
            # wallet_pairs_for_neo4j contains the complete non-deduplicated
            # handle<->wallet relationships from the CSV.
            graph_service.sync_actor_batch(actor_records, handle_records, wallet_pairs_for_neo4j)
            print(
                f"[+] Synced {len(actor_records)} actors / {len(handle_records)} handles / "
                f"{len(wallet_pairs_for_neo4j)} handle-wallet links into Neo4j"
            )
        except Exception as e:
            print(f"[-] Neo4j sync skipped (is Neo4j running?): {e}")


if __name__ == "__main__":
    print("[*] Starting manual database ingestion...")
    init_db_and_load_csvs(reset_tables=False)
