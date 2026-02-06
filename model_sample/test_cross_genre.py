"""
장르 간 추천 알고리즘 테스트 스크립트

사용자 선호 장르를 추출하고, 70% 같은 장르 + 30% 다른 장르 믹싱 추천
"""

import argparse
import json
from typing import Dict, List

import movie_a_2
import movie_a_3
import movie_a_7
import movie_preference_builder


def test_cross_genre_recommendation(
    user_id: str,
    movies_data: List[Dict],
    taxonomy: Dict,
    liked_movie_ids: List[str],
    limit: int = 10,
    bedrock_client=None
):
    """
    장르 간 추천 테스트
    
    Args:
        user_id: 사용자 ID
        movies_data: 전체 영화 데이터
        taxonomy: emotion_tag.json
        liked_movie_ids: 좋아하는 영화 ID 리스트
        limit: 추천 영화 개수
        bedrock_client: Bedrock 클라이언트
    """
    print(f"\n{'='*60}")
    print(f"🎬 장르 간 추천 알고리즘 테스트 (중복 방지)")
    print(f"{'='*60}\n")
    
    # 1. 사용자 선호도 로드
    preference = movie_preference_builder.load_user_preference(user_id)
    boost_tags = preference.get("boost_tags", [])
    penalty_tags = preference.get("penalty_tags", [])
    
    print(f"사용자: {user_id}")
    print(f"좋아하는 태그: {len(boost_tags)}개")
    print(f"싫어하는 태그: {len(penalty_tags)}개\n")
    
    # 2. 선호 장르 추출
    preferred_genres = movie_a_7.extract_user_genres(liked_movie_ids, movies_data)
    
    print(f"{'='*60}")
    print(f"📊 선호 장르 추출 결과")
    print(f"{'='*60}")
    
    if preferred_genres:
        print(f"선호 장르 (순서대로): {preferred_genres}")
        
        # 좋아하는 영화 표시
        liked_movies = [m for m in movies_data if str(m.get('id')) in liked_movie_ids or m.get('id') in liked_movie_ids]
        print(f"\n좋아하는 영화:")
        for m in liked_movies:
            print(f"  - {m.get('title')} ({', '.join(m.get('genres', []))})")
    else:
        print("선호 장르를 찾을 수 없습니다.")
    
    print(f"\n{'='*60}")
    print(f"📊 만족 확률 계산 중...")
    print(f"{'='*60}\n")
    
    # 3. 간단한 사용자 프로필 생성
    user_profile = {
        'emotion_scores': {},
        'narrative_traits': {},
        'ending_preference': {
            'happy': 0.5,
            'open': 0.5,
            'bittersweet': 0.5
        }
    }
    
    # 4. 각 영화에 대해 만족 확률 계산
    scored_movies = []
    
    for m in movies_data:
        # 이미 좋아하는 영화는 제외
        if str(m.get('id')) in liked_movie_ids or m.get('id') in liked_movie_ids:
            continue
        
        mp = movie_a_2.build_profile(m, taxonomy, bedrock_client)
        
        result = movie_a_3.calculate_satisfaction_probability(
            user_profile,
            mp,
            dislikes=penalty_tags,
            boost_tags=boost_tags,
            boost_weight=0.6,
            penalty_weight=0.8
        )
        
        scored_movies.append({
            'movie': m,
            'movie_id': m.get('id'),  # 중복 방지를 위한 ID
            'title': m.get('title'),
            'genres': m.get('genres', []),
            'score': result['probability'],
            'confidence': result['confidence'],
            'breakdown': result['breakdown']
        })
        
        print(f"  ✓ {m.get('title')}: {result['probability']:.3f}")
    
    # 5. 장르 간 추천 알고리즘 적용
    print(f"\n{'='*60}")
    print(f"🎯 장르 간 추천 알고리즘 적용 (중복 방지)")
    print(f"{'='*60}")
    print(f"각 선호 장르에서 순서대로 최고 점수 영화를 선택")
    print(f"이미 추천한 영화는 제외\n")
    
    recommendations = movie_a_7.cross_genre_recommendation(
        scored_movies,
        preferred_genres,
        limit=limit
    )
    
    # 6. 결과 출력
    print(f"{'='*60}")
    print(f"🎬 추천 영화 Top {len(recommendations)}")
    print(f"{'='*60}\n")
    
    # 중복 체크
    seen_ids = set()
    duplicates = []
    
    for i, item in enumerate(recommendations, 1):
        movie_id = item.get('movie_id')
        genres_str = ', '.join(item['genres'])
        
        # 중복 확인
        if movie_id in seen_ids:
            duplicates.append(f"영화 ID {movie_id}: {item['title']}")
        seen_ids.add(movie_id)
        
        # 어떤 장르에서 선택되었는지 표시
        selected_from_genre = None
        for genre in item['genres']:
            if genre in preferred_genres:
                selected_from_genre = genre
                break
        
        genre_info = f"✅ {selected_from_genre}에서 선택" if selected_from_genre else "🔀 기타"
        
        print(f"{i}. {item['title']}")
        print(f"   장르: {genres_str}")
        print(f"   선택: {genre_info}")
        print(f"   만족 확률: {item['score']:.1%}")
        print(f"   [신뢰도: {item['confidence']:.1%}]")
        print()
    
    # 7. 중복 검증
    print(f"{'='*60}")
    print(f"🔍 중복 검증")
    print(f"{'='*60}")
    
    if duplicates:
        print(f"❌ 중복 발견! ({len(duplicates)}개)")
        for dup in duplicates:
            print(f"  - {dup}")
    else:
        print(f"✅ 중복 없음! 모든 추천 영화가 고유합니다.")
    
    print(f"\n총 {len(recommendations)}개 영화 추천 완료")
    print(f"{'='*60}\n")
    
    return recommendations


def main():
    parser = argparse.ArgumentParser(description='장르 간 추천 알고리즘 테스트 (중복 방지)')
    parser.add_argument('--user-id', default='user_test')
    parser.add_argument('--movies', default='movies_small.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--liked-movies', nargs='+', default=['1306368', '1084242'],
                        help='좋아하는 영화 ID 리스트')
    parser.add_argument('--limit', type=int, default=10)
    
    args = parser.parse_args()
    
    # 데이터 로드
    movies = movie_a_2.load_json(args.movies)
    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    bedrock_client = movie_a_2.get_bedrock_client()
    
    # 테스트 실행
    recommendations = test_cross_genre_recommendation(
        args.user_id,
        movies,
        taxonomy,
        args.liked_movies,
        args.limit,
        bedrock_client
    )


if __name__ == '__main__':
    main()
