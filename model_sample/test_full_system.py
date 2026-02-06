"""
전체 시스템 검증 스크립트

A-3 (만족 확률) + A-5 (LLM 설명) 통합 시스템 테스트
"""

import json
import movie_a_2
import movie_a_3
import movie_a_5
import movie_preference_builder


def test_full_pipeline():
    """전체 파이프라인 테스트"""
    
    print("\n" + "="*60)
    print("🧪 전체 시스템 검증 시작")
    print("="*60)
    
    # 1. 데이터 로드
    print("\n📂 1단계: 데이터 로드")
    movies = movie_a_2.load_json('movies_small.json')
    taxonomy = movie_a_2.load_taxonomy('emotion_tag.json')
    print(f"   ✓ 영화 {len(movies)}개 로드")
    print(f"   ✓ 택소노미 로드 완료")
    
    # 2. 사용자 선호도 생성
    print("\n👤 2단계: 사용자 선호도 생성")
    liked_ids = [1306368]  # 더 립
    disliked_ids = [1242898]  # 프레데터
    
    preference = movie_preference_builder.build_user_preference_from_movies(
        liked_ids,
        disliked_ids,
        movies,
        taxonomy
    )
    
    print(f"   ✓ 좋아하는 태그: {len(preference['boost_tags'])}개")
    print(f"   ✓ 싫어하는 태그: {len(preference['penalty_tags'])}개")
    
    # 3. 영화 프로필 빌드
    print("\n🎬 3단계: 영화 프로필 빌드")
    test_movie = movies[0]
    movie_profile = movie_a_2.build_profile(test_movie, taxonomy)
    print(f"   ✓ 테스트 영화: {test_movie['title']}")
    print(f"   ✓ 감정 점수 키: {len(movie_profile['emotion_scores'])}개")
    
    # 4. 만족 확률 계산 (A-3)
    print("\n🔢 4단계: 만족 확률 계산 (A-3)")
    user_profile = {
        'emotion_scores': {},
        'narrative_traits': {},
        'ending_preference': {'happy': 0.5, 'open': 0.5, 'bittersweet': 0.5}
    }
    
    result = movie_a_3.calculate_satisfaction_probability(
        user_profile,
        movie_profile,
        dislikes=preference['penalty_tags'],
        boost_tags=preference['boost_tags'],
        boost_weight=0.6,
        penalty_weight=0.8
    )
    
    print(f"   ✓ 만족 확률: {result['probability']:.1%}")
    print(f"   ✓ 신뢰도: {result['confidence']:.1%}")
    print(f"   ✓ Raw Score: {result['raw_score']:.3f}")
    print(f"   ✓ Boost: +{result['breakdown']['boost_score']:.1f}")
    print(f"   ✓ Penalty: -{result['breakdown']['dislike_penalty']:.1f}")
    
    # 5. LLM 설명 생성 (A-5)
    print("\n📝 5단계: LLM 설명 생성 (A-5)")
    bedrock_client = movie_a_5.get_bedrock_client()
    
    explanation = movie_a_5.generate_explanation(
        prediction_result=result,
        movie_title=test_movie['title'],
        user_liked_tags=preference['boost_tags'][:5],
        user_disliked_tags=preference['penalty_tags'][:5],
        bedrock_client=bedrock_client
    )
    
    print(f"   ✓ 설명 생성 완료")
    print(f"\n   {explanation}\n")
    
    # 6. 최종 결과
    print("="*60)
    print("✅ 전체 시스템 검증 완료!")
    print("="*60)
    
    final_result = {
        "movie": test_movie['title'],
        "satisfaction_probability": f"{result['probability']:.1%}",
        "confidence": f"{result['confidence']:.1%}",
        "explanation": explanation,
        "breakdown": {
            "boost_score": round(result['breakdown']['boost_score'], 1),
            "dislike_penalty": round(result['breakdown']['dislike_penalty'], 1),
            "top_factors": result['breakdown']['top_factors']
        }
    }
    
    print("\n📊 최종 출력 (JSON):")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))
    
    return final_result


if __name__ == '__main__':
    test_full_pipeline()
