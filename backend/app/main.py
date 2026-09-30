import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func

from app.database.postgres import Base, engine
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
        init_db_and_load_csvs(reset_tables=False, sync_neo4j=False)

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

    if settings.SECRET_KEY == _DEV_DEFAULT_SECRET_KEY:
        print(
            "[!] WARNING: SECRET_KEY is still the checked-in development default. "
            "Every JWT this instance issues can be forged by anyone who has read "
            "this repo. Set a real SECRET_KEY via .env before this leaves local dev."
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
    return {"status": "healthy", "service": "Threat Intel API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
