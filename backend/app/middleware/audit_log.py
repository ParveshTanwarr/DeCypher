import asyncio
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt

from app.database.postgres import SessionLocal
from app.models.sql_models import AuditLog
from app.config import settings

IGNORED_PATHS = ("/docs", "/openapi.json", "/metrics", "/favicon.ico", "/health")


def _write_audit_log(username: str, method: str, endpoint: str, query_params: str):
    db = SessionLocal()
    try:
        log_entry = AuditLog(
            username=username,
            method=method,
            endpoint=endpoint,
            query_params=query_params,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"[-] Audit logging failed: {e}")
    finally:
        db.close()


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Extract identity from token header if provided
        auth_header = request.headers.get("Authorization")
        username = "anonymous"

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = payload.get("sub", "anonymous")
            except Exception:
                username = "invalid_token"

        path = request.url.path

        # 2. Asynchronously write audit log without stalling the event loop
        if not path.startswith(IGNORED_PATHS):
            await asyncio.to_thread(
                _write_audit_log,
                username=username,
                method=request.method,
                endpoint=path,
                query_params=str(request.query_params),
            )

        response = await call_next(request)
        return response