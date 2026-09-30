import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, text

from app.database.postgres import Base, engine
from app.database.neo4j_client import neo4j_conn
from app.config import settings
import app.models.sql_models
from app.models.sql_models import Actor
from app.routers import actors, search, feedback, export, auth, scanner, nlp, correlation, ai
from app.middleware.audit_log import AuditLogMiddleware
from app.services.ingestion import ensure_investigation_evidence_for_all_actors, init_db_and_load_csvs

_DEV_DEFAULT_SECRET_KEY = "threat_intel_dev_secret_key_change_in_prod_12345"


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

    db = SessionLocal()
    try:
        return int(db.query(func.count(Actor.actor_id)).scalar() or 0)
    finally:
        db.close()


def _seed_investigation_evidence() -> int:
    from app.database.postgres import SessionLocal
    db = SessionLocal()
    try:
        return ensure_investigation_evidence_for_all_actors(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Creating and verifying database tables...")
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)
    print("[*] Database tables ready.")

    actor_count = await asyncio.to_thread(_bootstrap_demo_data)
    if actor_count:
        print(f"[+] Intelligence store contains {actor_count} actors.")

    seeded_evidence = await asyncio.to_thread(_seed_investigation_evidence)
    if seeded_evidence:
        print(f"[+] Seeded {seeded_evidence} synthetic investigation evidence records.")

    if not settings.SECRET_KEY or settings.SECRET_KEY == _DEV_DEFAULT_SECRET_KEY:
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
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(export.router)
app.include_router(scanner.router)
app.include_router(nlp.router)
app.include_router(correlation.router)
app.include_router(ai.router)


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

    status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    return {"status": status, "service": "Threat Intel API", "checks": checks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
