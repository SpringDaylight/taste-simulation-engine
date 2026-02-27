# -*- coding: utf-8 -*-
"""
최종 추천 테스트 - "직장상사 길들이기" 확인
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from llm_lab.orchestrator import LLMOrchestrator

print("\n" + "="*80)
print("🎬 최종 추천 테스트")
print("="*80)

orchestrator = LLMOrchestrator()

# 테스트 쿼리
test_query = "제목에 '직장상사'가 들어간 영화 추천해줘"

print(f"\n📝 사용자 입력: {test_query}")

try:
    # 추천 실행 (작은 풀로 빠르게 테스트)
    result = orchestrator.recommend(
        user_input=test_query,
        top_k=5,
        candidate_pool_size=20
    )
    
    print("\n" + "="*80)
    print("✅ 최종 추천 결과")
    print("="*80)
    
    print(f"\n후보 수: {result['candidates_count']}개")
    print(f"추천 수: {len(result['recommendations'])}개")
    
    print("\n추천 영화:")
    found_target = False
    for i, movie in enumerate(result['recommendations'], 1):
        print(f"\n{i}. {movie['title']} (ID: {movie['movie_id']})")
        print(f"   장르: {', '.join(movie['genres'])}")
        print(f"   점수: {movie['similarity_score']:.3f}")
        
        if movie['movie_id'] == 1198994:  # 직장상사 길들이기
            print(f"   🎯 타겟 영화 발견!")
            found_target = True
    
    print("\n" + "="*80)
    if found_target:
        print("✅ 성공: '직장상사 길들이기' 추천됨!")
    else:
        print("⚠️ 실패: '직장상사 길들이기' 추천 안됨")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()

orchestrator.close()
