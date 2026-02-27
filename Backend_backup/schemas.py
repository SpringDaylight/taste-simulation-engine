"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: float},
    )


# ============================================
# User Schemas
# ============================================

class UserBase(BaseSchema):
    name: str
    avatar_text: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None


class UserCreate(UserBase):
    id: str


class UserUpdate(BaseSchema):
    name: Optional[str] = None
    avatar_text: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    popcorn: Optional[int] = None
    exp: Optional[int] = None


class UserSearchItem(BaseSchema):
    id: str
    user_id: Optional[str] = None
    nickname: Optional[str] = None
    avatar_text: Optional[str] = None


class UserSearchResponse(BaseSchema):
    users: List[UserSearchItem]


class UserSignupRequest(BaseSchema):
    user_id: str
    name: str
    nickname: str
    email: str
    password: str
    password_confirm: str
    birth_date: Optional[date] = None


class UserLoginRequest(BaseSchema):
    user_id: str
    password: str


class PasswordChangeRequest(BaseSchema):
    user_id: str
    current_password: str
    new_password: str
    new_password_confirm: str


class AccessTokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"


class AuthTokenResponse(AccessTokenResponse):
    user: "UserResponse"


class DailyQuestionResponse(BaseSchema):
    answered: bool
    question: Optional[str] = None
    message: Optional[str] = None


class DailyQuestionAnswerRequest(BaseSchema):
    user_id: Optional[str] = None
    answer: str


class RouletteStatusResponse(BaseSchema):
    can_spin: bool
    next_available_at: Optional[str] = None


class RouletteSpinRequest(BaseSchema):
    user_id: Optional[str] = None


class RouletteSpinResponse(BaseSchema):
    item: str
    popcorn_gain: int
    exp_gain: int
    total_popcorn: int
    total_exp: int


class RouletteConfigItem(BaseSchema):
    label: str
    probability: str
    popcorn_gain: int
    exp_gain: int


class RouletteConfigResponse(BaseSchema):
    items: List[RouletteConfigItem]


# ============================================
# Movie Schemas
# ============================================

class MovieBase(BaseSchema):
    title: str
    release: Optional[date] = None
    runtime: Optional[int] = None
    synopsis: Optional[str] = None
    poster_url: Optional[str] = None


class MovieCreate(MovieBase):
    pass


class MovieUpdate(BaseSchema):
    title: Optional[str] = None
    release: Optional[date] = None
    runtime: Optional[int] = None
    synopsis: Optional[str] = None
    poster_url: Optional[str] = None


class MovieResponse(MovieBase):
    id: int
    created_at: datetime
    avg_rating: Optional[Decimal] = None
    genres: List[str] = []
    tags: List[str] = []
    reviews_count: int = 0



class MovieListResponse(BaseSchema):
    movies: List[MovieResponse]
    total: int
    page: int
    page_size: int


# ============================================
# Review Schemas
# ============================================

class ReviewBase(BaseSchema):
    rating: Decimal = Field(..., ge=0.5, le=5.0, description="0.5~5.0, 0.5 단위")
    content: Optional[str] = None
    keywords: List[str] = []
    is_public: bool = True


class ReviewCreate(ReviewBase):
    movie_id: int


class ReviewUpdate(BaseSchema):
    rating: Optional[Decimal] = Field(None, ge=0.5, le=5.0)
    content: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_public: Optional[bool] = None


class ReviewResponse(ReviewBase):
    id: int
    user_id: str
    user_nickname: Optional[str] = None
    movie_id: int
    created_at: datetime
    likes_count: int = 0
    dislikes_count: int = 0
    comments_count: int = 0
    keywords: List[str] = []



class ReviewListResponse(BaseSchema):
    reviews: List[ReviewResponse]
    total: int


# ============================================
# Comment Schemas
# ============================================

class CommentBase(BaseSchema):
    content: str
    is_public: bool = True


class CommentCreate(CommentBase):
    review_id: int
    parent_comment_id: Optional[int] = None


class CommentUpdate(BaseSchema):
    content: Optional[str] = None
    is_public: Optional[bool] = None


class CommentResponse(CommentBase):
    id: int
    review_id: int
    parent_comment_id: Optional[int] = None
    user_id: str
    user_nickname: Optional[str] = None
    created_at: datetime
    likes_count: int = 0
    dislikes_count: int = 0


# ============================================
# Like Schemas
# ============================================

class LikeCreate(BaseSchema):
    review_id: int
    is_like: bool = True


class LikeResponse(BaseSchema):
    id: int
    review_id: int
    user_id: str
    is_like: bool
    created_at: datetime


# ============================================
# Watched Movie Schemas
# ============================================

class WatchedMovieCreate(BaseSchema):
    movie_id: int


class WatchedMovieResponse(BaseSchema):
    movie_id: int
    title: str
    poster_url: Optional[str] = None
    watched_at: datetime


class WatchedMovieListResponse(BaseSchema):
    items: List[WatchedMovieResponse]
    total: int


# ============================================
# Taste Analysis Schemas
# ============================================

class TasteAnalysisResponse(BaseSchema):
    user_id: str
    summary_text: Optional[str] = None
    updated_at: datetime


# ============================================
# User Preference Schemas (ML)
# ============================================

class UserPreferenceResponse(BaseSchema):
    user_id: str
    preference_vector_json: Dict[str, Any]
    persona_code: Optional[str] = None
    boost_tags: List[str] = []
    penalty_tags: List[str] = []
    
    # Survey fields
    favorite_genres: Optional[List[str]] = None
    disliked_genres: Optional[List[str]] = None
    viewing_context: Optional[str] = None
    preferred_vibe: Optional[str] = None
    interest_keywords: Optional[List[str]] = None
    preferred_origin: Optional[str] = None
    
    updated_at: datetime


# ============================================
# Movie Vector Schemas (ML)
# ============================================

class MovieVectorResponse(BaseSchema):
    movie_id: int
    emotion_scores: Dict[str, float]
    narrative_traits: Dict[str, float]
    ending_preference: Dict[str, float]
    updated_at: datetime


# ============================================
# Generic Response
# ============================================

class MessageResponse(BaseSchema):
    message: str
    detail: Optional[str] = None


class LikeToggleResponse(BaseSchema):
    message: str
    review_id: int
    likes_count: int
    dislikes_count: int


class CommentLikeToggleResponse(BaseSchema):
    message: str
    comment_id: int
    likes_count: int
    dislikes_count: int


class ErrorResponse(BaseSchema):
    error: str
    detail: Optional[str] = None


AuthTokenResponse.model_rebuild()
