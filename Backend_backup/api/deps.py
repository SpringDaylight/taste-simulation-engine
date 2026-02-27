from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from repositories.user import UserRepository
from utils.jwt import decode_token


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    token = _extract_bearer_token(authorization)
    if not token:
        return None
    payload = decode_token(token, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = UserRepository(db).get(user_id)
    return user


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = get_current_user_optional(authorization=authorization, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
