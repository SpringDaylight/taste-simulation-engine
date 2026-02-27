"""
TMDB Review repository for ML training data
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import TMDBReview
from repositories.base import BaseRepository


class TMDBReviewRepository(BaseRepository[TMDBReview]):
    """TMDB Review repository for ML training data"""
    
    def __init__(self, db: Session):
        super().__init__(TMDBReview, db)
    
    def get_by_movie(self, movie_id: int, skip: int = 0, limit: int = 100) -> List[TMDBReview]:
        """Get TMDB reviews for a movie"""
        return (
            self.db.query(TMDBReview)
            .filter(TMDBReview.movie_id == movie_id)
            .order_by(TMDBReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_all_for_ml(self, skip: int = 0, limit: int = 10000) -> List[TMDBReview]:
        """Get all TMDB reviews for ML training"""
        return (
            self.db.query(TMDBReview)
            .order_by(TMDBReview.movie_id, TMDBReview.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_by_movie(self, movie_id: int) -> int:
        """Count TMDB reviews for a movie"""
        return (
            self.db.query(func.count(TMDBReview.id))
            .filter(TMDBReview.movie_id == movie_id)
            .scalar()
        )
