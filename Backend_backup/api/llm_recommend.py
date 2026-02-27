"""
LLM 기반 영화 추천 API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import SessionLocal
from repositories.movie_vector import MovieVectorRepository
from ml.model_sample.analysis import description, similarity
import boto3
import os

router = APIRouter(prefix="/api/llm", tags=["llm-recommend"])


class RecommendRequest(BaseModel):
    user_input: str = Field(..., description="사용자 입력 텍스트")
    top_k: int = Field(default=5, ge=1, le=20, description="추천할 영화 개수")
    candidate_pool_size: int = Field(default=50, ge=10, le=200, description="후보 풀 크기")
    genres: Optional[List[str]] = Field(default=None, description="장르 필터")
    year_from: Optional[int] = Field(default=None, description="개봉년도 시작")
    year_to: Optional[int] = Field(default=None, description="개봉년도 끝")
    use_orchestrator: bool = Field(default=False, description="오케스트레이터 사용 여부")


class Movie(BaseModel):
    movie_id: int
    title: str
    genres: List[str]
    release_year: int
    similarity_score: float
    final_score: Optional[float] = None
    weighted_score: Optional[float] = None
    keyword_score: Optional[float] = None
    emotion_score: Optional[float] = None
    sources: Optional[List[str]] = None
    detail_url: str
    poster_url: Optional[str] = None
    rating: Optional[float] = None
    synopsis: Optional[str] = None
    reason: Optional[str] = None
    is_selected: Optional[bool] = None
    not_selected_reason: Optional[str] = None


class RecommendResponse(BaseModel):
    recommendations: List[Movie]
    explanation: str
    candidates_count: int
    method: str = "basic"
    usage: Optional[Dict[str, int]] = None
    keyword_candidates: Optional[List[Movie]] = None
    vector_candidates: Optional[List[Movie]] = None
    keyword_weight: Optional[float] = None
    emotion_weight: Optional[float] = None


class ExplainRequest(BaseModel):
    user_input: str
    movie_title: str
    movie_synopsis: Optional[str] = None
    genres: Optional[List[str]] = None
    keyword_score: Optional[float] = None
    emotion_score: Optional[float] = None
    final_score: Optional[float] = None


class ExplainResponse(BaseModel):
    explanation: str
    movie_title: str


def get_bedrock_client():
    """AWS Bedrock Runtime 클라이언트 생성"""
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'ap-northeast-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        return bedrock_runtime
    except Exception as e:
        print(f"⚠️  Bedrock 클라이언트 초기화 실패: {e}")
        return None


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_movies(request: RecommendRequest):
    """
    LLM 기반 영화 추천
    
    사용자 입력을 분석하여 감성 프로필을 생성하고,
    DB의 영화 벡터와 비교하여 추천합니다.
    """
    db = SessionLocal()
    try:
        repo = MovieVectorRepository(db)
        
        # 0. 사용자가 본 영화 ID 가져오기 (로그인한 경우)
        exclude_movie_ids = []
        if current_user:
            from repositories.watched import WatchedMovieRepository
            watched_repo = WatchedMovieRepository(db)
            exclude_movie_ids = watched_repo.get_watched_movie_ids(current_user.id)
            if exclude_movie_ids:
                print(f"✅ [LLM Recommend] 사용자가 본 영화 {len(exclude_movie_ids)}개 제외")
        
        # 1. 사용자 입력에서 감성 프로필 생성 (A-1 로직 사용)
        from domain.a1_preference import analyze_preference
        user_profile = analyze_preference({"text": request.user_input})
        
        # 2. DB에서 영화 벡터 가져오기
        all_vectors = repo.get_all_with_movie_info()
        
        if not all_vectors:
            raise HTTPException(status_code=404, detail="영화 벡터 데이터가 없습니다")
        
        # 3. 유사도 계산 (watched 영화 제외)
        recommendations = []
        for vector_data in all_vectors:
            # 이미 본 영화는 스킵
            if vector_data["movie_id"] in exclude_movie_ids:
                continue
            
            movie_profile = {
                "emotion_scores": vector_data["emotion_scores"],
                "narrative_traits": vector_data["narrative_traits"],
                "ending_preference": vector_data["ending_preference"]
            }
            
            # 만족 확률 계산 (개선된 버전)
            from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved
            result = calculate_satisfaction_probability_improved(
                user_profile=user_profile,
                movie_profile=movie_profile,
                dislikes=user_profile.get("dislike_tags", []),
                boost_tags=user_profile.get("boost_tags", []),
                use_sigmoid=True,
                sigmoid_k=6.0,
                sigmoid_x0=0.5
            )
            
            recommendations.append({
                "movie_id": vector_data["movie_id"],
                "title": vector_data["title"],
                "genres": vector_data.get("genres", []),
                "release_year": vector_data.get("release_year", 0),
                "similarity_score": result["probability"],
                "final_score": result["probability"],
                "detail_url": f"/movies/{vector_data['movie_id']}",
                "poster_url": vector_data.get("poster_url"),
                "rating": vector_data.get("avg_rating"),
                "synopsis": vector_data.get("synopsis")
            })
        
        # 4. 정렬 및 상위 K개 선택
        recommendations.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_recommendations = recommendations[:request.top_k]
        
        # 5. LLM 설명 생성
        bedrock_client = get_bedrock_client()
        if bedrock_client and top_recommendations:
            # 첫 번째 추천 영화에 대한 설명 생성
            top_movie = top_recommendations[0]
            prediction_result = {
                "probability": top_movie["similarity_score"],
                "confidence": 0.9,
                "breakdown": {
                    "emotion_similarity": 0.85,
                    "narrative_similarity": 0.80,
                    "ending_similarity": 0.75,
                    "boost_score": 0.0,
                    "dislike_penalty": 0.0,
                    "top_factors": ["정서 톤", "서사 초점"]
                }
            }
            
            explanation = description.generate_explanation(
                prediction_result=prediction_result,
                movie_title=top_movie["title"],
                user_liked_tags=user_profile.get("boost_tags", []),
                user_disliked_tags=user_profile.get("dislike_tags", []),
                bedrock_client=bedrock_client
            )
        else:
            explanation = f"'{request.user_input}' 입력에 기반하여 {len(top_recommendations)}개의 영화를 추천합니다."
        
        return RecommendResponse(
            recommendations=[Movie(**rec) for rec in top_recommendations],
            explanation=explanation,
            candidates_count=len(recommendations),
            method="orchestrator" if request.use_orchestrator else "basic"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 실패: {str(e)}")
    finally:
        db.close()


@router.post("/explain", response_model=ExplainResponse)
async def explain_recommendation(request: ExplainRequest):
    """
    특정 영화 추천 이유 상세 설명
    
    LLM을 사용하여 왜 이 영화가 사용자에게 추천되었는지 설명합니다.
    """
    try:
        bedrock_client = get_bedrock_client()
        
        if not bedrock_client:
            return ExplainResponse(
                explanation=f"'{request.movie_title}'은(는) 입력하신 취향과 잘 맞는 영화입니다.",
                movie_title=request.movie_title
            )
        
        # 예측 결과 구성
        prediction_result = {
            "probability": request.final_score or 0.8,
            "confidence": 0.9,
            "breakdown": {
                "emotion_similarity": request.emotion_score or 0.85,
                "narrative_similarity": 0.80,
                "ending_similarity": 0.75,
                "boost_score": 0.0,
                "dislike_penalty": 0.0,
                "top_factors": ["정서 톤", "서사 초점"]
            }
        }
        
        # LLM 설명 생성
        explanation = description.generate_explanation(
            prediction_result=prediction_result,
            movie_title=request.movie_title,
            user_liked_tags=[],
            user_disliked_tags=[],
            bedrock_client=bedrock_client
        )
        
        return ExplainResponse(
            explanation=explanation,
            movie_title=request.movie_title
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설명 생성 실패: {str(e)}")
