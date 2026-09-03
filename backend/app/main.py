from fastapi import FastAPI
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.database.postgres import Base, engine
import app.models.sql_models
from app.routers import actors, search, feedback, export, auth, scanner, nlp
from app.middleware.audit_log import AuditLogMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically creates all database tables on startup
    print("[*] Creating and verifying database tables...")
    Base.metadata.create_all(bind=engine)
    print("[*] Database tables ready.")
    yield


app = FastAPI(
    title="Dark Web Threat Intel Platform API",
    description="Attribution, Stylometry, and Correlation Graph Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Attach Audit Log Middleware
app.add_middleware(AuditLogMiddleware)

# Attach Prometheus Monitoring
Instrumentator().instrument(app).expose(app)

# Include All Routers
app.include_router(auth.router)
app.include_router(actors.router)
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(export.router)
app.include_router(scanner.router)
app.include_router(nlp.router)
app.include_router(nlp.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "Threat Intel API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)