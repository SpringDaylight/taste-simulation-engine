"""
User API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import get_db
from api.deps import get_current_user as get_current_user_dep
from schemas import (
    UserResponse, UserCreate, UserUpdate,
    ReviewResponse, ReviewListResponse,
    TasteAnalysisResponse, MessageResponse,
    WatchedMovieCreate, WatchedMovieListResponse, WatchedMovieResponse,
    UserSearchResponse, UserSearchItem
)
from repositories.user import UserRepository
from repositories.review import ReviewRepository
from repositories.watched import WatchedMovieRepository
from repositories.movie import MovieRepository

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user(
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db)
):
    """Get current user info"""
    repo = UserRepository(db)
    user = repo.get(current_user.id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        name=user.name,
        user_id=user.user_id,
        nickname=user.nickname,
        email=user.email,
        birth_date=user.birth_date,
        gender=user.gender,
        avatar_text=user.avatar_text,
        popcorn=user.popcorn,
        exp=user.exp,
        created_at=user.created_at
    )


@router.get("/search", response_model=UserSearchResponse)
def search_users(
    query: str = Query(..., min_length=1, description="Search by name, user_id or nickname"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search users for group assignment"""
    repo = UserRepository(db)
    users = repo.search(query, limit=limit)
    items = [
        UserSearchItem(
            id=user.id,
            user_id=user.user_id,
            nickname=user.nickname,
            avatar_text=user.avatar_text,
        )
        for user in users
    ]
    return UserSearchResponse(users=items)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    repo = UserRepository(db)
    
    # Check if user already exists
    existing = repo.get(user.id)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    if user.user_id and repo.get_by_user_id(user.user_id):
        raise HTTPException(status_code=400, detail="User ID already exists")
    if user.nickname and repo.get_by_nickname(user.nickname):
        raise HTTPException(status_code=400, detail="Nickname already exists")
    if user.email and repo.get_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user_data = user.model_dump()
    db_user = repo.create(user_data)
    
    return UserResponse(
        id=db_user.id,
        name=db_user.name,
        user_id=db_user.user_id,
        nickname=db_user.nickname,
        email=db_user.email,
        birth_date=db_user.birth_date,
        gender=db_user.gender,
        avatar_text=db_user.avatar_text,
        popcorn=db_user.popcorn,
        exp=db_user.exp,
        created_at=db_user.created_at
    )


@router.put("/me", response_model=UserResponse)
def update_user(
    user: UserUpdate,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db)
):
    """Update current user"""
    repo = UserRepository(db)
    current = repo.get(current_user.id)
    if not current:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user.model_dump(exclude_unset=True)
    if "nickname" in user_data and user_data["nickname"]:
        existing = repo.get_by_nickname(user_data["nickname"])
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Nickname already exists")
    if "email" in user_data and user_data["email"]:
        if user_data["email"] == current.email:
            raise HTTPException(status_code=400, detail="Email is the same as current")
        existing = repo.get_by_email(user_data["email"])
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already exists")
    db_user = repo.update(current_user.id, user_data)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=db_user.id,
        name=db_user.name,
        user_id=db_user.user_id,
        nickname=db_user.nickname,
        email=db_user.email,
        birth_date=db_user.birth_date,
        gender=db_user.gender,
        avatar_text=db_user.avatar_text,
        popcorn=db_user.popcorn,
        exp=db_user.exp,
        created_at=db_user.created_at
    )


@router.delete("/me", response_model=MessageResponse)
def delete_user(
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db)
):
    """Delete current user account"""
    repo = UserRepository(db)
    user = repo.get(current_user.id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo.delete(current_user.id)
    return MessageResponse(message="User deleted successfully")


@router.get("/me/reviews", response_model=ReviewListResponse)
def get_user_reviews(
    current_user=Depends(get_current_user_dep),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get current user's reviews"""
    repo = ReviewRepository(db)
    skip = (page - 1) * page_size
    
    user_id = current_user.id
    reviews = repo.get_by_user(user_id, skip=skip, limit=page_size)
    total = repo.count(filters={"user_id": user_id})
    
    review_responses = []
    for review in reviews:
        result = repo.get_with_counts(review.id)
        review_obj = result["review"]
        review_responses.append(
            ReviewResponse(
                id=review_obj.id,
                user_id=review_obj.user_id,
                user_nickname=review_obj.user.nickname if review_obj.user else None,
                movie_id=review_obj.movie_id,
                rating=review_obj.rating,
                content=review_obj.content,
                keywords=review_obj.keywords or [],
                is_public=review_obj.is_public,
                created_at=review_obj.created_at,
                likes_count=result["likes_count"],
                dislikes_count=result["dislikes_count"],
                comments_count=result["comments_count"]
            )
        )
    
    return ReviewListResponse(reviews=review_responses, total=total)


@router.get("/me/watched", response_model=WatchedMovieListResponse)
def get_watched_movies(
    current_user=Depends(get_current_user_dep),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get current user's watched movies"""
    repo = WatchedMovieRepository(db)
    skip = (page - 1) * page_size

    user_id = current_user.id
    items = repo.get_by_user(user_id, skip=skip, limit=page_size)
    total = repo.count_by_user(user_id)

    response_items = [
        WatchedMovieResponse(
            movie_id=item.movie_id,
            title=item.movie.title if item.movie else "",
            poster_url=item.movie.poster_url if item.movie else None,
            watched_at=item.watched_at,
        )
        for item in items
    ]

    return WatchedMovieListResponse(items=response_items, total=total)


@router.post("/me/watched", response_model=WatchedMovieResponse, status_code=201)
def add_watched_movie(
    payload: WatchedMovieCreate,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db)
):
    """Mark a movie as watched for current user"""
    movie_repo = MovieRepository(db)
    if not movie_repo.get(payload.movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")

    repo = WatchedMovieRepository(db)
    user_id = current_user.id
    existing = repo.get(user_id, payload.movie_id)
    if existing:
        movie = existing.movie
        return WatchedMovieResponse(
            movie_id=existing.movie_id,
            title=movie.title if movie else "",
            poster_url=movie.poster_url if movie else None,
            watched_at=existing.watched_at,
        )

    record = repo.create(user_id, payload.movie_id)
    db.refresh(record)
    movie = record.movie
    return WatchedMovieResponse(
        movie_id=record.movie_id,
        title=movie.title if movie else "",
        poster_url=movie.poster_url if movie else None,
        watched_at=record.watched_at,
    )


@router.delete("/me/watched/{movie_id}", response_model=MessageResponse)
def remove_watched_movie(
    movie_id: int,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db)
):
    """Unmark a movie as watched for current user"""
    repo = WatchedMovieRepository(db)
    deleted = repo.delete(current_user.id, movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watched record not found")

    return MessageResponse(message="Watched movie removed successfully")


@router.get("/me/taste-analysis", response_model=TasteAnalysisResponse)
def get_taste_analysis(
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db)
):
    """Get user's taste analysis"""
    repo = UserRepository(db)
    taste = repo.get_taste_analysis(current_user.id)
    
    if not taste:
        raise HTTPException(
            status_code=404,
            detail="Taste analysis not found. Please create reviews first."
        )
    
    return TasteAnalysisResponse(
        user_id=taste.user_id,
        summary_text=taste.summary_text,
        updated_at=taste.updated_at
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get user by ID"""
    repo = UserRepository(db)
    user = repo.get(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        name=user.name,
        user_id=user.user_id,
        nickname=user.nickname,
        email=user.email,
        birth_date=user.birth_date,
        gender=user.gender,
        avatar_text=user.avatar_text,
        popcorn=user.popcorn,
        exp=user.exp,
        created_at=user.created_at
    )
