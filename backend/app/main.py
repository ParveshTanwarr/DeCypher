import asyncio
import csv
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, inspect, text

from app.database.postgres import Base, engine
from app.database.neo4j_client import neo4j_conn
from app.config import settings
import app.models.sql_models
import app.models.advanced_models
from app.models.sql_models import (
    Actor,
    DarkWebHandle,
    Observation,
    PGPKey,
    ScanTarget,
    TemporalEvent,
    TrustLink,
    Wallet,
)
from app.routers import actors, search, feedback, export, auth, scanner, nlp, correlation, ai, behavioral, integrity, analytics, advanced
from app.middleware.audit_log import AuditLogMiddleware
from app.services.ingestion import ensure_investigation_evidence_for_all_actors, init_db_and_load_csvs
from app.services.nlp_service import nlp_service
from app.services.temporal_events import materialize_temporal_events
from app.services.observation_scope import build_observation_target_keys
from app.services.advanced_intelligence import MerkleEvidenceService



def _ensure_compatibility_schema() -> None:
    """Apply small forward-only schema changes that create_all cannot add."""
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    existing_columns = {
        column["name"]
        for column in inspector.get_columns("darkweb_handles")
    }

    with engine.begin() as connection:
        if "source_handle_id" not in existing_columns:
            connection.exec_driver_sql(
                "ALTER TABLE darkweb_handles ADD COLUMN source_handle_id VARCHAR(64)"
            )
        # Backfill the stable source IDs for existing synthetic rows. The
        # relational integer PK remains unchanged and continues to serve SQL
        # foreign keys; the source ID is exclusively the cross-system identity.
        handles_path = Path(__file__).resolve().parents[2] / "data" / "handles.csv"
        if handles_path.exists():
            with handles_path.open("r", encoding="utf-8", newline="") as file:
                for row in csv.DictReader(file):
                    source_id = (row.get("handle_id") or "").strip()
                    handle = (row.get("handle_name") or "").strip()
                    platform = (row.get("marketplace") or "").strip() or None
                    actor_id = (row.get("actor_id") or "").strip()
                    if not source_id or not handle:
                        continue
                    connection.execute(
                        text(
                            "UPDATE darkweb_handles "
                            "SET source_handle_id = :source_id "
                            "WHERE handle = :handle "
                            "AND ((platform = :platform) OR (platform IS NULL AND :platform IS NULL)) "
                            "AND (actor_id = :actor_id OR :actor_id = '') "
                            "AND (source_handle_id IS NULL OR source_handle_id <> :source_id)"
                        ),
                        {
                            "source_id": source_id,
                            "handle": handle,
                            "platform": platform,
                            "actor_id": actor_id,
                        },
                    )

        # Repair accidental duplicate canonical IDs after CSV backfill, then
        # enforce uniqueness for the canonical cross-system identity.
        connection.exec_driver_sql(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY source_handle_id
                        ORDER BY id ASC
                    ) AS rn
                FROM darkweb_handles
                WHERE source_handle_id IS NOT NULL
            )
            UPDATE darkweb_handles AS target
            SET source_handle_id = 'legacy:' || target.id::text
            FROM ranked
            WHERE target.id = ranked.id
              AND ranked.rn > 1
            """
        )

        connection.exec_driver_sql(
            "UPDATE darkweb_handles "
            "SET source_handle_id = 'legacy:' || id::text "
            "WHERE source_handle_id IS NULL"
        )

        # The old schema used handle+platform as a unique key. That
        # incorrectly collapsed legitimate repeated visible handles across actors.
        # Drop it when present; stable source_handle_id is the canonical identity.
        connection.exec_driver_sql(
            "ALTER TABLE darkweb_handles DROP CONSTRAINT IF EXISTS uq_handle_platform"
        )
        connection.exec_driver_sql(
            "DROP INDEX IF EXISTS uq_handle_platform"
        )
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_darkweb_handles_source_handle_id "
            "ON darkweb_handles (source_handle_id) "
            "WHERE source_handle_id IS NOT NULL"
        )


def _bootstrap_demo_data() -> int:
    """Populate a truly fresh demo database once, then return actor count."""
    from app.database.postgres import SessionLocal

    db = SessionLocal()
    try:
        actor_count = int(db.query(func.count(Actor.actor_id)).scalar() or 0)
    finally:
        db.close()

    if actor_count == 0:
        init_db_and_load_csvs(reset_tables=False, sync_neo4j=True)
    else:
        # Repair an existing pre-canonical database once if its handle row count
        # does not match the source fixture. This is intentionally gated so normal
        # API restarts do not re-ingest the full dataset.
        handles_path = Path(__file__).resolve().parents[2] / "data" / "handles.csv"
        expected_handles = 0
        if handles_path.exists():
            with handles_path.open("r", encoding="utf-8", newline="") as file:
                expected_handles = sum(1 for _ in csv.DictReader(file))
        db = SessionLocal()
        try:
            actual_handles = int(db.query(func.count(DarkWebHandle.id)).scalar() or 0)
        finally:
            db.close()
        if expected_handles and actual_handles != expected_handles:
            print(
                f"[*] Handle fixture reconciliation required: "
                f"expected={expected_handles}, actual={actual_handles}"
            )
            init_db_and_load_csvs(reset_tables=False, sync_neo4j=False)

    db = SessionLocal()
    try:
        return int(db.query(func.count(Actor.actor_id)).scalar() or 0)
    finally:
        db.close()


def _backfill_graph_if_needed(actor_count: int) -> None:
    """Rebuild Neo4j when canonical projections are incomplete and re-project SQL evidence."""
    if actor_count <= 0:
        return

    from app.database.postgres import SessionLocal
    from app.services import graph_service

    db = SessionLocal()
    try:
        expected = {
            "actors": int(db.query(func.count(Actor.actor_id)).scalar() or 0),
            "handles": int(db.query(func.count(DarkWebHandle.id)).scalar() or 0),
            "wallets": int(db.query(func.count(func.distinct(Wallet.address))).scalar() or 0),
            "pgp_keys": int(db.query(func.count(PGPKey.id)).scalar() or 0),
            "trust_links": int(db.query(func.count(TrustLink.id)).scalar() or 0),
            "observations": int(db.query(func.count(Observation.id)).scalar() or 0),
            "temporal_events": int(db.query(func.count(TemporalEvent.id)).scalar() or 0),
        }

        try:
            counts = {
                "actors": int((neo4j_conn.query("MATCH (n:Actor) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
                "handles": int((neo4j_conn.query("MATCH (n:Handle) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
                "wallets": int((neo4j_conn.query("MATCH (n:Wallet) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
                "pgp_keys": int((neo4j_conn.query("MATCH (n:PGPKey) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
                "trust_links": int((neo4j_conn.query("MATCH (:Handle)-[r:TRUSTS]->(:Handle) RETURN count(r) AS count") or [{}])[0].get("count") or 0),
                "observations": int((neo4j_conn.query("MATCH (n:Observation) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
                "temporal_events": int((neo4j_conn.query("MATCH (n:Event) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
                "numeric_handle_ids": int((neo4j_conn.query(
                    'MATCH (n:Handle) WHERE n.handle_id =~ "^[0-9]+$" RETURN count(n) AS count'
                ) or [{}])[0].get("count") or 0),
            }
        except Exception:
            raise

        incomplete = any(counts[name] < expected[name] for name in expected)
        legacy_nodes = counts["numeric_handle_ids"] > 0
        if incomplete or legacy_nodes:
            print(
                "[*] Neo4j graph projection is incomplete or contains legacy handle IDs; "
                "running a deterministic graph rebuild. "
                f"expected={expected}, actual={counts}"
            )
            graph_service.reset_graph()
            init_db_and_load_csvs(reset_tables=False, sync_neo4j=True)

        # Re-project observations from PostgreSQL after every startup. The SQL
        # store is authoritative, and this also repairs observations inserted by
        # the synthetic evidence seeder or background scanner.
        actors = db.query(Actor).all()
        actor_ids = [actor.actor_id for actor in actors]
        actor_set = set(actor_ids)
        handles = db.query(DarkWebHandle).all()
        scan_targets = db.query(ScanTarget).filter(
            ScanTarget.actor_id.in_(actor_ids)
        ).all()
        handles_by_actor: dict[str, list[DarkWebHandle]] = {}
        for handle in handles:
            if handle.actor_id:
                handles_by_actor.setdefault(str(handle.actor_id), []).append(handle)
        targets_by_actor: dict[str, list[ScanTarget]] = {}
        for target in scan_targets:
            if target.actor_id:
                targets_by_actor.setdefault(str(target.actor_id), []).append(target)

        target_to_actor: dict[str, str] = {}
        for actor in actors:
            keys = build_observation_target_keys(
                actor.actor_id,
                actor.primary_handle,
                handles_by_actor.get(str(actor.actor_id), []),
                targets_by_actor.get(str(actor.actor_id), []),
            )
            for key in keys:
                target_to_actor[key] = str(actor.actor_id)

        observations_by_actor: dict[str, list[dict]] = {}
        for observation in db.query(Observation).all():
            actor_id = target_to_actor.get((observation.target or "").strip().lower())
            if actor_id and actor_id in actor_set:
                observations_by_actor.setdefault(actor_id, []).append({
                    "observation_id": observation.observation_id,
                    "indicator_type": observation.indicator_type,
                    "detected": observation.detected,
                    "value": observation.value,
                    "target": observation.target,
                    "source": observation.source,
                    "confidence": observation.confidence,
                    "description": observation.description,
                    "timestamp": observation.timestamp.isoformat() if observation.timestamp else None,
                })

        for actor_id, observations in observations_by_actor.items():
            if observations:
                graph_service.sync_actor_observations(actor_id, observations)

        # Temporal events are SQL-backed but are projected here as part of the
        # graph readiness repair, so a rebuilt graph is complete before startup
        # finishes. The dedicated backfill helper remains idempotent.
        materialize_temporal_events(db)
        db.commit()

        # Startup is not considered graph-ready until the rebuilt projection
        # actually contains the SQL-authoritative minimums. This prevents a
        # swallowed Neo4j syntax/projection error from producing a "healthy"
        # API with an incomplete graph.
        verified = {
            "actors": int((neo4j_conn.query("MATCH (n:Actor) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
            "handles": int((neo4j_conn.query("MATCH (n:Handle) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
            "wallets": int((neo4j_conn.query("MATCH (n:Wallet) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
            "pgp_keys": int((neo4j_conn.query("MATCH (n:PGPKey) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
            "trust_links": int((neo4j_conn.query("MATCH (:Handle)-[r:TRUSTS]->(:Handle) RETURN count(r) AS count") or [{}])[0].get("count") or 0),
            "observations": int((neo4j_conn.query("MATCH (n:Observation) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
            "temporal_events": int((neo4j_conn.query("MATCH (n:Event) RETURN count(n) AS count") or [{}])[0].get("count") or 0),
            "event_handle_links": int((neo4j_conn.query(
                "MATCH (:Event)-[:DESCRIBES]->(:Handle) RETURN count(*) AS count"
            ) or [{}])[0].get("count") or 0),
            "numeric_handle_ids": int((neo4j_conn.query(
                'MATCH (n:Handle) WHERE n.handle_id =~ "^[0-9]+$" RETURN count(n) AS count'
            ) or [{}])[0].get("count") or 0),
        }
        if any(verified[name] < expected[name] for name in expected):
            raise RuntimeError(
                f"Neo4j graph verification failed: expected={expected}, verified={verified}"
            )
        if verified["numeric_handle_ids"] > 0:
            raise RuntimeError(
                f"Neo4j graph verification found legacy numeric handle IDs: {verified}"
            )
        if expected["temporal_events"] > 0 and verified["event_handle_links"] == 0:
            raise RuntimeError(
                f"Neo4j temporal graph verification found no Event->Handle links: {verified}"
            )
    except Exception as exc:
        db.rollback()
        # Graph completeness is a startup invariant for this deployment.
        # Failing here is preferable to silently serving a partial graph.
        print(f"[!] Neo4j graph backfill failed: {exc}")
        raise
    finally:
        db.close()


def _seed_investigation_evidence() -> int:
    from app.database.postgres import SessionLocal
    db = SessionLocal()
    try:
        return ensure_investigation_evidence_for_all_actors(db)
    finally:
        db.close()


def _backfill_temporal_events() -> int:
    from app.database.postgres import SessionLocal
    db = SessionLocal()
    try:
        added = materialize_temporal_events(db)
        db.commit()
        return added
    finally:
        db.close()


def _seal_merkle_blocks() -> int:
    from app.database.postgres import SessionLocal
    db = SessionLocal()
    try:
        created = MerkleEvidenceService(db).seal_pending()
        db.commit()
        return created
    finally:
        db.close()


def _backfill_evidence_ledger() -> int:
    from app.database.postgres import SessionLocal
    from app.services.evidence_ledger import EvidenceLedgerService

    db = SessionLocal()
    try:
        appended = EvidenceLedgerService(db).backfill_missing_observations()
        db.commit()
        return appended
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Creating and verifying database tables...")
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)
    await asyncio.to_thread(_ensure_compatibility_schema)
    print("[*] Database tables ready.")

    actor_count = await asyncio.to_thread(_bootstrap_demo_data)
    seeded_evidence = await asyncio.to_thread(_seed_investigation_evidence)
    if seeded_evidence:
        print(f"[+] Seeded {seeded_evidence} synthetic investigation evidence records.")
    if actor_count:
        print(f"[+] Intelligence store contains {actor_count} actors.")
        await asyncio.to_thread(_backfill_graph_if_needed, actor_count)

    ledger_backfill = await asyncio.to_thread(_backfill_evidence_ledger)
    if ledger_backfill:
        print(f"[+] Added {ledger_backfill} missing evidence integrity ledger entries.")

    merkle_blocks = await asyncio.to_thread(_seal_merkle_blocks)
    if merkle_blocks:
        print(f"[+] Sealed {merkle_blocks} evidence Merkle block(s).")

    temporal_event_backfill = await asyncio.to_thread(_backfill_temporal_events)
    if temporal_event_backfill:
        print(f"[+] Added {temporal_event_backfill} temporal evidence events.")

    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is missing or still using the development default. "
            "Set a unique SECRET_KEY in backend/.env before starting the API."
        )

    yield

    print("[*] Shutting down services and database connections...")
    engine.dispose()


app = FastAPI(
    title="Dark Web Threat Intel Platform API",
    description="Attribution, Stylometry, and Correlation Graph Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Keep credentialed browser access limited to explicitly configured frontend
# origins, and expose the download filename header so the React client can
# preserve the backend-provided CSV/JSON/PDF filenames across CORS.
cors_origins = [
    origin.strip()
    for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)

app.add_middleware(AuditLogMiddleware)
Instrumentator().instrument(app).expose(app)

app.include_router(auth.router)
app.include_router(actors.router)
app.include_router(behavioral.router)
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(export.router)
app.include_router(scanner.router)
app.include_router(nlp.router)
app.include_router(correlation.router)
app.include_router(ai.router)
app.include_router(integrity.router)
app.include_router(analytics.router)
app.include_router(advanced.router)


@app.get("/health", tags=["Health"])
def health_check():
    """Return dependency-aware health without hiding partial outages."""
    checks = {}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["postgres"] = "healthy"
    except Exception as exc:
        checks["postgres"] = f"unavailable: {type(exc).__name__}"

    try:
        neo4j_conn.query("RETURN 1 AS ok")
        checks["neo4j"] = "healthy"
    except Exception as exc:
        checks["neo4j"] = f"unavailable: {type(exc).__name__}"

    try:
        import redis
        redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1).ping()
        checks["redis"] = "healthy"
    except Exception as exc:
        checks["redis"] = f"unavailable: {type(exc).__name__}"

    checks["nlp"] = nlp_service.engine_status

    status = "healthy" if all(v == "healthy" or v == "validated_model" for v in checks.values()) else "degraded"
    return {"status": status, "service": "Threat Intel API", "checks": checks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
