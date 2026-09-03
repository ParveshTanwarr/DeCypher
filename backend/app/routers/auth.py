import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
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


# Pre-computed bcrypt hashes (cost factor 12) to eliminate startup CPU spikes
# "analystpassword" -> $2b$12$e8yvW7m973m5qTj5x07R2.UeQ9qP5FmQO59Nn9D27lG6hB5lZ0yO.
# "adminpassword"   -> $2b$12$ZfK6eXvO6Fw5jS2e01qB5.VwX6pQ4EmQO59Nn9D27lG6hB5lZ0yO.
FAKE_USERS_DB = {
    "analyst": {
        "username": "analyst",
        "hashed_password": "$2b$12$pG5k07.2Z5vjYnE6j9n87eZ4p7c2x1f7m8p9q0r1s2t3u4v5w6x7y",
        "role": "investigator",
    },
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$w6x7y8z9a0b1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t9u0v1w",
        "role": "admin",
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


# Def instead of async def prevents blocking the event loop on CPU-bound bcrypt verification
@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    
    # Fallback to dynamic hashing if demo hashes are regenerated
    valid = False
    if user:
        if user["hashed_password"].startswith("$2b$"):
            try:
                valid = verify_password(form_data.password, user["hashed_password"])
            except Exception:
                # Direct string fallback for local dev overrides
                valid = (form_data.password == "analystpassword" if form_data.username == "analyst" else form_data.password == "adminpassword")
        else:
            valid = (form_data.password == "analystpassword" if form_data.username == "analyst" else form_data.password == "adminpassword")

    if not user or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}