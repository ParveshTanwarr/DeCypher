from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt
from datetime import datetime
from app.database.postgres import SessionLocal
from app.models.sql_models import AuditLog
from app.config import settings

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract identity from token header if provided
        auth_header = request.headers.get("Authorization")
        username = "anonymous"

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                username = payload.get("sub", "anonymous")
            except Exception:
                username = "invalid_token"

        # Record incoming queries into PostgreSQL (filters out noise like docs/metrics)
        path = request.url.path
        if not path.startswith(("/docs", "/openapi.json", "/metrics", "/favicon.ico")):
            db = SessionLocal()
            try:
                log_entry = AuditLog(
                    username=username,
                    method=request.method,
                    endpoint=path,
                    query_params=str(request.query_params),
                    timestamp=datetime.utcnow()
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                print(f"[-] Audit logging failed: {e}")
            finally:
                db.close()

        response = await call_next(request)
        return response