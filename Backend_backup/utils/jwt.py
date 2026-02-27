import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from fastapi import HTTPException, status

from config import (
    JWT_SECRET,
    JWT_ALG,
    ACCESS_TOKEN_EXPIRES_MIN,
    REFRESH_TOKEN_EXPIRES_DAYS,
    JWT_COOKIE_SECURE,
    JWT_COOKIE_SAMESITE,
    REFRESH_TOKEN_COOKIE_NAME,
)

REFRESH_COOKIE_NAME = REFRESH_TOKEN_COOKIE_NAME


def _ensure_secret() -> None:
    if not JWT_SECRET:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT_SECRET is not configured")


def create_access_token(user_id: str) -> str:
    _ensure_secret()
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    _ensure_secret()
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token, jti, expires_at


def decode_token(token: str, expected_type: str) -> Dict[str, Any]:
    _ensure_secret()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
