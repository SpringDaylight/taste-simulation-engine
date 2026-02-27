"""
LLM 기반 영화 추천 API
"""
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from llm_lab.recommender import LLMRecommender
from llm_lab.orchestrator import LLMOrchestrator
from api.deps import get_current_user_optional

router = APIRouter(prefix="/api/llm", tags=["llm-recommend"])

# 전역 추천기
recommender = LLMRecommender()
orchestrator = LLMOrchestrator()


class RecommendRequest(BaseModel):
    user_input: str
    top_k: int = 5
    candidate_pool_size: int = 20
    genres: Optional[List[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    use_orchestrator: bool = False  # 오케스트레이터 사용 여부


class ExplainRequest(BaseModel):
    user_input: str
    movie_title: str
    movie_synopsis: Optional[str] = None
    genres: Optional[List[str]] = None
    keyword_score: Optional[float] = None
    emotion_score: Optional[float] = None
    final_score: Optional[float] = None


class SatisfactionRequest(BaseModel):
    movie_id: int
    user_id: Optional[str] = None  # 로그인한 사용자 ID (문자열 UUID)


class Movie(BaseModel):
    movie_id: int
    title: str
    genres: List[str]
    release_year: int
    similarity_score: float  # 프론트 호환성 (final_score와 동일)
    final_score: Optional[float] = None  # 최종 점수 (가중치 + 보너스)
    weighted_score: Optional[float] = None  # 가중치 적용 점수
    keyword_score: Optional[float] = None  # 키워드 점수
    emotion_score: Optional[float] = None  # 감성 점수
    sources: Optional[List[str]] = None  # 검색 소스 (keyword, vector)
    detail_url: str
    poster_url: Optional[str] = None
    rating: Optional[float] = None
    synopsis: Optional[str] = None  # 시놉시스
    reason: Optional[str] = None  # 개별 추천 이유
    is_selected: Optional[bool] = None  # 최종 선택 여부
    not_selected_reason: Optional[str] = None  # 선택되지 않은 이유
    satisfaction_probability: Optional[float] = None  # 만족도 확률


class RecommendResponse(BaseModel):
    recommendations: List[Movie]
    explanation: str
    candidates_count: int
    usage: Optional[dict] = None
    method: str = "basic"  # basic or orchestrator
    keyword_candidates: Optional[List[Movie]] = None  # 키워드 후보군
    vector_candidates: Optional[List[Movie]] = None  # 벡터 후보군
    keyword_weight: Optional[float] = None  # 키워드 가중치
    emotion_weight: Optional[float] = None  # 감성 가중치


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_movies(
    request: RecommendRequest,
    current_user = Depends(get_current_user_optional)
):
    """
    LLM 기반 영화 추천
    
    - use_orchestrator=False: 기존 방식 (하이브리드 검색 + LLM 선택)
    - use_orchestrator=True: 오케스트레이터 방식 (LLM 컨트롤러)
    """
    try:
        # 사용자 ID 추출 (로그인한 경우)
        user_id = current_user.id if current_user else None
        
        if request.use_orchestrator:
            # 오케스트레이터 방식 - wrap blocking operation in thread pool
            result = await asyncio.to_thread(
                orchestrator.recommend,
                user_input=request.user_input,
                top_k=request.top_k,
                candidate_pool_size=request.candidate_pool_size,
                user_id=user_id  # 사용자 ID 전달
            )
            result['method'] = 'orchestrator'
        else:
            # 기존 방식 - wrap blocking operation in thread pool
            result = await asyncio.to_thread(
                recommender.recommend,
                user_input=request.user_input,
                top_k=request.top_k,
                candidate_pool_size=request.candidate_pool_size,
                genres=request.genres,
                year_from=request.year_from,
                year_to=request.year_to
            )
            result['method'] = 'basic'
        
        return RecommendResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 오류: {str(e)}")


@router.post("/explain")
async def explain_recommendation(request: ExplainRequest):
    """
    특정 영화 추천 이유를 LLM으로 상세 설명 (캐싱 적용)
    """
    try:
        from llm_lab.async_client import AsyncLLMClient
        from utils.cache import cache_get, cache_set
        
        # 캐시 키 생성: explanation:{user_input_hash}:{movie_title}
        # user_input을 해시화하여 키 길이 제한
        import hashlib
        user_input_hash = hashlib.md5(request.user_input.encode()).hexdigest()[:16]
        cache_key = f"explanation:{user_input_hash}:{request.movie_title}"
        
        # 캐시 확인
        cached_result = cache_get(cache_key)
        if cached_result:
            print(f"✅ [Explain] Cache hit: {cache_key}")
            return cached_result
        
        print(f"🔍 [Explain] Cache miss, generating: {cache_key}")
        
        llm_client = AsyncLLMClient()
        
        # 점수 정보를 내부적으로만 사용 (LLM에게 컨텍스트 제공)
        score_context = ""
        has_keyword_match = request.keyword_score is not None and request.keyword_score > 0
        has_emotion_match = request.emotion_score is not None and request.emotion_score > 0
        
        if has_keyword_match and has_emotion_match:
            score_context = "\n\n[내부 정보] 이 영화는 키워드 매칭과 감성 유사도 모두에서 높은 점수를 받았습니다."
        elif has_keyword_match:
            score_context = "\n\n[내부 정보] 이 영화는 주로 키워드 매칭을 통해 선택되었습니다."
        elif has_emotion_match:
            score_context = "\n\n[내부 정보] 이 영화는 주로 감성 유사도를 통해 선택되었습니다."
        
        # 장르 정보
        genre_info = ""
        if request.genres:
            genre_info = f"\n- 장르: {', '.join(request.genres)}"
        
        # 시놉시스 정보
        synopsis_info = ""
        if request.movie_synopsis:
            synopsis_info = f"\n- 줄거리: {request.movie_synopsis[:200]}..."
        
        prompt = f"""사용자가 "{request.user_input}"라고 요청했을 때, 
영화 "{request.movie_title}"을(를) 추천한 이유를 자세히 설명해주세요.

영화 정보:{genre_info}{synopsis_info}{score_context}

다음 내용을 포함해서 2-3문단으로 설명해주세요:
1. 이 영화가 사용자 요청과 어떻게 관련되는지
2. 영화의 어떤 특징(주제, 분위기, 스토리 등)이 사용자의 니즈를 충족시키는지
3. 왜 이 영화가 다른 후보들 중에서 선택되었는지

⚠️ 중요: 구체적인 점수나 퍼센트는 절대 언급하지 마세요. 대신 영화의 특징과 사용자 요청의 연관성을 자연스럽게 설명하세요.

친근하고 자연스러운 톤으로 작성해주세요."""

        explanation = await llm_client.generate_simple(prompt)
        
        result = {
            "explanation": explanation,
            "movie_title": request.movie_title
        }
        
        # 캐시에 저장 (TTL 24시간 - 설명은 자주 바뀌지 않음)
        cache_set(cache_key, result, ttl=86400)
        print(f"✅ [Explain] Cached result: {cache_key}")
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설명 생성 오류: {str(e)}")


@router.post("/satisfaction")
async def calculate_satisfaction(
    request: SatisfactionRequest,
    current_user = Depends(get_current_user_optional)
):
    """
    사용자 취향과 영화 특성 간의 만족도 확률 계산 (개선된 버전)
    
    JWT 인증을 사용하여 자동으로 사용자 정보를 가져옵니다.
    user_id 파라미터는 하위 호환성을 위해 유지됩니다.
    
    Redis 캐시를 사용하여 동일한 (user_id, movie_id) 조합에 대한 반복 계산을 방지합니다.
    """
    try:
        from db import SessionLocal
        from models import UserPreference, MovieVector
        from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved
        from api.deps import get_current_user_optional
        from utils.cache import cache_get, cache_set
        
        # JWT에서 사용자 정보 가져오기 (우선순위 1)
        user_id = None
        if current_user:
            user_id = current_user.id
            print(f"✅ [Satisfaction] JWT에서 사용자 인증: {user_id}")
        # 하위 호환성: request body의 user_id 사용 (우선순위 2)
        elif request.user_id:
            user_id = request.user_id
            print(f"⚠️ [Satisfaction] Body에서 user_id 사용 (deprecated): {user_id}")
        
        # 로그인하지 않은 경우 에러
        if not user_id:
            print(f"❌ [Satisfaction] user_id 없음 - 401 반환")
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        # 캐시 키 생성: satisfaction:{user_id}:{movie_id}
        cache_key = f"satisfaction:{user_id}:{request.movie_id}"
        
        # 캐시 확인
        cached_result = cache_get(cache_key)
        if cached_result:
            print(f"✅ [Satisfaction] Cache hit: {cache_key}")
            return cached_result
        
        print(f"🔍 [Satisfaction] Cache miss, calculating: {cache_key}")
        
        # Wrap database operations in thread pool
        def _execute_satisfaction_calculation():
            # Wrap SessionLocal() creation
            db = SessionLocal()
            
            try:
                # Wrap database query for movie vector
                movie_vector = db.query(MovieVector).filter(
                    MovieVector.movie_id == request.movie_id
                ).first()
                
                if not movie_vector:
                    raise HTTPException(status_code=404, detail="영화 벡터를 찾을 수 없습니다")
                
                # Wrap database query for user preference
                print(f"✅ [Satisfaction] user_id 있음, DB 조회 시작: {user_id}")
                user_pref = db.query(UserPreference).filter(
                    UserPreference.user_id == user_id
                ).first()
                
                if not user_pref or not user_pref.preference_vector_json:
                    print(f"❌ [Satisfaction] UserPreference 없음")
                    raise HTTPException(status_code=404, detail="사용자 선호도를 찾을 수 없습니다")
                
                print(f"✅ [Satisfaction] UserPreference 찾음")
                
                # preference_vector_json에서 global 프로필 추출
                pref_json = user_pref.preference_vector_json
                if 'global' in pref_json:
                    # 신 형식: global 키가 있는 경우
                    user_profile = pref_json['global']
                else:
                    # 구 형식: 최상위에 직접 있는 경우
                    user_profile = pref_json
                
                # 영화 프로필 구성
                movie_profile = {
                    'emotion_scores': movie_vector.emotion_scores,
                    'narrative_traits': movie_vector.narrative_traits,
                    'ending_preference': movie_vector.ending_preference or {}
                }
                
                # Wrap calculate_satisfaction_probability_improved() call
                result = calculate_satisfaction_probability_improved(
                    user_profile=user_profile,
                    movie_profile=movie_profile,
                    dislikes=user_pref.dislike_tags or [],
                    boost_tags=user_pref.boost_tags or [],
                    use_sigmoid=True,
                    sigmoid_k=6.0,
                    sigmoid_x0=0.5
                )
                
                response = {
                    "movie_id": request.movie_id,
                    "satisfaction_probability": result['probability'],
                    "confidence": result['confidence'],
                    "breakdown": result['breakdown'],
                    "user_id": user_id
                }
                
                # 캐시에 저장 (TTL 1시간)
                cache_set(cache_key, response, ttl=3600)
                print(f"✅ [Satisfaction] Cached result: {cache_key}")
                
                return response
                
            finally:
                # Ensure proper session cleanup in finally block
                db.close()
        
        # Execute in thread pool to avoid blocking event loop
        return await asyncio.to_thread(_execute_satisfaction_calculation)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"만족도 계산 오류: {str(e)}")
