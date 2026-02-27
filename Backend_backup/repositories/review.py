"""
Review repository with custom queries
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from models import Review, ReviewLike, Comment, CommentLike, User
from repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """Review repository with custom queries"""
    
    def __init__(self, db: Session):
        super().__init__(Review, db)
    
    def get_by_movie(
        self,
        movie_id: int,
        skip: int = 0,
        limit: int = 20,
        viewer_user_id: Optional[str] = None,
        include_private: bool = False
    ) -> List[Review]:
        """Get reviews for a movie with user info (public + viewer's private)"""
        query = (
            self.db.query(Review)
            .options(joinedload(Review.user))
            .filter(Review.movie_id == movie_id)
        )

        if not include_private:
            if viewer_user_id:
                query = query.filter(or_(Review.is_public == True, Review.user_id == viewer_user_id))
            else:
                query = query.filter(Review.is_public == True)

        return (
            query.order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> List[Review]:
        """Get reviews by a user with user info"""
        return (
            self.db.query(Review)
            .options(joinedload(Review.user))
            .filter(Review.user_id == user_id)
            .order_by(Review.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_with_user(self, review_id: int) -> Optional[Review]:
        """Get review with user info"""
        return (
            self.db.query(Review)
            .options(joinedload(Review.user))
            .filter(Review.id == review_id)
            .first()
        )
    
    def get_user_review_for_movie(self, user_id: str, movie_id: int) -> Optional[Review]:
        """Get user's review for a specific movie"""
        return (
            self.db.query(Review)
            .filter(Review.user_id == user_id, Review.movie_id == movie_id)
            .first()
        )
    
    def get_with_counts(self, review_id: int) -> Optional[dict]:
        """Get review with counts and user info"""
        review = self.get_with_user(review_id)
        if not review:
            return None

        comments_count = (
            self.db.query(func.count(Comment.id))
            .filter(Comment.review_id == review_id)
            .scalar()
        )
        
        return {
            "review": review,
            "likes_count": review.likes_count,
            "dislikes_count": review.dislikes_count,
            "comments_count": comments_count
        }

    def count_by_movie(
        self,
        movie_id: int,
        viewer_user_id: Optional[str] = None,
        include_private: bool = False,
    ) -> int:
        """Count reviews for a movie with visibility rules"""
        query = self.db.query(func.count(Review.id)).filter(Review.movie_id == movie_id)
        if not include_private:
            if viewer_user_id:
                query = query.filter(or_(Review.is_public == True, Review.user_id == viewer_user_id))
            else:
                query = query.filter(Review.is_public == True)
        return query.scalar()
    
    def toggle_like(self, review_id: int, user_id: str, is_like: bool = True) -> bool:
        """Toggle like/dislike on a review and update counters"""
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return False

        existing_like = (
            self.db.query(ReviewLike)
            .filter(ReviewLike.review_id == review_id, ReviewLike.user_id == user_id)
            .first()
        )

        if existing_like:
            if existing_like.is_like == is_like:
                # Remove reaction if same action
                self.db.delete(existing_like)
                if is_like:
                    review.likes_count = max(0, review.likes_count - 1)
                else:
                    review.dislikes_count = max(0, review.dislikes_count - 1)
            else:
                # Switch reaction
                if existing_like.is_like:
                    review.likes_count = max(0, review.likes_count - 1)
                    review.dislikes_count += 1
                else:
                    review.dislikes_count = max(0, review.dislikes_count - 1)
                    review.likes_count += 1
                existing_like.is_like = is_like
        else:
            # Create new reaction
            new_like = ReviewLike(review_id=review_id, user_id=user_id, is_like=is_like)
            self.db.add(new_like)
            if is_like:
                review.likes_count += 1
            else:
                review.dislikes_count += 1

        self.db.commit()
        return True

    def toggle_comment_like(self, comment_id: int, user_id: str, is_like: bool = True) -> bool:
        """Toggle like/dislike on a comment and update counters"""
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            return False

        existing_like = (
            self.db.query(CommentLike)
            .filter(CommentLike.comment_id == comment_id, CommentLike.user_id == user_id)
            .first()
        )

        if existing_like:
            if existing_like.is_like == is_like:
                self.db.delete(existing_like)
                if is_like:
                    comment.likes_count = max(0, comment.likes_count - 1)
                else:
                    comment.dislikes_count = max(0, comment.dislikes_count - 1)
            else:
                if existing_like.is_like:
                    comment.likes_count = max(0, comment.likes_count - 1)
                    comment.dislikes_count += 1
                else:
                    comment.dislikes_count = max(0, comment.dislikes_count - 1)
                    comment.likes_count += 1
                existing_like.is_like = is_like
        else:
            new_like = CommentLike(comment_id=comment_id, user_id=user_id, is_like=is_like)
            self.db.add(new_like)
            if is_like:
                comment.likes_count += 1
            else:
                comment.dislikes_count += 1

        self.db.commit()
        return True
    
    def add_comment(
        self,
        review_id: int,
        user_id: str,
        content: str,
        parent_comment_id: Optional[int] = None,
        is_public: bool = True,
    ) -> Comment:
        """Add comment to review (optionally as a reply)"""
        comment = Comment(
            review_id=review_id,
            user_id=user_id,
            content=content,
            parent_comment_id=parent_comment_id,
            is_public=is_public,
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def get_comment(self, comment_id: int) -> Optional[Comment]:
        """Get comment by ID"""
        return self.db.query(Comment).filter(Comment.id == comment_id).first()

    def update_comment(
        self,
        comment_id: int,
        content: Optional[str],
        is_public: Optional[bool] = None
    ) -> Optional[Comment]:
        """Update comment content"""
        comment = self.get_comment(comment_id)
        if not comment:
            return None

        if content is not None:
            comment.content = content
        if is_public is not None:
            comment.is_public = is_public

        self.db.commit()
        self.db.refresh(comment)
        return comment

    def delete_comment(self, comment_id: int) -> bool:
        """Delete comment by ID"""
        comment = self.get_comment(comment_id)
        if not comment:
            return False

        self.db.delete(comment)
        self.db.commit()
        return True
    
    def get_comments(
        self,
        review_id: int,
        skip: int = 0,
        limit: int = 50,
        viewer_user_id: Optional[str] = None,
        review_owner_id: Optional[str] = None,
    ) -> List[Comment]:
        """Get comments for a review with visibility rules"""
        query = (
            self.db.query(Comment)
            .options(joinedload(Comment.user))
            .filter(Comment.review_id == review_id)
        )

        if viewer_user_id and review_owner_id and viewer_user_id == review_owner_id:
            pass
        elif viewer_user_id:
            query = query.filter(
                or_(Comment.is_public == True, Comment.user_id == viewer_user_id)
            )
        else:
            query = query.filter(Comment.is_public == True)

        return (
            query.order_by(Comment.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
