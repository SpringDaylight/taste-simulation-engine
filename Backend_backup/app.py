"""
Main FastAPI application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api import movies, reviews, users, auth, gamification, cocktail, user_preferences, questions, roulette, group_recommend
from llm_lab.api import router as llm_lab_router
from llm_lab.api_recommend import router as llm_recommend_router
from llm_lab.api_personalized import router as personalized_router
from utils.validator import validate_request

from domain.a1_preference import analyze_preference
from domain.a2_movie_vector import process_movie_vector
from domain.a3_prediction import predict_satisfaction
from domain.a4_explanation import explain_prediction
from domain.a5_emotional_search import emotional_search
from domain.a6_group_simulation import simulate_group
from domain.a7_taste_map import build_taste_map

# Create FastAPI app
app = FastAPI(
    title="Movie Recommendation API",
    description="정서·서사 기반 영화 취향 시뮬레이션 & 감성 검색 서비스",
    version="1.2.0"
)


@app.on_event("startup")
def run_startup_migrations():
    """앱 시작 시 누락된 DB 컬럼을 자동으로 추가합니다."""
    from db import SessionLocal
    db = SessionLocal()
    try:
        db.execute(__import__('sqlalchemy').text(
            "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS keywords JSONB DEFAULT '[]'::jsonb"
        ))
        db.commit()
    except Exception as e:
        print(f"[startup migration] warning: {e}")
    finally:
        db.close()


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # 로컬 개발
        "http://localhost:3000",  # 로컬 개발 (대체 포트)
        "http://bolrae-malrae-frontend.s3-website.ap-northeast-2.amazonaws.com",  # S3 프로덕션
        "https://bolreamalrea.com",  # 프로덕션 도메인
        # 추가 도메인이 있으면 여기에 추가
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(movies.router)
app.include_router(reviews.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(gamification.router)
app.include_router(cocktail.router)
app.include_router(user_preferences.router)
app.include_router(questions.router)
app.include_router(roulette.router)
app.include_router(group_recommend.router)
app.include_router(llm_lab_router)
app.include_router(llm_recommend_router)
app.include_router(personalized_router)


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Movie Recommendation API is running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Health check for load balancer"""
    return {"status": "healthy"}


@app.post("/analyze/preference")
def analyze_preference_endpoint(body: dict) -> dict:
    """
    Analyze user preference from text input and optionally save to database
    
    Request body:
        - text: User input text (required)
        - dislikes: Comma-separated dislike tags (optional)
        - user_id: User ID to save preference (optional)
        - save_to_db: Whether to save to database (default: False)
    """
    from db import SessionLocal
    from repositories.user_preference import UserPreferenceRepository
    
    try:
        body = validate_request("a1_preference_request.json", body)
        result = analyze_preference(body)
        
        # Save to database if user_id is provided and save_to_db is True
        user_id = body.get("user_id")
        save_to_db = body.get("save_to_db", False)
        
        if user_id and save_to_db:
            db = SessionLocal()
            try:
                repo = UserPreferenceRepository(db)
                
                # Prepare preference vector JSON
                preference_vector_json = {
                    "emotion_scores": result["emotion_scores"],
                    "narrative_traits": result["narrative_traits"],
                    "direction_mood": result["direction_mood"],
                    "character_relationship": result["character_relationship"],
                    "ending_preference": result["ending_preference"]
                }
                
                # Save to database
                saved_preference = repo.upsert(
                    user_id=user_id,
                    preference_vector_json=preference_vector_json,
                    boost_tags=result.get("boost_tags", []),
                    dislike_tags=result.get("dislike_tags", []),
                    penalty_tags=[]  # Can be added later if needed
                )
                
                result["saved"] = True
                result["preference_id"] = saved_preference.id
            finally:
                db.close()
        else:
            result["saved"] = False
        
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/users/{user_id}/preference")
def get_user_preference_endpoint(user_id: str) -> dict:
    """
    Get saved user preference by user_id
    
    Returns:
        User preference data including vectors and tags
    """
    from db import SessionLocal
    from repositories.user_preference import UserPreferenceRepository
    
    db = SessionLocal()
    try:
        repo = UserPreferenceRepository(db)
        preference = repo.get_by_user_id(user_id)
        
        if not preference:
            raise HTTPException(status_code=404, detail=f"Preference not found for user_id: {user_id}")
        
        return {
            "user_id": preference.user_id,
            "preference_vector": preference.preference_vector_json,
            "persona_code": preference.persona_code,
            "boost_tags": preference.boost_tags,
            "dislike_tags": preference.dislike_tags,
            "penalty_tags": preference.penalty_tags,
            "updated_at": preference.updated_at.isoformat() if preference.updated_at else None
        }
    finally:
        db.close()


@app.post("/movie/vector")
def movie_vector_endpoint(body: dict) -> dict:
    """
    Process movie vector and optionally save to database
    
    Request body:
        - movie_id: Movie ID (required)
        - title: Movie title (required)
        - overview, synopsis, keywords, genres, directors, cast: Movie metadata (optional)
        - save_to_db: Whether to save to database (default: False)
    """
    from db import SessionLocal
    from repositories.movie_vector import MovieVectorRepository
    
    try:
        body = validate_request("a2_movie_vector_request.json", body)
        result = process_movie_vector(body)
        
        # Save to database if save_to_db is True
        save_to_db = body.get("save_to_db", False)
        
        if save_to_db:
            db = SessionLocal()
            try:
                repo = MovieVectorRepository(db)
                
                # Save to database
                saved_vector = repo.upsert(
                    movie_id=result["movie_id"],
                    emotion_scores=result["emotion_scores"],
                    narrative_traits=result["narrative_traits"],
                    direction_mood=result["direction_mood"],
                    character_relationship=result["character_relationship"],
                    ending_preference=result["ending_preference"],
                    embedding_text=result.get("embedding_text"),
                    embedding_vector=result.get("embedding", [])
                )
                
                result["saved"] = True
                result["vector_id"] = saved_vector.id
            finally:
                db.close()
        else:
            result["saved"] = False
        
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/movies/{movie_id}/vector")
def get_movie_vector_endpoint(movie_id: int) -> dict:
    """
    Get saved movie vector by movie_id
    
    Returns:
        Movie vector data including all feature scores
    """
    from db import SessionLocal
    from repositories.movie_vector import MovieVectorRepository
    
    db = SessionLocal()
    try:
        repo = MovieVectorRepository(db)
        vector = repo.get_by_movie_id(movie_id)
        
        if not vector:
            raise HTTPException(status_code=404, detail=f"Vector not found for movie_id: {movie_id}")
        
        return {
            "movie_id": vector.movie_id,
            "emotion_scores": vector.emotion_scores,
            "narrative_traits": vector.narrative_traits,
            "direction_mood": vector.direction_mood,
            "character_relationship": vector.character_relationship,
            "ending_preference": vector.ending_preference,
            "embedding_text": vector.embedding_text,
            "embedding_vector": vector.embedding_vector,
            "updated_at": vector.updated_at.isoformat() if vector.updated_at else None
        }
    finally:
        db.close()


@app.post("/movies/vectors/batch")
def get_movie_vectors_batch_endpoint(body: dict) -> dict:
    """
    Get multiple movie vectors by movie_ids
    
    Request body:
        - movie_ids: List of movie IDs
    
    Returns:
        Dictionary mapping movie_id to vector data
    """
    from db import SessionLocal
    from repositories.movie_vector import MovieVectorRepository
    
    movie_ids = body.get("movie_ids", [])
    if not movie_ids:
        raise HTTPException(status_code=400, detail="movie_ids is required")
    
    db = SessionLocal()
    try:
        repo = MovieVectorRepository(db)
        vectors = repo.get_by_movie_ids(movie_ids)
        
        result = {}
        for vector in vectors:
            result[vector.movie_id] = {
                "emotion_scores": vector.emotion_scores,
                "narrative_traits": vector.narrative_traits,
                "direction_mood": vector.direction_mood,
                "character_relationship": vector.character_relationship,
                "ending_preference": vector.ending_preference,
                "embedding_text": vector.embedding_text,
                "embedding_vector": vector.embedding_vector,
                "updated_at": vector.updated_at.isoformat() if vector.updated_at else None
            }
        
        return {
            "total": len(result),
            "vectors": result
        }
    finally:
        db.close()


@app.post("/predict/satisfaction")
def predict_satisfaction_endpoint(body: dict) -> dict:
    """
    만족도 예측 API
    - user_id가 있으면: DB에서 UserPreference 조회
    - user_id가 없으면: body의 user_profile 사용 (하위 호환성)
    
    TODO: JWT 인증 추가 시 토큰에서 user_id 추출
    """
    try:
        from db import SessionLocal
        from models import UserPreference
        
        # user_id가 있으면 DB에서 조회
        user_id = body.get("user_id")
        if user_id:
            db = SessionLocal()
            try:
                user_pref = db.query(UserPreference).filter(
                    UserPreference.user_id == user_id
                ).first()
                
                if not user_pref or not user_pref.preference_vector_json:
                    raise HTTPException(status_code=404, detail="사용자 선호도를 찾을 수 없습니다")
                
                # preference_vector_json에서 global 프로필 추출
                pref_json = user_pref.preference_vector_json
                if 'global' in pref_json:
                    # 신 형식: global 키가 있는 경우
                    user_profile = pref_json['global']
                else:
                    # 구 형식: 최상위에 직접 있는 경우
                    user_profile = pref_json
                
                # DB에서 가져온 프로필로 교체
                body["user_profile"] = user_profile
                body["dislike_tags"] = user_pref.dislikes or []
                body["boost_tags"] = user_pref.boost_tags or []
            finally:
                db.close()
        
        # 기존 로직 실행
        body = validate_request("a3_predict_request.json", body)
        return predict_satisfaction(body)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/explain/prediction")
def explain_prediction_endpoint(body: dict) -> dict:
    try:
        body = validate_request("a4_explain_request.json", body)
        return explain_prediction(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/search/emotional")
def emotional_search_endpoint(body: dict) -> dict:
    try:
        body = validate_request("a5_search_request.json", body)
        return emotional_search(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/group/simulate")
def group_simulate_endpoint(body: dict) -> dict:
    try:
        body = validate_request("a6_group_request.json", body)
        return simulate_group(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/map/taste")
def taste_map_endpoint(body: dict) -> dict:
    try:
        body = validate_request("a7_map_request.json", body)
        return build_taste_map(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
