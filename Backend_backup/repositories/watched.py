"""
Watched movies repository
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models import WatchedMovie, Movie


class WatchedMovieRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: str, skip: int = 0, limit: int = 20) -> List[WatchedMovie]:
        return (
            self.db.query(WatchedMovie)
            .options(joinedload(WatchedMovie.movie))
            .filter(WatchedMovie.user_id == user_id)
            .order_by(WatchedMovie.watched_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_user(self, user_id: str) -> int:
        return (
            self.db.query(func.count(WatchedMovie.id))
            .filter(WatchedMovie.user_id == user_id)
            .scalar()
        )

    def get(self, user_id: str, movie_id: int) -> Optional[WatchedMovie]:
        return (
            self.db.query(WatchedMovie)
            .filter(WatchedMovie.user_id == user_id, WatchedMovie.movie_id == movie_id)
            .first()
        )

    def create(self, user_id: str, movie_id: int) -> WatchedMovie:
        from utils.cache import cache_delete
        
        record = WatchedMovie(user_id=user_id, movie_id=movie_id)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        # 캐시 무효화
        cache_delete(f"watched_ids:{user_id}")
        
        return record

    def get_watched_movie_ids(self, user_id: str) -> List[int]:
        """
        Get list of movie IDs that user has watched (with caching)
        
        캐시 TTL: 5분 (watched 상태는 자주 변경되지 않음)
        """
        from utils.cache import cache_get, cache_set
        
        cache_key = f"watched_ids:{user_id}"
        
        # 캐시 확인
        cached_ids = cache_get(cache_key)
        if cached_ids is not None:
            return cached_ids
        
        # DB 조회
        results = (
            self.db.query(WatchedMovie.movie_id)
            .filter(WatchedMovie.user_id == user_id)
            .all()
        )
        movie_ids = [row[0] for row in results]
        
        # 캐시 저장 (TTL 5분)
        cache_set(cache_key, movie_ids, ttl=300)
        
        return movie_ids

    def delete(self, user_id: str, movie_id: int) -> bool:
        from utils.cache import cache_delete
        
        record = self.get(user_id, movie_id)
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        
        # 캐시 무효화
        cache_delete(f"watched_ids:{user_id}")
        
        return True
