"""
Movie API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import get_db
from api.deps import get_current_user_optional
from schemas import (
    MovieResponse, MovieListResponse, MovieCreate, MovieUpdate, MessageResponse,
    ReviewResponse, ReviewListResponse
)
from repositories.movie import MovieRepository
from repositories.review import ReviewRepository

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("", response_model=MovieListResponse)
def get_movies(
    query: Optional[str] = Query(None, description="Search query"),
    genres: Optional[str] = Query(None, description="Filter by genres (comma-separated)"),
    category: Optional[str] = Query(None, description="Category filter"),
    sort: Optional[str] = Query("latest", description="Sort by: latest, popular, rating"),
    runtime_min: Optional[int] = Query(None, ge=0, description="Minimum runtime (minutes)"),
    runtime_max: Optional[int] = Query(None, ge=0, description="Maximum runtime (minutes)"),
    year_min: Optional[int] = Query(None, ge=0, description="Minimum release year"),
    year_max: Optional[int] = Query(None, ge=0, description="Maximum release year"),
    runtime_ranges: Optional[str] = Query(
        None,
        description="Runtime ranges (comma-separated keys: under-100, between-100-120, between-120-140, over-140)",
    ),
    year_ranges: Optional[str] = Query(
        None,
        description="Year ranges (comma-separated keys: pre1950, 1950s, 1960s, 1970s, 1980s, 1990s, 2000s, 2010s, 2020plus)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get movies with optional search and filters
    
    - **query**: Search in title and synopsis
    - **genres**: Filter by genres (comma-separated, e.g., "액션,드라마")
    - **category**: Category filter (optional)
    - **sort**: Sort order (latest, popular, rating)
    - **runtime_min/runtime_max**: Runtime filter (minutes)
    - **year_min/year_max**: Release year filter
    - **runtime_ranges/year_ranges**: OR-based multi-range filters (comma-separated keys)
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page
    """
    if runtime_min is not None and runtime_max is not None and runtime_min > runtime_max:
        raise HTTPException(status_code=400, detail="runtime_min cannot be greater than runtime_max")
    if year_min is not None and year_max is not None and year_min > year_max:
        raise HTTPException(status_code=400, detail="year_min cannot be greater than year_max")

    runtime_range_map = {
        "under-100": (None, 100),
        "between-100-120": (100, 120),
        "between-120-140": (120, 140),
        "over-140": (140, None),
    }
    year_range_map = {
        "pre1950": (None, 1949),
        "1950s": (1950, 1959),
        "1960s": (1960, 1969),
        "1970s": (1970, 1979),
        "1980s": (1980, 1989),
        "1990s": (1990, 1999),
        "2000s": (2000, 2009),
        "2010s": (2010, 2019),
        "2020plus": (2020, None),
    }

    runtime_range_list = []
    if runtime_ranges:
        for key in [v.strip() for v in runtime_ranges.split(",") if v.strip()]:
            if key in runtime_range_map:
                runtime_range_list.append(runtime_range_map[key])
    if runtime_min is not None or runtime_max is not None:
        runtime_range_list.append((runtime_min, runtime_max))

    year_range_list = []
    if year_ranges:
        for key in [v.strip() for v in year_ranges.split(",") if v.strip()]:
            if key in year_range_map:
                year_range_list.append(year_range_map[key])
    if year_min is not None or year_max is not None:
        year_range_list.append((year_min, year_max))

    repo = MovieRepository(db)
    skip = (page - 1) * page_size
    
    # Parse genres from comma-separated string
    genre_list = [g.strip() for g in genres.split(",")] if genres else None
    
    movies = repo.search(
        query=query,
        genres=genre_list,
        category=category,
        sort=sort,
        runtime_ranges=runtime_range_list or None,
        year_ranges=year_range_list or None,
        skip=skip,
        limit=page_size
    )
    total = repo.count_search(
        query=query,
        genres=genre_list,
        category=category,
        runtime_ranges=runtime_range_list or None,
        year_ranges=year_range_list or None,
    )
    
    # Convert to response format
    movie_responses = []
    for movie, reviews_count in movies:
        # 한국어 keywords 사용
        if movie.keywords and isinstance(movie.keywords, list):
            tags = movie.keywords[:8]
        else:
            tags = [t.tag for t in movie.tags][:8]

        movie_dict = {
            "id": movie.id,
            "title": movie.title,
            "release": movie.release,
            "runtime": movie.runtime,
            "synopsis": movie.synopsis,
            "poster_url": movie.poster_url,
            "avg_rating": movie.avg_rating,
            "created_at": movie.created_at,
            "genres": [g.genre for g in movie.genres],
            "tags": tags,
            "reviews_count": reviews_count
        }
        movie_responses.append(MovieResponse(**movie_dict))

    return MovieListResponse(
        movies=movie_responses,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    """Get movie by ID with genres and tags"""
    repo = MovieRepository(db)
    movie = repo.get_with_details(movie_id)
    
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    # 한국어 keywords 사용 (JSONB 컬럼)
    if movie.keywords and isinstance(movie.keywords, list):
        tags = movie.keywords[:10]  # 최대 10개
    else:
        # fallback: TMDB 영어 태그
        tags = [t.tag for t in movie.tags][:10]
    
    return MovieResponse(
        id=movie.id,
        title=movie.title,
        release=movie.release,
        runtime=movie.runtime,
        synopsis=movie.synopsis,
        poster_url=movie.poster_url,
        avg_rating=movie.avg_rating,
        created_at=movie.created_at,
        genres=[g.genre for g in movie.genres],
        tags=tags
    )


@router.get("/{movie_id}/reviews", response_model=ReviewListResponse)
def get_movie_reviews(
    movie_id: int,
    current_user=Depends(get_current_user_optional),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get reviews for a specific movie"""
    # Check if movie exists
    movie_repo = MovieRepository(db)
    if not movie_repo.get(movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")
    
    review_repo = ReviewRepository(db)
    skip = (page - 1) * page_size
    
    viewer_user_id = current_user.id if current_user else None
    reviews = review_repo.get_by_movie(
        movie_id,
        skip=skip,
        limit=page_size,
        viewer_user_id=viewer_user_id,
        include_private=True,
    )
    total = review_repo.count_by_movie(
        movie_id,
        viewer_user_id=viewer_user_id,
        include_private=True,
    )
    
    review_responses = []
    for review in reviews:
        result = review_repo.get_with_counts(review.id)
        review_obj = result["review"]
        is_owner = viewer_user_id and review_obj.user_id == viewer_user_id
        content = review_obj.content if (review_obj.is_public or is_owner) else None
        review_responses.append(
            ReviewResponse(
                id=review_obj.id,
                user_id=review_obj.user_id,
                user_nickname=review_obj.user.nickname if review_obj.user else None,
                movie_id=review_obj.movie_id,
                rating=review_obj.rating,
                content=content,
                keywords=review_obj.keywords or [],
                is_public=review_obj.is_public,
                created_at=review_obj.created_at,
                likes_count=result["likes_count"],
                dislikes_count=result["dislikes_count"],
                comments_count=result["comments_count"]
            )
        )
    
    return ReviewListResponse(reviews=review_responses, total=total)



@router.post("", response_model=MovieResponse, status_code=201)
def create_movie(movie: MovieCreate, db: Session = Depends(get_db)):
    """Create a new movie"""
    repo = MovieRepository(db)
    
    movie_data = movie.model_dump()
    db_movie = repo.create(movie_data)
    
    return MovieResponse(
        id=db_movie.id,
        title=db_movie.title,
        release=db_movie.release,
        runtime=db_movie.runtime,
        synopsis=db_movie.synopsis,
        poster_url=db_movie.poster_url,
        avg_rating=db_movie.avg_rating,
        created_at=db_movie.created_at,
        genres=[],
        tags=[]
    )


@router.put("/{movie_id}", response_model=MovieResponse)
def update_movie(movie_id: int, movie: MovieUpdate, db: Session = Depends(get_db)):
    """Update a movie"""
    repo = MovieRepository(db)
    
    movie_data = movie.model_dump(exclude_unset=True)
    db_movie = repo.update(movie_id, movie_data)
    
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    return MovieResponse(
        id=db_movie.id,
        title=db_movie.title,
        release=db_movie.release,
        runtime=db_movie.runtime,
        synopsis=db_movie.synopsis,
        poster_url=db_movie.poster_url,
        avg_rating=db_movie.avg_rating,
        created_at=db_movie.created_at,
        genres=[g.genre for g in db_movie.genres],
        tags=[t.tag for t in db_movie.tags]
    )


@router.delete("/{movie_id}", response_model=MessageResponse)
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    """Delete a movie"""
    repo = MovieRepository(db)
    
    if not repo.delete(movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")
    
    return MessageResponse(message="Movie deleted successfully")


@router.get("/genre/{genre}", response_model=List[MovieResponse])
def get_movies_by_genre(
    genre: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get movies by genre"""
    repo = MovieRepository(db)
    movies = repo.get_by_genre(genre, limit=limit)
    
    return [
        MovieResponse(
            id=movie.id,
            title=movie.title,
            release=movie.release,
            runtime=movie.runtime,
            synopsis=movie.synopsis,
            poster_url=movie.poster_url,
            avg_rating=movie.avg_rating,
            created_at=movie.created_at,
            genres=[g.genre for g in movie.genres],
            tags=[t.tag for t in movie.tags]
        )
        for movie in movies
    ]


@router.get("/popular/list", response_model=List[MovieResponse])
def get_popular_movies(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get popular movies (by review count)"""
    repo = MovieRepository(db)
    movies = repo.get_popular(limit=limit)
    
    return [
        MovieResponse(
            id=movie.id,
            title=movie.title,
            release=movie.release,
            runtime=movie.runtime,
            synopsis=movie.synopsis,
            poster_url=movie.poster_url,
            avg_rating=movie.avg_rating,
            created_at=movie.created_at,
            genres=[g.genre for g in movie.genres],
            tags=[t.tag for t in movie.tags]
        )
        for movie in movies
    ]
