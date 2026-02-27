"""
Movie repository with custom queries
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, collate

from models import Movie, MovieGenre, MovieTag, Review
from repositories.base import BaseRepository


class MovieRepository(BaseRepository[Movie]):
    """Movie repository with custom queries"""
    
    def __init__(self, db: Session):
        super().__init__(Movie, db)
    
    def get_with_details(self, movie_id: int) -> Optional[Movie]:
        """Get movie with genres and tags"""
        return (
            self.db.query(Movie)
            .options(joinedload(Movie.genres), joinedload(Movie.tags))
            .filter(Movie.id == movie_id)
            .first()
        )
    
    def search(
        self,
        query: Optional[str] = None,
        genres: Optional[List[str]] = None,
        category: Optional[str] = None,
        sort: str = "latest",
        runtime_ranges: Optional[List[tuple[Optional[int], Optional[int]]]] = None,
        year_ranges: Optional[List[tuple[Optional[int], Optional[int]]]] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[tuple[Movie, int]]:
        """Search movies by title, genres, category with sorting"""
        db_query = self.db.query(
            Movie,
            func.count(func.distinct(Review.id)).label("reviews_count")
        ).options(
            joinedload(Movie.genres),
            joinedload(Movie.tags)
        ).outerjoin(Review)
        
        # Text search
        if query:
            db_query = db_query.filter(Movie.title.ilike(f"%{query}%"))
        
        # Genre filter
        if genres:
            db_query = db_query.join(MovieGenre).filter(
                MovieGenre.genre.in_(genres)
            ).distinct()
        
        # Category filter (can be used for tags or other categorization)
        if category:
            db_query = db_query.join(MovieTag).filter(
                MovieTag.tag.ilike(f"%{category}%")
            ).distinct()

        # Runtime filter (OR across ranges)
        if runtime_ranges:
            runtime_conditions = []
            for min_val, max_val in runtime_ranges:
                conds = []
                if min_val is not None:
                    conds.append(Movie.runtime >= min_val)
                if max_val is not None:
                    conds.append(Movie.runtime <= max_val)
                if conds:
                    runtime_conditions.append(and_(*conds))
            if runtime_conditions:
                db_query = db_query.filter(or_(*runtime_conditions))

        # Release year filter (OR across ranges)
        if year_ranges:
            year_conditions = []
            for min_val, max_val in year_ranges:
                conds = []
                if min_val is not None:
                    conds.append(func.extract("year", Movie.release) >= min_val)
                if max_val is not None:
                    conds.append(func.extract("year", Movie.release) <= max_val)
                if conds:
                    year_conditions.append(and_(*conds))
            if year_conditions:
                db_query = db_query.filter(or_(*year_conditions))
        
        # Sorting
        db_query = db_query.group_by(Movie.id)
        if sort == "popular":
            # Sort by review count
            db_query = db_query.order_by(func.count(func.distinct(Review.id)).desc())
        elif sort == "rating":
            # Sort by average rating
            db_query = db_query.order_by(func.coalesce(func.avg(Review.rating), 0).desc())
        elif sort == "title":
            # Sort by title (Korean collation)
            db_query = db_query.order_by(collate(Movie.title, "ko_KR.utf8").asc().nullslast())
        else:  # latest (default)
            db_query = db_query.order_by(Movie.release.desc().nullslast())
        
        return db_query.offset(skip).limit(limit).all()
    
    def count_search(
        self,
        query: Optional[str] = None,
        genres: Optional[List[str]] = None,
        category: Optional[str] = None,
        runtime_ranges: Optional[List[tuple[Optional[int], Optional[int]]]] = None,
        year_ranges: Optional[List[tuple[Optional[int], Optional[int]]]] = None,
    ) -> int:
        """Count movies matching search criteria"""
        db_query = self.db.query(Movie)
        
        # Text search
        if query:
            db_query = db_query.filter(Movie.title.ilike(f"%{query}%"))
        
        # Genre filter
        if genres:
            db_query = db_query.join(MovieGenre).filter(
                MovieGenre.genre.in_(genres)
            ).distinct()
        
        # Category filter
        if category:
            db_query = db_query.join(MovieTag).filter(
                MovieTag.tag.ilike(f"%{category}%")
            ).distinct()

        # Runtime filter (OR across ranges)
        if runtime_ranges:
            runtime_conditions = []
            for min_val, max_val in runtime_ranges:
                conds = []
                if min_val is not None:
                    conds.append(Movie.runtime >= min_val)
                if max_val is not None:
                    conds.append(Movie.runtime <= max_val)
                if conds:
                    runtime_conditions.append(and_(*conds))
            if runtime_conditions:
                db_query = db_query.filter(or_(*runtime_conditions))

        # Release year filter (OR across ranges)
        if year_ranges:
            year_conditions = []
            for min_val, max_val in year_ranges:
                conds = []
                if min_val is not None:
                    conds.append(func.extract("year", Movie.release) >= min_val)
                if max_val is not None:
                    conds.append(func.extract("year", Movie.release) <= max_val)
                if conds:
                    year_conditions.append(and_(*conds))
            if year_conditions:
                db_query = db_query.filter(or_(*year_conditions))
        
        return db_query.count()
    
    def get_by_genre(self, genre: str, limit: int = 20) -> List[Movie]:
        """Get movies by genre"""
        return (
            self.db.query(Movie)
            .join(MovieGenre)
            .filter(MovieGenre.genre == genre)
            .options(joinedload(Movie.genres), joinedload(Movie.tags))
            .limit(limit)
            .all()
        )
    
    def get_popular(self, limit: int = 20) -> List[Movie]:
        """Get popular movies (by review count)"""
        return (
            self.db.query(Movie)
            .outerjoin(Review)
            .group_by(Movie.id)
            .order_by(func.count(Review.id).desc())
            .options(joinedload(Movie.genres), joinedload(Movie.tags))
            .limit(limit)
            .all()
        )

    def recalc_avg_rating(self, movie_id: int) -> Optional[float]:
        """Recalculate and persist avg_rating for a movie (rounded to 0.5 steps)"""
        avg_rating = (
            self.db.query((func.round(func.avg(Review.rating) * 2) / 2))
            .filter(Review.movie_id == movie_id)
            .scalar()
        )

        movie = self.get(movie_id)
        if not movie:
            return None

        movie.avg_rating = avg_rating
        self.db.commit()
        self.db.refresh(movie)
        return movie.avg_rating
    
    def add_genre(self, movie_id: int, genre: str) -> bool:
        """Add genre to movie"""
        movie_genre = MovieGenre(movie_id=movie_id, genre=genre)
        self.db.add(movie_genre)
        self.db.commit()
        return True
    
    def add_tag(self, movie_id: int, tag: str) -> bool:
        """Add tag to movie"""
        movie_tag = MovieTag(movie_id=movie_id, tag=tag)
        self.db.add(movie_tag)
        self.db.commit()
        return True
