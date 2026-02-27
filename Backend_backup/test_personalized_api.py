"""
개인 맞춤 추천 API 테스트 스크립트
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from repositories.user import UserRepository
from repositories.user_preference import UserPreferenceRepository
from repositories.watched import WatchedMovieRepository
from repositories.movie_vector import MovieVectorRepository
from models import MovieVector, Movie
from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved


def test_personalized_recommendation():
    """개인 맞춤 추천 로직 테스트"""
    print("\n" + "="*80)
    print("개인 맞춤 추천 API 테스트")
    print("="*80)
    
    db = SessionLocal()
    try:
        # 1. 테스트 사용자 선택
        user_repo = UserRepository(db)
        users = user_repo.get_all(limit=1)
        
        if not users:
            print("❌ 테스트할 사용자가 없습니다.")
            return
        
        user = users[0]
        user_id = user.id
        print(f"\n✅ 테스트 사용자: {user.nickname} (ID: {user_id})")
        
        # 2. 사용자 선호도 확인
        pref_repo = UserPreferenceRepository(db)
        user_pref = pref_repo.get_by_user_id(user_id)
        
        if not user_pref or not user_pref.preference_vector_json:
            print("❌ 사용자 선호도가 없습니다.")
            return
        
        print("✅ 사용자 선호도 로드 완료")
        
        # 3. watched 영화 확인
        watched_repo = WatchedMovieRepository(db)
        exclude_movie_ids = watched_repo.get_watched_movie_ids(user_id)
        print(f"✅ 제외할 영화: {len(exclude_movie_ids)}개")
        
        # 4. 후보 영화 가져오기
        candidate_pool_size = 50
        query = (
            db.query(MovieVector, Movie)
            .join(Movie, MovieVector.movie_id == Movie.id)
            .order_by(Movie.avg_rating.desc().nullslast())
        )
        
        if exclude_movie_ids:
            query = query.filter(~MovieVector.movie_id.in_(exclude_movie_ids))
        
        candidates = query.limit(candidate_pool_size).all()
        print(f"✅ 후보 영화: {len(candidates)}개")
        
        if not candidates:
            print("❌ 추천할 영화가 없습니다.")
            return
        
        # 5. 만족도 계산
        print(f"\n🔄 만족도 계산 중...")
        recommendations = []
        
        for movie_vector, movie in candidates:
            movie_profile = {
                'emotion_scores': movie_vector.emotion_scores,
                'narrative_traits': movie_vector.narrative_traits,
                'ending_preference': movie_vector.ending_preference or {}
            }
            
            result = calculate_satisfaction_probability_improved(
                user_profile=user_pref.preference_vector_json,
                movie_profile=movie_profile,
                dislikes=user_pref.dislike_tags or [],
                boost_tags=user_pref.boost_tags or [],
                use_sigmoid=True,
                sigmoid_k=6.0,
                sigmoid_x0=0.5
            )
            
            probability = result['probability']
            match_rate = int(probability * 100)
            
            recommendations.append({
                'movie_id': movie.id,
                'title': movie.title,
                'probability': probability,
                'match_rate': match_rate
            })
        
        # 6. 정렬
        recommendations.sort(key=lambda x: x['probability'], reverse=True)
        top_12 = recommendations[:12]
        
        print(f"\n✅ 추천 완료: {len(top_12)}개")
        print(f"   평균 만족도: {sum(r['match_rate'] for r in top_12) / len(top_12):.1f}%")
        
        # 7. 결과 출력
        print(f"\n📊 Top 12 추천 영화:")
        for i, rec in enumerate(top_12, 1):
            print(f"   {i:2d}. {rec['title'][:40]:40s} - {rec['match_rate']:3d}%")
        
        # 8. watched 영화가 포함되지 않았는지 확인
        watched_ids_set = set(exclude_movie_ids)
        has_watched = any(r['movie_id'] in watched_ids_set for r in top_12)
        
        if has_watched:
            print("\n❌ 경고: watched 영화가 추천에 포함되었습니다!")
        else:
            print("\n✅ watched 영화 필터링 정상 작동")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_api_endpoint():
    """실제 API 엔드포인트 테스트 (curl 명령어 출력)"""
    print("\n" + "="*80)
    print("API 엔드포인트 테스트 명령어")
    print("="*80)
    
    print("\n1. 빠른 추천 (12개):")
    print("   curl -X GET 'http://localhost:8000/api/personalized/recommendations/quick' \\")
    print("        -H 'Authorization: Bearer YOUR_JWT_TOKEN'")
    
    print("\n2. 커스텀 추천 (top_k=20, pool=200):")
    print("   curl -X GET 'http://localhost:8000/api/personalized/recommendations?top_k=20&candidate_pool_size=200' \\")
    print("        -H 'Authorization: Bearer YOUR_JWT_TOKEN'")
    
    print("\n3. Swagger UI에서 테스트:")
    print("   http://localhost:8000/docs#/personalized-recommend")


if __name__ == "__main__":
    test_personalized_recommendation()
    test_api_endpoint()
    
    print("\n" + "="*80)
    print("✅ 테스트 완료")
    print("="*80)
