"""
사용자 취향 기반 영화 추천 테스트 스크립트

좋아하는/싫어하는 영화를 선택한 사용자에게 영화를 추천합니다.
"""

import argparse
import json
from typing import Dict, List

import movie_a_2
import movie_a_3
import movie_preference_builder


def recommend_with_preference(
    user_id: str,
    movies_data: List[Dict],
    taxonomy: Dict,
    bedrock_client=None,
    limit: int = 5
):
    """
    사용자 선호도를 기반으로 영화 추천
    
    Args:
        user_id: 사용자 ID
        movies_data: 전체 영화 데이터
        taxonomy: emotion_tag.json
        bedrock_client: Bedrock 클라이언트
        limit: 추천 영화 개수
    """
    # 1. 사용자 선호도 로드
    preference = movie_preference_builder.load_user_preference(user_id)
    
    boost_tags = preference.get("boost_tags", [])
    penalty_tags = preference.get("penalty_tags", [])
    
    print(f"\n{'='*60}")
    print(f"사용자: {user_id}")
    print(f"{'='*60}")
    print(f"✅ 좋아하는 태그 ({len(boost_tags)}개):")
    print(f"   {boost_tags[:10]}...")
    print(f"❌ 싫어하는 태그 ({len(penalty_tags)}개):")
    print(f"   {penalty_tags[:10]}...")
    print(f"{'='*60}\n")
    
    # 2. 간단한 사용자 프로필 생성 (기본 벡터)
    # 실제로는 A-1으로 생성하지만, 여기서는 기본값 사용
    user_profile = {
        'emotion_scores': {},
        'narrative_traits': {},
        'ending_preference': {
            'happy': 0.5,
            'open': 0.5,
            'bittersweet': 0.5
        }
    }
    
    # 3. 각 영화에 대해 만족 확률 계산
    scored = []
    print("📊 영화 평가 중...")
    
    for m in movies_data:
        mp = movie_a_2.build_profile(m, taxonomy, bedrock_client)
        
        #좋아하는/싫어하는 태그를 반영한 확률 계산
        result = movie_a_3.calculate_satisfaction_probability(
            user_profile,
            mp,
            dislikes=penalty_tags,  # 싫어하는 태그
            boost_tags=boost_tags,   # 좋아하는 태그
            boost_weight=0.6,  # 좋아하는 것 가중치
            penalty_weight=0.8  # 싫어하는 것 가중치
        )
        
        scored.append({
            'movie_id': m.get('id'),
            'title': m.get('title'),
            'satisfaction_probability': result['probability'],
            'confidence': result['confidence'],
            'raw_score': result['raw_score'],
            'breakdown': result['breakdown']
        })
        
        print(f"  ✓ {m.get('title')}: {result['probability']:.3f}")
    
    # 4. 정렬 및 상위 N개 반환
    scored.sort(key=lambda x: x['satisfaction_probability'], reverse=True)
    
    print(f"\n{'='*60}")
    print(f"🎬 추천 영화 Top {limit}")
    print(f"{'='*60}\n")
    
    # A-5: LLM 설명 생성 추가
    import movie_a_5
    bedrock_client = movie_a_5.get_bedrock_client()
    
    for i, movie in enumerate(scored[:limit], 1):
        # LLM 설명 생성
        explanation = movie_a_5.generate_explanation(
            prediction_result={
                "probability": movie['satisfaction_probability'],
                "confidence": movie['confidence'],
                "breakdown": movie['breakdown']
            },
            movie_title=movie['title'],
            user_liked_tags=boost_tags[:5] if boost_tags else [],
            user_disliked_tags=penalty_tags[:5] if penalty_tags else [],
            bedrock_client=bedrock_client
        )
        
        print(f"{i}. {movie['title']}")
        print(f"   만족 확률: {movie['satisfaction_probability']:.1%}")
        print(f"   📝 {explanation}")
        print(f"   [신뢰도: {movie['confidence']:.1%}, ")
        print(f"    좋아하는 것: +{movie['breakdown']['boost_score']:.1f}, ")
        print(f"    싫어하는 것: -{movie['breakdown']['dislike_penalty']:.1f}]\n")
    
    return scored[:limit]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='사용자 취향 기반 영화 추천')
    parser.add_argument('--user-id', default='user_test')
    parser.add_argument('--movies', default='movies_small.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--limit', type=int, default=5)
    
    args = parser.parse_args()
    
    # 데이터 로드
    movies = movie_a_2.load_json(args.movies)
    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    bedrock_client = movie_a_2.get_bedrock_client()
    
    # 추천 실행
    recommendations = recommend_with_preference(
        args.user_id,
        movies,
        taxonomy,
        bedrock_client,
        args.limit
    )
