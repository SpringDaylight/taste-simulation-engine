"""
watched_movies 필터링 테스트 스크립트

3가지 추천 방식에서 watched_movies가 제대로 필터링되는지 확인합니다.
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from repositories.watched import WatchedMovieRepository
from repositories.user import UserRepository
from repositories.movie_vector import MovieVectorRepository


def test_watched_repository():
    """WatchedMovieRepository.get_watched_movie_ids() 테스트"""
    print("\n" + "="*80)
    print("1. WatchedMovieRepository 테스트")
    print("="*80)
    
    db = SessionLocal()
    try:
        watched_repo = WatchedMovieRepository(db)
        user_repo = UserRepository(db)
        
        # 첫 번째 사용자 가져오기
        users = user_repo.get_all(limit=1)
        if not users:
            print("❌ 테스트할 사용자가 없습니다.")
            return
        
        user = users[0]
        print(f"\n✅ 테스트 사용자: {user.nickname} (ID: {user.id})")
        
        # watched 영화 ID 가져오기
        watched_ids = watched_repo.get_watched_movie_ids(user.id)
        print(f"✅ 사용자가 본 영화: {len(watched_ids)}개")
        
        if watched_ids:
            print(f"   영화 ID 샘플: {watched_ids[:5]}")
        
        # 캐싱 테스트
        print("\n🔄 캐싱 테스트 (두 번째 호출)...")
        watched_ids_2 = watched_repo.get_watched_movie_ids(user.id)
        print(f"✅ 캐시에서 가져온 영화: {len(watched_ids_2)}개")
        
        if watched_ids == watched_ids_2:
            print("✅ 캐싱 정상 작동")
        else:
            print("❌ 캐싱 오류")
        
    finally:
        db.close()


def test_llm_orchestrator_filtering():
    """LLM Orchestrator에서 watched 필터링 테스트"""
    print("\n" + "="*80)
    print("2. LLM Orchestrator 필터링 테스트")
    print("="*80)
    
    db = SessionLocal()
    try:
        from llm_lab.orchestrator import LLMOrchestrator
        from repositories.user import UserRepository
        
        # 첫 번째 사용자 가져오기
        user_repo = UserRepository(db)
        users = user_repo.get_all(limit=1)
        if not users:
            print("❌ 테스트할 사용자가 없습니다.")
            return
        
        user = users[0]
        print(f"\n✅ 테스트 사용자: {user.nickname} (ID: {user.id})")
        
        # Orchestrator 추천 실행
        orchestrator = LLMOrchestrator()
        
        print("\n🔍 추천 실행 중 (watched 필터링 포함)...")
        result = orchestrator.recommend(
            user_input="감동적인 영화 추천해줘",
            top_k=5,
            candidate_pool_size=50,
            user_id=user.id  # user_id 전달
        )
        
        print(f"\n✅ 추천 결과: {len(result['recommendations'])}개")
        print(f"   후보군 크기: {result['candidates_count']}개")
        
        # 추천된 영화가 watched에 없는지 확인
        watched_repo = WatchedMovieRepository(db)
        watched_ids = set(watched_repo.get_watched_movie_ids(user.id))
        
        for i, movie in enumerate(result['recommendations'], 1):
            movie_id = movie['movie_id']
            is_watched = movie_id in watched_ids
            status = "❌ 이미 본 영화!" if is_watched else "✅"
            print(f"   {i}. {movie['title']} (ID: {movie_id}) {status}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_basic_recommend_filtering():
    """기본 추천 (홈 화면)에서 watched 필터링 테스트"""
    print("\n" + "="*80)
    print("3. 기본 추천 (홈 화면) 필터링 테스트")
    print("="*80)
    
    db = SessionLocal()
    try:
        from repositories.user import UserRepository
        from repositories.user_preference import UserPreferenceRepository
        from repositories.movie_vector import MovieVectorRepository
        from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved
        
        # 첫 번째 사용자 가져오기
        user_repo = UserRepository(db)
        users = user_repo.get_all(limit=1)
        if not users:
            print("❌ 테스트할 사용자가 없습니다.")
            return
        
        user = users[0]
        print(f"\n✅ 테스트 사용자: {user.nickname} (ID: {user.id})")
        
        # 사용자 선호도 가져오기
        pref_repo = UserPreferenceRepository(db)
        user_pref = pref_repo.get_by_user_id(user.id)
        
        if not user_pref or not user_pref.preference_vector_json:
            print("❌ 사용자 선호도가 없습니다.")
            return
        
        print("✅ 사용자 선호도 로드 완료")
        
        # watched 영화 ID 가져오기
        watched_repo = WatchedMovieRepository(db)
        exclude_movie_ids = watched_repo.get_watched_movie_ids(user.id)
        print(f"✅ 제외할 영화: {len(exclude_movie_ids)}개")
        
        # 모든 영화 벡터 가져오기
        movie_repo = MovieVectorRepository(db)
        all_vectors = movie_repo.get_all_with_movie_info()
        
        print(f"✅ 전체 영화: {len(all_vectors)}개")
        
        # 만족도 계산 (watched 제외)
        recommendations = []
        for vector_data in all_vectors:
            # watched 영화 스킵
            if vector_data["movie_id"] in exclude_movie_ids:
                continue
            
            movie_profile = {
                "emotion_scores": vector_data["emotion_scores"],
                "narrative_traits": vector_data["narrative_traits"],
                "ending_preference": vector_data["ending_preference"]
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
            
            recommendations.append({
                "movie_id": vector_data["movie_id"],
                "title": vector_data["title"],
                "probability": result["probability"]
            })
        
        # 정렬
        recommendations.sort(key=lambda x: x["probability"], reverse=True)
        top_5 = recommendations[:5]
        
        print(f"\n✅ 추천 결과 (watched 제외): {len(recommendations)}개")
        print(f"   Top 5:")
        
        watched_ids_set = set(exclude_movie_ids)
        for i, movie in enumerate(top_5, 1):
            is_watched = movie["movie_id"] in watched_ids_set
            status = "❌ 이미 본 영화!" if is_watched else "✅"
            print(f"   {i}. {movie['title']} ({movie['probability']*100:.1f}%) {status}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """모든 테스트 실행"""
    print("\n" + "="*80)
    print("watched_movies 필터링 테스트")
    print("="*80)
    
    try:
        # 1. Repository 테스트
        test_watched_repository()
        
        # 2. LLM Orchestrator 테스트
        test_llm_orchestrator_filtering()
        
        # 3. 기본 추천 테스트
        test_basic_recommend_filtering()
        
        print("\n" + "="*80)
        print("✅ 모든 테스트 완료")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
