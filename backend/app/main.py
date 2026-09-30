import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.database.postgres import Base, engine
from app.config import settings
import app.models.sql_models
from app.routers import actors, search, feedback, export, auth, scanner, nlp, correlation, ai
from app.middleware.audit_log import AuditLogMiddleware

_DEV_DEFAULT_SECRET_KEY = "threat_intel_dev_secret_key_change_in_prod_12345"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Creating and verifying database tables...")
    await asyncio.to_thread(Base.metadata.create_all, bind=engine)
    print("[*] Database tables ready.")

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
