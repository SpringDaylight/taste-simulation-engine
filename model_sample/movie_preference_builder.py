"""
영화 선택 기반 세부 취향 추출 모듈

사용자가 좋아하는/싫어하는 영화를 선택하면,
해당 영화의 세부 태그를 추출하여 가중치를 적용합니다.
"""

import json
from typing import Dict, List
import movie_a_2


def extract_tags_from_movie(movie_profile: Dict) -> List[str]:
    """
    영화 프로필에서 주요 태그 추출
    
    Args:
        movie_profile: build_profile로 생성된 영화 프로필
    
    Returns:
        태그 리스트 (점수 0.5 이상만 추출)
    """
    tags = []
    
    # 모든 카테고리에서 높은 점수의 태그 추출
    categories = ['emotion_scores', 'narrative_traits', 'direction_mood', 'character_relationship']
    
    for category in categories:
        if category in movie_profile:
            for tag, score in movie_profile[category].items():
                if score >= 0.5:  # 임계값: 0.5 이상만 의미 있는 태그로 간주
                    tags.append(tag)
    
    return tags


def build_user_preference_from_movies(
    liked_movie_ids: List[int],
    disliked_movie_ids: List[int],
    movies_data: List[Dict],
    taxonomy: Dict,
    bedrock_client=None
) -> Dict:
    """
    좋아하는/싫어하는 영화 ID 리스트로부터 사용자 취향 생성
    
    Args:
        liked_movie_ids: 좋아하는 영화 ID 리스트
        disliked_movie_ids: 싫어하는 영화 ID 리스트
        movies_data: 전체 영화 데이터
        taxonomy: emotion_tag.json
        bedrock_client: Bedrock 클라이언트 (선택)
    
    Returns:
        {
            "boost_tags": [...],  # 좋아하는 영화에서 추출된 태그
            "penalty_tags": [...] # 싫어하는 영화에서 추출된 태그
        }
    """
    # 영화 ID → 영화 객체 매핑
    movie_map = {m['id']: m for m in movies_data}
    
    boost_tags = []
    penalty_tags = []
    
    # 좋아하는 영화에서 태그 추출
    print(f"\n📌 좋아하는 영화 분석 중...")
    for movie_id in liked_movie_ids:
        if movie_id in movie_map:
            movie = movie_map[movie_id]
            print(f"  ✓ {movie.get('title')}")
            
            # 영화 프로필 생성
            profile = movie_a_2.build_profile(movie, taxonomy, bedrock_client)
            
            # 세부 태그 추출
            tags = extract_tags_from_movie(profile)
            boost_tags.extend(tags)
            print(f"    추출된 태그: {tags[:5]}...")  # 일부만 출력
    
    # 싫어하는 영화에서 태그 추출
    print(f"\n📌 싫어하는 영화 분석 중...")
    for movie_id in disliked_movie_ids:
        if movie_id in movie_map:
            movie = movie_map[movie_id]
            print(f"  ✗ {movie.get('title')}")
            
            # 영화 프로필 생성
            profile = movie_a_2.build_profile(movie, taxonomy, bedrock_client)
            
            # 세부 태그 추출
            tags = extract_tags_from_movie(profile)
            penalty_tags.extend(tags)
            print(f"    추출된 태그: {tags[:5]}...")  # 일부만 출력
    
    # 중복 제거 및 빈도 기반 필터링
    from collections import Counter
    
    boost_counter = Counter(boost_tags)
    penalty_counter = Counter(penalty_tags)
    
    # 최소 2번 이상 등장한 태그만 유지 (노이즈 제거)
    filtered_boost = [tag for tag, count in boost_counter.items() if count >= 1]
    filtered_penalty = [tag for tag, count in penalty_counter.items() if count >= 1]
    
    print(f"\n✅ 추출 완료!")
    print(f"   좋아하는 태그 ({len(filtered_boost)}개): {filtered_boost[:10]}")
    print(f"   싫어하는 태그 ({len(filtered_penalty)}개): {filtered_penalty[:10]}")
    
    return {
        "boost_tags": filtered_boost,
        "penalty_tags": filtered_penalty,
        "boost_tag_frequency": dict(boost_counter),
        "penalty_tag_frequency": dict(penalty_counter)
    }


def save_user_preference(user_id: str, preference: Dict, output_file: str = "user_preferences.json"):
    """
    사용자 취향을 JSON 파일로 저장 (데이터베이스 대신)
    
    Args:
        user_id: 사용자 ID
        preference: build_user_preference_from_movies의 결과
        output_file: 저장할 파일 경로
    """
    try:
        # 기존 파일 로드
        with open(output_file, 'r', encoding='utf-8') as f:
            all_prefs = json.load(f)
    except FileNotFoundError:
        all_prefs = {}
    
    # 사용자 취향 업데이트
    all_prefs[user_id] = preference
    
    # 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_prefs, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 사용자 취향 저장 완료: {output_file}")


def load_user_preference(user_id: str, input_file: str = "user_preferences.json") -> Dict:
    """
    저장된 사용자 취향 불러오기
    
    Args:
        user_id: 사용자 ID
        input_file: 파일 경로
    
    Returns:
        사용자 취향 딕셔너리
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            all_prefs = json.load(f)
        return all_prefs.get(user_id, {"boost_tags": [], "penalty_tags": []})
    except FileNotFoundError:
        print(f"⚠️  파일을 찾을 수 없습니다: {input_file}")
        return {"boost_tags": [], "penalty_tags": []}


# CLI 테스트
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='영화 선택으로 취향 생성')
    parser.add_argument('--liked', help='좋아하는 영화 ID (쉼표 구분)', required=True)
    parser.add_argument('--disliked', help='싫어하는 영화 ID (쉼표 구분)', required=True)
    parser.add_argument('--movies', default='movies_dataset_final.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-id', default='user_001')
    parser.add_argument('--output', default='user_preferences.json')
    
    args = parser.parse_args()
    
    # 영화 ID 파싱
    liked_ids = [int(x.strip()) for x in args.liked.split(',')]
    disliked_ids = [int(x.strip()) for x in args.disliked.split(',')]
    
    # 데이터 로드
    movies = movie_a_2.load_json(args.movies)
    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    bedrock_client = movie_a_2.get_bedrock_client()
    
    # 취향 생성
    preference = build_user_preference_from_movies(
        liked_ids,
        disliked_ids,
        movies,
        taxonomy,
        bedrock_client
    )
    
    # 저장
    save_user_preference(args.user_id, preference, args.output)
    
    print("\n" + "="*60)
    print(f"사용자 '{args.user_id}'의 취향이 생성되었습니다!")
    print("="*60)
