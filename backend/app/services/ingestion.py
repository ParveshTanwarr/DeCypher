import hashlib
import os
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from typing import Optional

from app.database.postgres import engine, Base, SessionLocal
from app.config import settings
from app.models.sql_models import (
    DarkWebHandle,
    Wallet,
    Marketplace,
    Actor,
    Observation,
    PGPKey,
    TrustLink,
    handle_pgp_keys,
)
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
    valid_cols = [
        "handle",
        "platform",
        "actor_id",
        "first_seen",
        "last_seen",
        "registration_date",
        "status",
    ]
    df_filtered = prepared_handles[[c for c in valid_cols if c in prepared_handles.columns]].copy()
    df_filtered = df_filtered.dropna(subset=["handle"])

    if "handle" in df_filtered.columns and "platform" in df_filtered.columns:
        df_filtered = df_filtered.drop_duplicates(subset=["handle", "platform"], keep="last")

    # Persist the stable source handle ID separately from the relational model's
    # integer primary key. The source ID is the only identifier exposed to Neo4j.
    df_filtered["source_handle_id"] = prepared_handles.loc[df_filtered.index, "handle_id"]
    records = df_filtered.where(pd.notnull(df_filtered), None).to_dict(orient="records")
    if not records:
        return 0, []

    stmt = insert(DarkWebHandle).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_handle_platform",
        set_={
            "source_handle_id": stmt.excluded.source_handle_id,
            "actor_id": stmt.excluded.actor_id,
            "status": stmt.excluded.status,
            "last_seen": stmt.excluded.last_seen,
        },
    )
    session.execute(stmt)

    # The relational model uses an auto-increment integer primary key (id),
    # while the graph schema uses the stable CSV handle_id (for example H00887).
    # Return a separate graph payload so the stable identifier is preserved
    # without inserting an unknown handle_id column into PostgreSQL.
    graph_cols = [
        column for column in ["handle_id", "handle", "platform", "actor_id", "status"]
        if column in prepared_handles.columns
    ]
    graph_df = prepared_handles[graph_cols].dropna(
        subset=["handle_id", "handle", "actor_id"]
    ).drop_duplicates(subset=["handle_id"], keep="last")
    graph_records = graph_df.where(pd.notnull(graph_df), None).to_dict(orient="records")

    return len(records), graph_records


def _upsert_pgp_keys_and_trust_links(
    session: Session,
    prepared_handles: pd.DataFrame,
    trust_links_df: Optional[pd.DataFrame] = None,
):
    """
    Normalize PGP fingerprints into first-class PGPKey records, connect them
    to handles, and load synthetic trust/signature relationships.

    handles.csv remains the source of truth for observed fingerprints. The
    optional trust_links.csv uses stable handle_id values from handles.csv so
    the demo relationships remain deterministic and auditable.
    """
    if "pgp_fingerprint" not in prepared_handles.columns:
        return 0, 0

    pgp_df = prepared_handles.copy()
    pgp_df["pgp_fingerprint"] = (
        pgp_df["pgp_fingerprint"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )
    pgp_df = pgp_df[pgp_df["pgp_fingerprint"] != ""].copy()
    if pgp_df.empty:
        return 0, 0

    pgp_df["first_seen"] = pd.to_datetime(pgp_df["first_seen"], errors="coerce")
    pgp_df["last_seen"] = pd.to_datetime(pgp_df["last_seen"], errors="coerce")

    pgp_records = []
    for fingerprint, group in pgp_df.groupby("pgp_fingerprint", sort=False):
        first_seen = group["first_seen"].min()
        last_seen = group["last_seen"].max()
        pgp_records.append({
            "fingerprint": fingerprint,
            "key_type": "OpenPGP",
            "source": "synthetic_dataset",
            "first_seen": None if pd.isna(first_seen) else first_seen.to_pydatetime(),
            "last_seen": None if pd.isna(last_seen) else last_seen.to_pydatetime(),
        })

    stmt = insert(PGPKey).values(pgp_records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["fingerprint"],
        set_={
            "last_seen": stmt.excluded.last_seen,
            "source": stmt.excluded.source,
        },
    )
    session.execute(stmt)
    session.flush()

    key_rows = session.query(PGPKey).filter(
        PGPKey.fingerprint.in_([row["fingerprint"] for row in pgp_records])
    ).all()
    key_by_fingerprint = {key.fingerprint: key for key in key_rows}

    # Attach every observed fingerprint to its handle. A handle may have
    # multiple observed keys over time, so this is intentionally many-to-many.
    handle_rows = session.query(DarkWebHandle).all()
    handle_by_identity = {
        (handle.handle, handle.platform): handle
        for handle in handle_rows
    }

    association_records = []
    for row in pgp_df[["handle", "platform", "pgp_fingerprint"]].drop_duplicates().to_dict("records"):
        handle = handle_by_identity.get((row["handle"], row["platform"]))
        key = key_by_fingerprint.get(row["pgp_fingerprint"])
        if handle and key:
            association_records.append({
                "handle_id": handle.id,
                "pgp_key_id": key.id,
            })

    if association_records:
        association_stmt = insert(handle_pgp_keys).values(association_records)
        association_stmt = association_stmt.on_conflict_do_nothing()
        session.execute(association_stmt)

    trust_count = 0
    if trust_links_df is not None and not trust_links_df.empty:
        source_map = (
            prepared_handles[["handle_id", "handle", "platform", "pgp_fingerprint"]]
            .dropna(subset=["handle_id", "handle"])
            .drop_duplicates(subset=["handle_id"])
        )
        source_map = source_map.set_index("handle_id").to_dict("index")

        trust_records = []
        for raw in trust_links_df.to_dict("records"):
            source = source_map.get(str(raw.get("source_handle_id")))
            target = source_map.get(str(raw.get("target_handle_id")))
            if not source or not target:
                continue

            source_handle = handle_by_identity.get((source["handle"], source["platform"]))
            target_handle = handle_by_identity.get((target["handle"], target["platform"]))
            if not source_handle or not target_handle:
                continue

            fingerprint = str(source.get("pgp_fingerprint") or "").strip().upper()
            source_key = key_by_fingerprint.get(fingerprint)

            first_seen = pd.to_datetime(raw.get("first_seen"), errors="coerce")
            last_seen = pd.to_datetime(raw.get("last_seen"), errors="coerce")
            confidence = pd.to_numeric(raw.get("confidence"), errors="coerce")

            trust_records.append({
                "source_handle_id": source_handle.id,
                "target_handle_id": target_handle.id,
                "source_pgp_key_id": source_key.id if source_key else None,
                "relationship_type": str(raw.get("relationship_type") or "trust"),
                "source": str(raw.get("source") or "synthetic_dataset"),
                "confidence": float(confidence) if pd.notna(confidence) else 0.75,
                "first_seen": None if pd.isna(first_seen) else first_seen.to_pydatetime(),
                "last_seen": None if pd.isna(last_seen) else last_seen.to_pydatetime(),
            })

        if trust_records:
            trust_stmt = insert(TrustLink).values(trust_records)
            trust_stmt = trust_stmt.on_conflict_do_update(
                constraint="uq_trust_link_pair_type",
                set_={
                    "source_pgp_key_id": trust_stmt.excluded.source_pgp_key_id,
                    "source": trust_stmt.excluded.source,
                    "confidence": trust_stmt.excluded.confidence,
                    "last_seen": trust_stmt.excluded.last_seen,
                },
            )
            session.execute(trust_stmt)
            trust_count = len(trust_records)

    return len(pgp_records), trust_count


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
    pair_cols = [c for c in ["address", "associated_handle", "handle_id", "currency"] if c in merged.columns]
    all_pairs = merged[pair_cols].dropna(subset=["address", "associated_handle", "handle_id"]).to_dict(orient="records")

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



INVESTIGATION_EVIDENCE_TEMPLATES = (
    (
        "default_banner",
        "SYNTH-BANNER",
        "Controlled synthetic banner correlation signal.",
    ),
    (
        "ssl_cert_reuse",
        "SYNTH-CERT",
        "Controlled synthetic TLS/certificate reuse signal.",
    ),
    (
        "descriptor_timing",
        "SYNTH-TIMING",
        "Controlled synthetic descriptor-timing correlation signal.",
    ),
    (
        "exposed_status_page",
        "SYNTH-STATUS",
        "Controlled synthetic exposed-status-page signal.",
    ),
)


def ensure_investigation_evidence_for_all_actors(session: Session) -> int:
    """Ensure every seeded actor has a complete four-signal demo evidence trail.

    The bundled dataset contains real synthetic infrastructure findings for a
    subset of actors. For the investigation UI, every actor should still have
    a visible, provenance-tagged evidence trail. Missing signals are therefore
    filled with deterministic synthetic demo observations only; existing
    observations are never overwritten.
    """
    actors = session.query(Actor).order_by(Actor.actor_id.asc()).all()
    if not actors:
        return 0

    actor_ids = [actor.actor_id for actor in actors]
    existing_rows = (
        session.query(Observation.target, Observation.indicator_type)
        .filter(Observation.target.in_(actor_ids))
        .all()
    )
    existing = {
        (str(target).strip().lower(), str(indicator_type).strip().lower())
        for target, indicator_type in existing_rows
        if target and indicator_type
    }

    if settings.DEMO_MODE:
        now = datetime.combine(
            settings.DEMO_REFERENCE_DATE,
            datetime.max.time(),
            tzinfo=timezone.utc,
        )
    else:
        now = datetime.now(timezone.utc)
    records = []

    for actor in actors:
        for indicator_type, value_prefix, description in INVESTIGATION_EVIDENCE_TEMPLATES:
            key = (actor.actor_id.strip().lower(), indicator_type.lower())
            if key in existing:
                continue

            seed_bytes = hashlib.sha256(
                f"{actor.actor_id}:{indicator_type}".encode("utf-8")
            ).digest()
            confidence = round(0.68 + (seed_bytes[0] % 24) / 100.0, 2)
            age_days = seed_bytes[1] % 45
            timestamp = now - timedelta(
                days=age_days,
                hours=seed_bytes[2] % 24,
                minutes=seed_bytes[3] % 60,
            )
            token = hashlib.sha256(
                f"decypher:{actor.actor_id}:{indicator_type}".encode("utf-8")
            ).hexdigest()[:12].upper()

            records.append(
                {
                    "observation_id": f"SYN-{actor.actor_id}-{indicator_type.upper()}",
                    "indicator_type": indicator_type,
                    "detected": True,
                    "value": f"{value_prefix}-{token}",
                    "target": actor.actor_id,
                    "source": "synthetic_investigation_evidence",
                    "timestamp": timestamp,
                    "confidence": confidence,
                    "description": (
                        f"{description} "
                        f"Synthetic evidence generated for controlled SIH demonstration; "
                        f"not a real-world observation."
                    ),
                }
            )
            existing.add(key)

    if not records:
        return 0

    stmt = insert(Observation).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=["observation_id"])
    result = session.execute(stmt)
    session.commit()
    return int(result.rowcount or 0)


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
    trust_links_path = os.path.join(DATA_DIR, "trust_links.csv")

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
    pgp_records_count = 0
    trust_records_count = 0
    trust_df_for_neo4j = None

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

        if prepared_handles is not None:
            try:
                trust_df = pd.read_csv(trust_links_path) if os.path.exists(trust_links_path) else None
                trust_df_for_neo4j = trust_df
                pgp_records_count, trust_records_count = _upsert_pgp_keys_and_trust_links(
                    session,
                    prepared_handles,
                    trust_df,
                )
                session.commit()
                print(
                    f"[+] Upserted {pgp_records_count} PGP keys and "
                    f"{trust_records_count} trust links"
                )
            except Exception as e:
                session.rollback()
                print(f"[-] Error loading PGP/trust data: {e}")

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
            # A full SQL reset means the graph must be reset too; otherwise
            # legacy name-keyed Handle nodes can coexist with the new
            # stable-handle-ID graph and corrupt correlations.
            if reset_tables:
                graph_service.reset_graph()

            # wallet_pairs_for_neo4j contains the complete non-deduplicated
            # handle<->wallet relationships from the CSV.
            graph_service.sync_actor_batch(actor_records, handle_records, wallet_pairs_for_neo4j)
            if prepared_handles is not None:
                graph_service.sync_pgp_and_trust_graph(
                    prepared_handles.to_dict("records"),
                    trust_df_for_neo4j.to_dict("records") if trust_df_for_neo4j is not None else [],
                )
            print(
                f"[+] Synced {len(actor_records)} actors / {len(handle_records)} handles / "
                f"{len(wallet_pairs_for_neo4j)} handle-wallet links / "
                f"{pgp_records_count} PGP keys / {trust_records_count} trust links into Neo4j"
            )
        except Exception as e:
            print(f"[-] Neo4j sync skipped (is Neo4j running?): {e}")


if __name__ == "__main__":
    print("[*] Starting manual database ingestion...")
    init_db_and_load_csvs(reset_tables=False)
