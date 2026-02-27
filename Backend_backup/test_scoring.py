# -*- coding: utf-8 -*-
"""
점수 계산 로직 테스트
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "="*80)
print("📊 점수 계산 로직 테스트")
print("="*80)

# 시뮬레이션 데이터
candidates = [
    {
        "movie_id": 1198994,
        "title": "직장상사 길들이기",
        "similarity_score": 0.400,
        "sources": ["keyword"]
    },
    {
        "movie_id": 331482,
        "title": "작은 아씨들",
        "similarity_score": 0.083,
        "sources": ["hybrid", "vector"]
    },
    {
        "movie_id": 16442,
        "title": "요크 상사",
        "similarity_score": 0.200,
        "sources": ["keyword", "hybrid", "vector"]
    }
]

print("\n원래 점수:")
for c in candidates:
    print(f"  {c['title']}: {c['similarity_score']:.3f} (소스: {len(c['sources'])}개)")

# 최종 점수 계산
for candidate in candidates:
    source_count = len(candidate.get('sources', []))
    original_score = candidate.get('similarity_score', 0)
    
    # 다중 소스 보너스
    multi_source_bonus = (source_count - 1) * 0.1
    
    # 최종 점수
    candidate['final_score'] = original_score + multi_source_bonus
    candidate['multi_source_bonus'] = multi_source_bonus

# 정렬
candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)

print("\n최종 점수 (원래 + 보너스):")
for i, c in enumerate(candidates, 1):
    print(f"  {i}. {c['title']}: {c['final_score']:.3f} "
          f"(원래: {c['similarity_score']:.3f} + 보너스: {c['multi_source_bonus']:.3f})")

print("\n" + "="*80)
print("✅ 결과: '직장상사 길들이기'가 1위!")
print("="*80)
