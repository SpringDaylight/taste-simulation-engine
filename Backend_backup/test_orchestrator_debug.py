# -*- coding: utf-8 -*-
"""
오케스트레이터 디버깅 테스트
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from llm_lab.orchestrator import LLMOrchestrator

print("\n" + "="*80)
print("🎬 오케스트레이터 디버깅 테스트")
print("="*80)

orchestrator = LLMOrchestrator()

# 테스트 쿼리
test_query = "직장 상사와 관련된 영화를 추천해줘"

print(f"\n📝 사용자 입력: {test_query}")

try:
    # 추천 실행
    result = orchestrator.recommend(
        user_input=test_query,
        top_k=5,
        candidate_pool_size=30  # 작은 풀로 테스트
    )
    
    print("\n" + "="*80)
    print("✅ 최종 추천 결과")
    print("="*80)
    
    print(f"\n후보 수: {result['candidates_count']}개")
    print(f"추천 수: {len(result['recommendations'])}개")
    
    print(f"\n전체 설명: {result['explanation']}")
    
    print("\n추천 영화:")
    for i, movie in enumerate(result['recommendations'], 1):
        print(f"\n{i}. {movie['title']} (ID: {movie['movie_id']})")
        print(f"   장르: {', '.join(movie['genres'])}")
        print(f"   점수: {movie['similarity_score']:.3f}")
        if movie.get('reason'):
            print(f"   이유: {movie['reason']}")
    
except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()

orchestrator.close()

print("\n" + "="*80)
print("✅ 테스트 완료")
print("="*80)
