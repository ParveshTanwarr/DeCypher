from fastapi import FastAPI
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.services.ingestion import init_db_and_load_csvs
from app.routers import actors, search, feedback, export, auth
from app.middleware.audit_log import AuditLogMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Initializing database and checking CSV files...")
    init_db_and_load_csvs()
    yield

app = FastAPI(
    title="Dark Web Threat Intel Platform API",
    description="Attribution, Stylometry, and Correlation Graph Engine",
    version="1.0.0",
    lifespan=lifespan
)

# 1. Attach Audit Log Middleware
app.add_middleware(AuditLogMiddleware)

# 2. Attach Prometheus metrics monitoring at /metrics
Instrumentator().instrument(app).expose(app)

# 3. Include all endpoint routers
app.include_router(auth.router)
app.include_router(actors.router)
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(export.router)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "Threat Intel API"}