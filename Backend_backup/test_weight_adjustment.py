# -*- coding: utf-8 -*-
"""
동적 가중치 조정 테스트
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from llm_lab.orchestrator import LLMOrchestrator

print("\n" + "="*80)
print("🎯 동적 가중치 조정 테스트")
print("="*80)

orchestrator = LLMOrchestrator()

# 테스트 쿼리들
test_cases = [
    {
        "query": "직장 상사와 관련된 영화를 추천해줘",
        "expected": "키워드 중심 (주제 기반)",
        "expected_weight": "키워드 80-90%"
    },
    {
        "query": "우울한 영화 추천해줘",
        "expected": "감성 중심 (감성 기반)",
        "expected_weight": "감성 70-80%"
    },
    {
        "query": "가족과 함께 볼 따뜻한 영화",
        "expected": "균형 (주제 + 감성)",
        "expected_weight": "균형 50:50"
    },
    {
        "query": "비 오는 날 막걸리 마시면서 보기 좋은 영화",
        "expected": "키워드 중심 (상황 기반)",
        "expected_weight": "키워드 60-80%"
    },
    {
        "query": "설레는 로맨스 영화",
        "expected": "감성 중심 (감성 기반)",
        "expected_weight": "감성 70%"
    },
    {
        "query": "학교 생활을 다룬 영화",
        "expected": "키워드 중심 (주제 기반)",
        "expected_weight": "키워드 80%"
    }
]

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"테스트 {i}: {test['query']}")
    print(f"예상: {test['expected']} ({test['expected_weight']})")
    print("="*80)
    
    try:
        # Planner 실행 (가중치 결정 포함)
        query_plan = orchestrator._plan_query(test['query'])
        
        print(f"\n📊 쿼리 분석:")
        print(f"  키워드: {query_plan.get('keywords', [])}")
        print(f"  감성: {query_plan.get('mood', [])}")
        
        # 가중치 결정
        keyword_weight, emotion_weight = orchestrator._determine_weights(
            user_input=test['query'],
            query_plan=query_plan
        )
        
        print(f"\n🎯 결정된 가중치:")
        print(f"  키워드: {keyword_weight*100:.0f}%")
        print(f"  감성: {emotion_weight*100:.0f}%")
        
        # 판단
        if keyword_weight > 0.7:
            result_type = "키워드 중심"
        elif emotion_weight > 0.7:
            result_type = "감성 중심"
        else:
            result_type = "균형"
        
        print(f"\n✅ 결과: {result_type}")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

orchestrator.close()

print("\n" + "="*80)
print("✅ 테스트 완료")
print("="*80)

print("\n📝 요약:")
print("- 주제 키워드 (직장, 상사, 학교 등) → 키워드 가중치 증가")
print("- 감성 키워드 (우울, 힐링, 설레 등) → 감성 가중치 증가")
print("- 둘 다 있으면 → 균형 (50:50)")
print("- 둘 다 없으면 → 약간 키워드 우선 (60:40)")
print()
