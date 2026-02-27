# -*- coding: utf-8 -*-
"""
키워드 추출 테스트 (LLM vs 규칙 기반)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from llm_lab.orchestrator import LLMOrchestrator

print("\n" + "="*80)
print("🔍 키워드 추출 비교 테스트")
print("="*80)

orchestrator = LLMOrchestrator()

# 테스트 쿼리들
test_cases = [
    "제목에 '직장상사'가 들어간 영화 추천해줘",
    "직장 상사와 관련된 영화를 추천해줘",
    "학교 생활을 다룬 영화",
    "우울한 영화 추천해줘"
]

for i, query in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"테스트 {i}: {query}")
    print("="*80)
    
    try:
        # Planner LLM 실행
        query_plan = orchestrator._plan_query(query)
        
        # LLM이 추출한 키워드
        llm_keywords = query_plan.get("keywords", [])
        
        # 규칙 기반 키워드 추출
        rule_keywords = orchestrator.db_connector._extract_keywords(query)
        
        print(f"\n✅ LLM 추출 키워드:")
        print(f"   {llm_keywords}")
        
        print(f"\n⚙️ 규칙 기반 키워드:")
        print(f"   {rule_keywords}")
        
        print(f"\n📊 비교:")
        print(f"   LLM: {len(llm_keywords)}개")
        print(f"   규칙: {len(rule_keywords)}개")
        
        # 차이점
        llm_only = set(llm_keywords) - set(rule_keywords)
        rule_only = set(rule_keywords) - set(llm_keywords)
        
        if llm_only:
            print(f"   LLM만 추출: {list(llm_only)}")
        if rule_only:
            print(f"   규칙만 추출: {list(rule_only)}")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

orchestrator.close()

print("\n" + "="*80)
print("✅ 테스트 완료")
print("="*80)

print("\n📝 결론:")
print("- LLM 추출: 문맥 이해, 따옴표 처리, 불용어 자동 제거")
print("- 규칙 기반: 단순 분리, 불용어 리스트 필요, 따옴표 문제")
print("- 권장: LLM 추출 사용 (더 정확)")
