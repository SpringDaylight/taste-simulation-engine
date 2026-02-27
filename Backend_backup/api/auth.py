"""Authentication API endpoints (Kakao OAuth)"""
import os
import requests
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import get_db
from config import KAKAO_CLIENT_ID, KAKAO_CLIENT_SECRET, KAKAO_REDIRECT_URI
from schemas import (
    UserResponse,
    MessageResponse,
    UserSignupRequest,
    UserLoginRequest,
    PasswordChangeRequest,
    AuthTokenResponse,
    AccessTokenResponse,
)
from repositories.user import UserRepository
from repositories.user_auth import UserAuthRepository
from repositories.refresh_token import RefreshTokenRepository
from models import User
from utils.security import (
    hash_password,
    verify_password,
    validate_password_policy,
    generate_user_pk,
)
from utils.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    REFRESH_COOKIE_NAME,
    JWT_COOKIE_SECURE,
    JWT_COOKIE_SAMESITE,
    REFRESH_TOKEN_EXPIRES_DAYS,
)
from utils.refresh_token_store import RefreshTokenStore
from datetime import date, datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
        max_age=REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")


def _issue_tokens(user: User, db: Session, response: Response) -> str:
    refresh_token, jti, expires_at = create_refresh_token(user.id)
    token_hash = hash_token(refresh_token)
    
    # Redis에 refresh token 저장 시도
    ttl_seconds = REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60
    redis_success = RefreshTokenStore.save(
        token_hash=token_hash,
        user_id=user.id,
        jti=jti,
        expires_at=expires_at,
        ttl_seconds=ttl_seconds
    )
    
    # Redis 실패 시 PostgreSQL fallback
    if not redis_success:
        from repositories.refresh_token import RefreshTokenRepository
        print("⚠️ [Refresh] Redis unavailable, falling back to PostgreSQL")
        RefreshTokenRepository(db).create(
            user_id=user.id,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
        )
    
    _set_refresh_cookie(response, refresh_token)
    return create_access_token(user.id)


class KakaoSignupCompleteRequest(BaseModel):
    kakao_id: str
    provider: str
    nickname: str
    email: Optional[str] = None
    birth_date: Optional[str] = None  # YYYY-MM-DD format
    gender: Optional[str] = None

# Kakao OAuth URLs
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


# @router.get("/kakao/login")
# def kakao_login():
#     """Redirect to Kakao OAuth login page"""
#     if not KAKAO_CLIENT_ID:
#         raise HTTPException(status_code=500, detail="KAKAO_CLIENT_ID is not configured")
#     kakao_oauth_url = (
#         f"{KAKAO_AUTH_URL}?"
#         f"client_id={KAKAO_CLIENT_ID}&"
#         f"redirect_uri={KAKAO_REDIRECT_URI}&"
#         f"response_type=code"
#     )
#     return {"auth_url": kakao_oauth_url}
# 
# 
# @router.get("/kakao/callback")
# def kakao_callback(
#     code: str = Query(..., description="Authorization code from Kakao"),
#     response: Response,
#     db: Session = Depends(get_db)
# ):
#     """Handle Kakao OAuth callback"""
#     
#     print(f"Kakao callback received with code: {code[:20]}...")
#     print(f"Using redirect_uri: {KAKAO_REDIRECT_URI}")
#     print(f"Using client_id: {KAKAO_CLIENT_ID}")
#     print(f"Client secret configured: {bool(KAKAO_CLIENT_SECRET)}")
#     
    # Exchange code for access token
#     token_data = {
#         "grant_type": "authorization_code",
#         "client_id": KAKAO_CLIENT_ID,
#         "redirect_uri": KAKAO_REDIRECT_URI,
#         "code": code
#     }
#     
    # Add client_secret if configured
#     if KAKAO_CLIENT_SECRET:
#         token_data["client_secret"] = KAKAO_CLIENT_SECRET
#     
#     token_response = requests.post(
#         KAKAO_TOKEN_URL,
#         data=token_data,
#         headers={"Content-Type": "application/x-www-form-urlencoded"},
#         timeout=10
#     )
#     
#     if token_response.status_code != 200:
#         error_detail = token_response.json() if token_response.content else {}
#         print(f"Kakao token error: {token_response.status_code}, {error_detail}")
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Failed to get access token from Kakao: {error_detail.get('error_description', error_detail)}"
#         )
#     
#     token_data = token_response.json()
#     access_token = token_data.get("access_token")
#     if not access_token:
#         raise HTTPException(status_code=400, detail="Failed to get access token from Kakao")
#     
    # Get user info from Kakao
#     user_response = requests.get(
#         KAKAO_USER_INFO_URL,
#         headers={"Authorization": f"Bearer {access_token}"},
#         timeout=10
#     )
#     
#     if user_response.status_code != 200:
#         raise HTTPException(status_code=400, detail="Failed to get user info from Kakao")
#     
#     user_data = user_response.json()
#     kakao_id = str(user_data.get("id"))
#     kakao_account = user_data.get("kakao_account", {})
#     profile = kakao_account.get("profile", {})
#     
#     provider = "kakao"
#     provider_user_id = kakao_id
#     nickname = profile.get("nickname", f"User{kakao_id[:6]}")
#     email = kakao_account.get("email")
#     
    # Check if user exists
#     user_repo = UserRepository(db)
#     auth_repo = UserAuthRepository(db)
# 
#     auth = auth_repo.get_by_provider(provider, provider_user_id)
#     
#     if auth:
        # Existing user - issue JWT tokens
#         user = user_repo.get(auth.user_id)
#         access_token = _issue_tokens(user, db, response)
#         return {
#             "id": user.id,
#             "user_id": user.user_id,
#             "name": user.name,
#             "nickname": user.nickname,
#             "email": user.email,
#             "avatar_text": user.avatar_text,
#             "access_token": access_token,
#             "token_type": "bearer",
#             "is_new_user": False
#         }
#     else:
        # New user - return temporary info for signup flow
#         return {
#             "id": None,
#             "user_id": None,
#             "name": nickname,
#             "nickname": nickname,
#             "email": email,
#             "avatar_text": "카카오 로그인 사용자",
#             "access_token": access_token,
#             "is_new_user": True,
#             "kakao_id": kakao_id,  # For completing signup later
#             "provider": provider
#         }
# 
# 
# @router.post("/kakao/complete-signup", response_model=AuthTokenResponse, status_code=201)
# def complete_kakao_signup(
#     payload: KakaoSignupCompleteRequest,
#     response: Response,
#     db: Session = Depends(get_db)
# ):
#     """Complete Kakao user signup after additional info form"""
#     user_repo = UserRepository(db)
#     auth_repo = UserAuthRepository(db)
#     
    # Check if already registered
#     existing_auth = auth_repo.get_by_provider(payload.provider, payload.kakao_id)
#     if existing_auth:
#         raise HTTPException(status_code=400, detail="User already registered")
#     
    # Check nickname availability
#     if user_repo.get_by_nickname(payload.nickname):
#         raise HTTPException(status_code=400, detail="Nickname already exists")
#     
    # Parse birth_date if provided
#     birth_date_obj = None
#     if payload.birth_date:
#         try:
#             from datetime import datetime
#             birth_date_obj = datetime.strptime(payload.birth_date, "%Y-%m-%d").date()
#             
            # Validate birth_date
#             today = date.today()
#             if birth_date_obj > today:
#                 raise HTTPException(status_code=400, detail="Birth date cannot be in the future")
#             age = today.year - birth_date_obj.year - (
#                 (today.month, today.day) < (birth_date_obj.month, birth_date_obj.day)
#             )
#             if age > 120:
#                 raise HTTPException(status_code=400, detail="Birth date is not valid")
#         except ValueError:
#             raise HTTPException(status_code=400, detail="Invalid birth date format. Use YYYY-MM-DD")
#     
    # Create user
#     user = user_repo.create({
#         "id": generate_user_pk(),
#         "name": payload.nickname,
#         "nickname": payload.nickname,
#         "email": payload.email,
#         "birth_date": birth_date_obj,
#         "gender": payload.gender,
#         "avatar_text": "카카오 로그인 사용자"
#     })
#     
    # Create auth record
#     auth_repo.create({
#         "user_id": user.id,
#         "provider": payload.provider,
#         "provider_user_id": payload.kakao_id,
#         "email": payload.email
#     })
#     
#     user_response = UserResponse(
#         id=user.id,
#         name=user.name,
#         user_id=user.user_id,
#         nickname=user.nickname,
#         email=user.email,
#         birth_date=user.birth_date,
#         gender=user.gender,
#         avatar_text=user.avatar_text,
#         created_at=user.created_at,
#     )
#     access_token = _issue_tokens(user, db, response)
#     return AuthTokenResponse(access_token=access_token, user=user_response)
# 
# 
@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(payload: UserSignupRequest, db: Session = Depends(get_db)):
    """Create a local user account"""
    user_repo = UserRepository(db)

    if payload.password != payload.password_confirm:
        raise HTTPException(status_code=400, detail="Password confirmation does not match")

    if payload.birth_date:
        today = date.today()
        if payload.birth_date > today:
            raise HTTPException(status_code=400, detail="Birth date cannot be in the future")
        age = today.year - payload.birth_date.year - (
            (today.month, today.day) < (payload.birth_date.month, payload.birth_date.day)
        )
        if age > 120:
            raise HTTPException(status_code=400, detail="Birth date is not valid")

    if not validate_password_policy(payload.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be 8-20 chars and include at least 2 of: uppercase, lowercase, number, special"
        )

    if user_repo.get_by_user_id(payload.user_id):
        raise HTTPException(status_code=400, detail="User ID already exists")
    if user_repo.get_by_nickname(payload.nickname):
        raise HTTPException(status_code=400, detail="Nickname already exists")
    if user_repo.get_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    db_user = user_repo.create(
        {
            "id": generate_user_pk(),
            "user_id": payload.user_id,
            "name": payload.name,
            "nickname": payload.nickname,
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "birth_date": payload.birth_date,
        }
    )

    return UserResponse(
        id=db_user.id,
        name=db_user.name,
        user_id=db_user.user_id,
        nickname=db_user.nickname,
        email=db_user.email,
        birth_date=db_user.birth_date,
        gender=db_user.gender,
        avatar_text=db_user.avatar_text,
        created_at=db_user.created_at,
    )


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login with user_id and password"""
    user_repo = UserRepository(db)
    user = user_repo.get_by_user_id(payload.user_id)

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_response = UserResponse(
        id=user.id,
        name=user.name,
        user_id=user.user_id,
        nickname=user.nickname,
        email=user.email,
        birth_date=user.birth_date,
        gender=user.gender,
        avatar_text=user.avatar_text,
        created_at=user.created_at,
    )
    access_token = _issue_tokens(user, db, response)
    return AuthTokenResponse(access_token=access_token, user=user_response)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Issue a new access token using refresh token cookie"""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    payload = decode_token(refresh_token, expected_type="refresh")
    token_hash = hash_token(refresh_token)
    
    # Redis에서 refresh token 조회 (fallback to PostgreSQL)
    stored = RefreshTokenStore.get(token_hash)
    
    # Redis 실패 시 PostgreSQL fallback
    if stored is None:
        from repositories.refresh_token import RefreshTokenRepository
        print("⚠️ [Refresh] Redis unavailable, falling back to PostgreSQL")
        
        repo = RefreshTokenRepository(db)
        stored_db = repo.get_by_hash(token_hash)
        
        if not stored_db or stored_db.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Refresh token expired or revoked")
        
        if stored_db.expires_at and stored_db.expires_at.replace(tzinfo=None) < datetime.utcnow():
            repo.revoke(stored_db)
            raise HTTPException(status_code=401, detail="Refresh token expired")
        
        # PostgreSQL에서 가져온 경우 revoke
        repo.revoke(stored_db)
        stored = {"user_id": stored_db.user_id}
    else:
        # Redis에서 가져온 경우
        expires_at = datetime.fromisoformat(stored["expires_at"])
        if expires_at.replace(tzinfo=None) < datetime.utcnow():
            RefreshTokenStore.revoke(token_hash)
            raise HTTPException(status_code=401, detail="Refresh token expired")
        
        # Rotate refresh token (기존 토큰 무효화)
        RefreshTokenStore.revoke(token_hash)
    
    user_id = stored.get("user_id") or payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = _issue_tokens(user, db, response)
    return AccessTokenResponse(access_token=new_access_token)


@router.post("/password", response_model=MessageResponse)
def change_password(payload: PasswordChangeRequest, db: Session = Depends(get_db)):
    """Change password for a local user"""
    user_repo = UserRepository(db)
    user = user_repo.get_by_user_id(payload.user_id)

    if not user or not user.password_hash:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    if payload.new_password != payload.new_password_confirm:
        raise HTTPException(status_code=400, detail="Password confirmation does not match")

    if not validate_password_policy(payload.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be 8-20 chars and include at least 2 of: uppercase, lowercase, number, special"
        )

    user_repo.update(user.id, {"password_hash": hash_password(payload.new_password)})
    return MessageResponse(message="Password updated successfully")


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Logout user"""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        token_hash = hash_token(refresh_token)
        
        # Redis에서 refresh token 무효화 시도
        redis_success = RefreshTokenStore.revoke(token_hash)
        
        # Redis 실패 시 PostgreSQL fallback
        if not redis_success:
            from repositories.refresh_token import RefreshTokenRepository
            print("⚠️ [Logout] Redis unavailable, falling back to PostgreSQL")
            repo = RefreshTokenRepository(db)
            stored = repo.get_by_hash(token_hash)
            if stored and stored.revoked_at is None:
                repo.revoke(stored)

    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully")
