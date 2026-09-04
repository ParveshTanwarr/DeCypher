import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


# Real pre-computed bcrypt hashes (cost factor 12) -- generated once with
# hash_password() so login doesn't re-hash on every startup.
# "analystpassword" -> hashed below
# "adminpassword"   -> hashed below
# (The previous hashes here were placeholder strings, not actual hashes of
# these passwords -- bcrypt.checkpw() against them returned False for
# "analyst" with no exception raised, so the old exception-based plaintext
# fallback never triggered and that account could never log in. Real
# hashes make the fallback below purely defensive, not load-bearing.)
FAKE_USERS_DB = {
    "analyst": {
        "username": "analyst",
        "hashed_password": "$2b$12$uiZ/.aZ95M/bjg3RE6IwNuQcTC/Zuk.fsRtHcifqmY/hodEnGFRn6",
        "role": "investigator",
    },
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$OZewJfXH5OceeFP2kbLIV.iY2vv1SNM3KqOU/WXYkbHaPQ8526Q86",
        "role": "admin",
    },
    # Machine-to-machine account so non-interactive callers (the infra
    # team's scanner pipeline, CI, etc.) can obtain a token the same way a
    # human does, now that every router requires one. There was no such
    # account before -- once auth got enforced, anything that isn't a
    # person logging into the dashboard had no way to authenticate at all.
    # Change this password before relying on it for anything real.
    "scanner_service": {
        "username": "scanner_service",
        "hashed_password": "$2b$12$ZTaSLukC8ISYhwwFz2oy1uB31ELLNqH471a6zfkSpa7oJl8hrUemC",
        "role": "service",
    },
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception


def require_role(*allowed_roles: str):
    """
    Role-check dependency factory. Authentication (is this a valid token?)
    was previously the whole story -- role was embedded in every JWT but
    nothing ever read it, so an "investigator" token and an "admin" token
    could do exactly the same things everywhere. This adds authorization
    on top for routes that need it.

    Usage: dependencies=[Depends(require_role("admin"))]
    """
    def _check(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return _check


# --- Minimal login rate limiting -----------------------------------------
# There was previously no protection at all on /auth/token -- unlimited
# password guesses against either demo account. This is a simple in-memory
# fixed-window limiter (per username+client IP): 5 attempts per 60s. It's
# intentionally lightweight for a hackathon -- it resets on restart and
# doesn't share state across multiple server instances, so it's not a
# production-grade solution, but it's a meaningful improvement over no
# protection at all.
_LOGIN_ATTEMPTS: dict = defaultdict(list)
_LOGIN_ATTEMPTS_LOCK = Lock()
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60


def _check_rate_limit(key: str) -> None:
    now = time.monotonic()
    with _LOGIN_ATTEMPTS_LOCK:
        attempts = [t for t in _LOGIN_ATTEMPTS[key] if now - t < _WINDOW_SECONDS]
        if len(attempts) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {_WINDOW_SECONDS} seconds.",
            )
        attempts.append(now)
        _LOGIN_ATTEMPTS[key] = attempts


# Def instead of async def prevents blocking the event loop on CPU-bound bcrypt verification
@router.post("/token", response_model=Token)
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(f"{form_data.username}:{client_ip}")

    user = FAKE_USERS_DB.get(form_data.username)

    valid = False
    if user:
        try:
            valid = verify_password(form_data.password, user["hashed_password"])
        except Exception:
            # Only reachable if hashed_password isn't a well-formed bcrypt
            # hash at all (e.g. someone pastes a raw password in by
            # mistake) -- treat that as a failed login rather than 500ing.
            valid = False

    if not user or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}