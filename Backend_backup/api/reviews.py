"""
Review API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import get_db
from api.deps import get_current_user, get_current_user_optional
from schemas import (
    ReviewResponse, ReviewListResponse, ReviewCreate, ReviewUpdate,
    CommentResponse, CommentCreate, CommentUpdate, MessageResponse, LikeToggleResponse,
    CommentLikeToggleResponse
)
from repositories.review import ReviewRepository
from repositories.movie import MovieRepository
from repositories.watched import WatchedMovieRepository

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: int,
    current_user=Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get review by ID with counts"""
    repo = ReviewRepository(db)
    result = repo.get_with_counts(review_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review = result["review"]
    viewer_user_id = current_user.id if current_user else None
    if not review.is_public and review.user_id != viewer_user_id:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        user_nickname=review.user.nickname if review.user else None,
        movie_id=review.movie_id,
        rating=review.rating,
        content=review.content,
        keywords=review.keywords or [],
        is_public=review.is_public,
        created_at=review.created_at,
        likes_count=result["likes_count"],
        dislikes_count=result["dislikes_count"],
        comments_count=result["comments_count"]
    )


@router.post("", response_model=ReviewResponse, status_code=201)
def create_review(
    review: ReviewCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new review"""
    from repositories.user_preference import UserPreferenceRepository
    from domain.a1_preference import analyze_preference
    
    repo = ReviewRepository(db)
    user_id = current_user.id
    
    # Check if user already reviewed this movie
    existing = repo.get_user_review_for_movie(user_id, review.movie_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already reviewed this movie. Use PUT to update."
        )
    
    review_data = review.model_dump()
    review_data["user_id"] = user_id
    
    db_review = repo.create(review_data)
    MovieRepository(db).recalc_avg_rating(db_review.movie_id)
    # Ensure watched_movies has this movie for the user
    watched_repo = WatchedMovieRepository(db)
    if not watched_repo.get(user_id, db_review.movie_id):
        watched_repo.create(user_id, db_review.movie_id)
    
    # 사용자 선호도 업데이트 (리뷰 기반)
    try:
        # 사용자의 모든 리뷰 가져오기
        user_reviews = repo.get_by_user(user_id, skip=0, limit=100)
        
        # 리뷰 내용을 기반으로 선호도 분석
        review_texts = []
        for r in user_reviews:
            if r.content:
                review_texts.append(r.content)
        
        if review_texts:
            combined_text = " ".join(review_texts[-10:])  # 최근 10개 리뷰만 사용
            
            # A-1 API로 선호도 분석
            user_profile = analyze_preference({
                "text": combined_text,
                "dislikes": ""
            })
            
            # UserPreference 테이블에 저장
            pref_repo = UserPreferenceRepository(db)
            preference_vector_json = {
                "emotion_scores": user_profile["emotion_scores"],
                "narrative_traits": user_profile["narrative_traits"],
                "direction_mood": user_profile["direction_mood"],
                "character_relationship": user_profile["character_relationship"],
                "ending_preference": user_profile["ending_preference"]
            }
            
            pref_repo.upsert(
                user_id=user_id,
                preference_vector_json=preference_vector_json,
                boost_tags=user_profile.get("boost_tags", []),
                dislike_tags=user_profile.get("dislike_tags", []),
                penalty_tags=[]
            )
    except Exception as e:
        # 선호도 업데이트 실패는 치명적이지 않으므로 로그만 남김
        print(f"Failed to update user preference: {e}")
    
    # Refresh to get user relationship
    db.refresh(db_review)
    
    return ReviewResponse(
        id=db_review.id,
        user_id=db_review.user_id,
        user_nickname=db_review.user.nickname if db_review.user else None,
        movie_id=db_review.movie_id,
        rating=db_review.rating,
        content=db_review.content,
        keywords=db_review.keywords or [],
        is_public=db_review.is_public,
        created_at=db_review.created_at,
        likes_count=0,
        dislikes_count=0,
        comments_count=0
    )


@router.put("/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    review: ReviewUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a review"""
    from repositories.user_preference import UserPreferenceRepository
    from domain.a1_preference import analyze_preference
    
    repo = ReviewRepository(db)
    review_data = review.model_dump(exclude_unset=True)
    
    # exclude_unset=True removes 'content' if it's explicitly set to None (in some Pydantic versions)
    # or keeps it. Let's ensure if 'content' is explicitly in the incoming payload as None, we update it.
    if "content" in review.model_fields_set:
        review_data["content"] = review.content

    db_review = repo.update(review_id, review_data)
    
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    MovieRepository(db).recalc_avg_rating(db_review.movie_id)
    
    # 사용자 선호도 업데이트 (리뷰 기반)
    try:
        user_id = db_review.user_id
        user_reviews = repo.get_by_user(user_id, skip=0, limit=100)
        
        review_texts = []
        for r in user_reviews:
            if r.content:
                review_texts.append(r.content)
        
        if review_texts:
            combined_text = " ".join(review_texts[-10:])
            
            user_profile = analyze_preference({
                "text": combined_text,
                "dislikes": ""
            })
            
            pref_repo = UserPreferenceRepository(db)
            preference_vector_json = {
                "emotion_scores": user_profile["emotion_scores"],
                "narrative_traits": user_profile["narrative_traits"],
                "direction_mood": user_profile["direction_mood"],
                "character_relationship": user_profile["character_relationship"],
                "ending_preference": user_profile["ending_preference"]
            }
            
            pref_repo.upsert(
                user_id=user_id,
                preference_vector_json=preference_vector_json,
                boost_tags=user_profile.get("boost_tags", []),
                dislike_tags=user_profile.get("dislike_tags", []),
                penalty_tags=[]
            )
    except Exception as e:
        print(f"Failed to update user preference: {e}")
    
    result = repo.get_with_counts(review_id)
    
    review_obj = result["review"]
    return ReviewResponse(
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


@router.delete("/{review_id}", response_model=MessageResponse)
def delete_review(
    review_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a review"""
    repo = ReviewRepository(db)
    
    review = repo.get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this review")

    repo.delete(review_id)
    MovieRepository(db).recalc_avg_rating(review.movie_id)
    
    return MessageResponse(message="Review deleted successfully")


@router.post("/{review_id}/likes", response_model=LikeToggleResponse)
def toggle_like(
    review_id: int,
    current_user=Depends(get_current_user),
    is_like: bool = Query(True, description="True for like, False for dislike"),
    db: Session = Depends(get_db)
):
    """Toggle like/dislike on a review"""
    repo = ReviewRepository(db)
    
    review = repo.get(review_id)
    user_id = current_user.id
    if not review or (not review.is_public and review.user_id != user_id):
        raise HTTPException(status_code=404, detail="Review not found")

    if not repo.toggle_like(review_id, user_id, is_like):
        raise HTTPException(status_code=404, detail="Review not found")
    
    action = "liked" if is_like else "disliked"
    updated = repo.get_with_counts(review_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found")

    return LikeToggleResponse(
        message=f"Review {action} successfully",
        review_id=review_id,
        likes_count=updated["likes_count"],
        dislikes_count=updated["dislikes_count"],
    )


@router.get("/{review_id}/comments", response_model=List[CommentResponse])
def get_comments(
    review_id: int,
    current_user=Depends(get_current_user_optional),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get comments for a review"""
    repo = ReviewRepository(db)
    
    viewer_user_id = current_user.id if current_user else None
    review = repo.get(review_id)
    if not review or (not review.is_public and review.user_id != viewer_user_id):
        raise HTTPException(status_code=404, detail="Review not found")
    
    comments = repo.get_comments(
        review_id,
        skip=skip,
        limit=limit,
        viewer_user_id=viewer_user_id,
        review_owner_id=review.user_id,
    )
    
    return [
        CommentResponse(
            id=comment.id,
            review_id=comment.review_id,
            parent_comment_id=comment.parent_comment_id,
            user_id=comment.user_id,
            user_nickname=comment.user.nickname if comment.user else None,
            content=comment.content,
            created_at=comment.created_at,
            likes_count=comment.likes_count,
            dislikes_count=comment.dislikes_count
        )
        for comment in comments
    ]


@router.post("/{review_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    review_id: int,
    comment: CommentCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a review"""
    repo = ReviewRepository(db)
    
    user_id = current_user.id
    review = repo.get(review_id)
    if not review or (not review.is_public and review.user_id != user_id):
        raise HTTPException(status_code=404, detail="Review not found")

    if comment.parent_comment_id is not None:
        parent = repo.get_comment(comment.parent_comment_id)
        if not parent or parent.review_id != review_id:
            raise HTTPException(status_code=400, detail="Invalid parent comment")
    
    db_comment = repo.add_comment(
        review_id,
        user_id,
        comment.content,
        parent_comment_id=comment.parent_comment_id,
        is_public=comment.is_public,
    )
    
    # Refresh to get user relationship
    db.refresh(db_comment)
    
    return CommentResponse(
        id=db_comment.id,
        review_id=db_comment.review_id,
        parent_comment_id=db_comment.parent_comment_id,
        user_id=db_comment.user_id,
        user_nickname=db_comment.user.nickname if db_comment.user else None,
        content=db_comment.content,
        created_at=db_comment.created_at,
        likes_count=db_comment.likes_count,
        dislikes_count=db_comment.dislikes_count
    )


@router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update comment content"""
    repo = ReviewRepository(db)
    existing = repo.get_comment(comment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    user_id = current_user.id
    if existing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this comment")

    db_comment = repo.update_comment(comment_id, payload.content, payload.is_public)

    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Refresh to get user relationship
    db.refresh(db_comment)

    return CommentResponse(
        id=db_comment.id,
        review_id=db_comment.review_id,
        parent_comment_id=db_comment.parent_comment_id,
        user_id=db_comment.user_id,
        user_nickname=db_comment.user.nickname if db_comment.user else None,
        content=db_comment.content,
        created_at=db_comment.created_at,
        likes_count=db_comment.likes_count,
        dislikes_count=db_comment.dislikes_count
    )


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
def delete_comment(
    comment_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a comment"""
    repo = ReviewRepository(db)
    existing = repo.get_comment(comment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    user_id = current_user.id
    if existing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

    deleted = repo.delete_comment(comment_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")

    return MessageResponse(message="Comment deleted successfully")


@router.post("/comments/{comment_id}/likes", response_model=CommentLikeToggleResponse)
def toggle_comment_like(
    comment_id: int,
    current_user=Depends(get_current_user),
    is_like: bool = Query(True, description="True for like, False for dislike"),
    db: Session = Depends(get_db)
):
    """Toggle like/dislike on a comment"""
    repo = ReviewRepository(db)

    comment = repo.get_comment(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    review = repo.get(comment.review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    user_id = current_user.id
    if not review.is_public and review.user_id != user_id:
        raise HTTPException(status_code=404, detail="Review not found")

    if not comment.is_public and comment.user_id != user_id and review.user_id != user_id:
        raise HTTPException(status_code=404, detail="Comment not found")

    if not repo.toggle_comment_like(comment_id, user_id, is_like):
        raise HTTPException(status_code=404, detail="Comment not found")

    action = "liked" if is_like else "disliked"
    updated = repo.get_comment(comment_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Comment not found")

    return CommentLikeToggleResponse(
        message=f"Comment {action} successfully",
        comment_id=comment_id,
        likes_count=updated.likes_count,
        dislikes_count=updated.dislikes_count,
    )
