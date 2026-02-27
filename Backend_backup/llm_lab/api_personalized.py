"""
개인 맞춤 추천 API
홈 화면용 - 사용자 취향 기반 영화 추천
"""
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from api.deps import get_current_user
from models import UserPreference, MovieVector, Movie
from repositories.watched import WatchedMovieRepository
from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved

router = APIRouter(prefix="/api/personalized", tags=["personalized-recommend"])


class PersonalizedMovie(BaseModel):
    """개인 맞춤 추천 영화"""
    movie_id: int
    title: str
    poster_url: Optional[str] = None
    genres: List[str] = []
    release_year: Optional[int] = None
    avg_rating: Optional[float] = None
    synopsis: Optional[str] = None
    satisfaction_probability: float  # 만족도 확률 (0.0 ~ 1.0)
    match_rate: int  # 적합도 퍼센트 (0 ~ 100)
    detail_url: str


class PersonalizedRecommendResponse(BaseModel):
    """개인 맞춤 추천 응답"""
    recommendations: List[PersonalizedMovie]
    total: int
    user_id: str
    has_preference: bool


@router.get("/recommendations", response_model=PersonalizedRecommendResponse)
async def get_personalized_recommendations(
    top_k: int = Query(12, ge=1, le=50, description="추천할 영화 개수"),
    candidate_pool_size: int = Query(100, ge=20, le=500, description="후보 풀 크기"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    개인 맞춤 영화 추천 (홈 화면용)
    
    - JWT 인증 필수
    - 사용자 선호도 기반 만족도 계산
    - watched 영화 자동 제외
    - 만족도 순으로 정렬된 영화 리스트 반환
    
    Args:
        top_k: 최종 추천 개수 (기본 12개)
        candidate_pool_size: 후보 풀 크기 (기본 100개)
    
    Returns:
        정렬된 추천 영화 리스트
    """
    user_id = current_user.id
    
    print(f"\n{'='*80}")
    print(f"[개인 맞춤 추천] 사용자: {user_id}")
    print(f"{'='*80}")
    
    def _execute_recommendation():
        """동기 함수로 DB 작업 수행"""
        # 1. 사용자 선호도 확인
        user_pref = db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
        
        if not user_pref or not user_pref.preference_vector_json:
            raise HTTPException(
                status_code=404, 
                detail="사용자 선호도를 찾을 수 없습니다. 취향 설문을 먼저 진행해주세요."
            )
        
        print(f"✅ 사용자 선호도 로드 완료")
        
        # preference_vector_json에서 global 프로필 추출
        pref_json = user_pref.preference_vector_json
        if 'global' in pref_json:
            # 신 형식: global 키가 있는 경우
            user_profile = pref_json['global']
        else:
            # 구 형식: 최상위에 직접 있는 경우
            user_profile = pref_json
        
        # 2. watched 영화 ID 가져오기
        watched_repo = WatchedMovieRepository(db)
        exclude_movie_ids = watched_repo.get_watched_movie_ids(user_id)
        print(f"✅ 제외할 영화: {len(exclude_movie_ids)}개")
        
        # 3. 후보 영화 가져오기 (인기순 + watched 제외)
        query = (
            db.query(MovieVector, Movie)
            .join(Movie, MovieVector.movie_id == Movie.id)
            .order_by(Movie.avg_rating.desc().nullslast())  # 평점 높은 순
        )
        
        # watched 영화 제외
        if exclude_movie_ids:
            query = query.filter(~MovieVector.movie_id.in_(exclude_movie_ids))
        
        candidates = query.limit(candidate_pool_size).all()
        
        if not candidates:
            raise HTTPException(
                status_code=404,
                detail="추천할 영화를 찾을 수 없습니다."
            )
        
        print(f"✅ 후보 영화: {len(candidates)}개")
        
        # 4. 각 영화의 만족도 계산
        print(f"🔄 만족도 계산 중...")
        recommendations = []
        
        for movie_vector, movie in candidates:
            movie_profile = {
                'emotion_scores': movie_vector.emotion_scores,
                'narrative_traits': movie_vector.narrative_traits,
                'ending_preference': movie_vector.ending_preference or {}
            }
            
            # 만족도 계산
            result = calculate_satisfaction_probability_improved(
                user_profile=user_profile,
                movie_profile=movie_profile,
                dislikes=user_pref.dislike_tags or [],
                boost_tags=user_pref.boost_tags or [],
                use_sigmoid=True,
                sigmoid_k=6.0,
                sigmoid_x0=0.5
            )
            
            probability = result['probability']
            match_rate = int(probability * 100)
            
            # 영화 정보 구성
            recommendations.append({
                'movie_id': movie.id,
                'title': movie.title,
                'poster_url': movie.poster_url,
                'genres': [g.genre for g in movie.genres],
                'release_year': movie.release.year if movie.release else None,
                'avg_rating': float(movie.avg_rating) if movie.avg_rating else None,
                'synopsis': movie.synopsis,
                'satisfaction_probability': probability,
                'match_rate': match_rate,
                'detail_url': f'/movies/{movie.id}'
            })
        
        # 5. 만족도 순으로 정렬
        recommendations.sort(key=lambda x: x['satisfaction_probability'], reverse=True)
        
        # 6. 상위 K개 선택
        top_recommendations = recommendations[:top_k]
        
        print(f"✅ 추천 완료: {len(top_recommendations)}개")
        print(f"   평균 만족도: {sum(r['match_rate'] for r in top_recommendations) / len(top_recommendations):.1f}%")
        
        return {
            'recommendations': [PersonalizedMovie(**r) for r in top_recommendations],
            'total': len(top_recommendations),
            'user_id': user_id,
            'has_preference': True
        }
    
    # 비동기 실행
    try:
        return await asyncio.to_thread(_execute_recommendation)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 추천 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/recommendations/quick", response_model=PersonalizedRecommendResponse)
async def get_quick_recommendations(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    빠른 개인 맞춤 추천 (홈 화면 초기 로딩용)
    
    - 후보 50개, 추천 12개로 고정
    - 빠른 응답을 위한 최적화된 버전
    """
    return await get_personalized_recommendations(
        top_k=12,
        candidate_pool_size=50,
        current_user=current_user,
        db=db
    )
