## A-4 설명 가능한 취향 추천 (LLM)

import argparse
import json
from typing import Dict, List, Tuple

import movie_a_2


# 주요 기여 요소 추출
# 사용자 프로필과 영화 프로필을 비교하여 매칭에 가장 큰 영향을 준 요소 찾기
def find_top_contributors(
    user_profile: Dict,
    movie_profile: Dict,
    top_n: int = 3
) -> List[Tuple[str, str, float]]:
    """
    사용자-영화 매칭에서 가장 큰 기여를 한 정서 태그 찾기
    
    Args:
        user_profile: 사용자 취향 프로필
        movie_profile: 영화 프로필
        top_n: 상위 N개 추출
    
    Returns:
        [(category, tag, contribution_score), ...]
        예: [('emotion', '감동적이에요', 0.85), ('story_flow', '반전이 있어요', 0.72)]
    """
    contributors = []
    
    # Emotion scores 비교
    for tag in user_profile.get('emotion_scores', {}):
        user_score = user_profile['emotion_scores'].get(tag, 0.0)
        movie_score = movie_profile['emotion_scores'].get(tag, 0.0)
        # 둘 다 높으면 기여도가 높음 (곱셈)
        contribution = user_score * movie_score
        if contribution > 0.1:  # 최소 임계값
            contributors.append(('emotion', tag, contribution))
    
    # Narrative traits 비교
    for tag in user_profile.get('narrative_traits', {}):
        user_score = user_profile['narrative_traits'].get(tag, 0.0)
        movie_score = movie_profile['narrative_traits'].get(tag, 0.0)
        contribution = user_score * movie_score
        if contribution > 0.1:
            contributors.append(('story_flow', tag, contribution))
    
    # Ending preference 비교
    for tag in user_profile.get('ending_preference', {}):
        user_score = user_profile['ending_preference'].get(tag, 0.0)
        movie_score = movie_profile['ending_preference'].get(tag, 0.0)
        contribution = user_score * movie_score
        if contribution > 0.1:
            contributors.append(('ending', tag, contribution))
    
    # 기여도 순으로 정렬하여 상위 N개 반환
    contributors.sort(key=lambda x: x[2], reverse=True)
    return contributors[:top_n]


# 설명 생성 (더미 LLM)
def generate_explanation(
    movie_title: str,
    match_rate: float,
    contributors: List[Tuple[str, str, float]],
    use_llm: bool = False
) -> Dict:
    """
    추천 이유 설명 생성
    
    Args:
        movie_title: 영화 제목
        match_rate: 매칭률 (0-100)
        contributors: 주요 기여 요소 리스트
        use_llm: 실제 LLM 사용 여부 (향후 구현)
    
    Returns:
        설명 텍스트 + 주의사항
    """
    if use_llm:
        # 향후 LLM API 연동
        # prompt = f"다음 영화를 추천합니다: {movie_title}, 매칭률: {match_rate}%..."
        # explanation = call_llm_api(prompt)
        pass
    
    # 더미 버전: 템플릿 기반 설명 생성
    reasons = []
    for category, tag, score in contributors:
        if category == 'emotion':
            reasons.append(f"이 영화는 '{tag}' 감성이 강해서")
        elif category == 'story_flow':
            reasons.append(f"'{tag}' 서사 구조가 있어서")
        elif category == 'ending':
            reasons.append(f"'{tag}' 결말을 가지고 있어서")
    
    if not reasons:
        reasons.append("다양한 정서적 요소가 잘 맞아서")
    
    explanation_text = f"'{movie_title}'를 추천합니다 (매칭률: {match_rate:.1f}%). "
    explanation_text += ", ".join(reasons[:3])
    explanation_text += " 귀하의 취향과 잘 맞을 것으로 예상됩니다."
    
    return {
        'movie_title': movie_title,
        'match_rate': round(match_rate, 2),
        'explanation': explanation_text,
        'key_factors': [
            {'category': cat, 'tag': tag, 'score': round(score, 3)}
            for cat, tag, score in contributors
        ],
        'disclaimer': '이 추천은 정서 태그 기반 확률적 분석이며, 개인의 주관적 취향과 다를 수 있습니다.'
    }


# LLM 기반 설명 생성 (미구현 - 향후 구현)
def generate_explanation_with_llm(
    movie_title: str,
    match_rate: float,
    contributors: List[Tuple[str, str, float]],
    user_text: str
) -> str:
    """
    실제 LLM을 사용한 자연스러운 설명 생성
    
    향후 구현:
    1. 프롬프트 구성
       - 사용자 입력: {user_text}
       - 영화: {movie_title}
       - 매칭률: {match_rate}
       - 주요 요소: {contributors}
    
    2. LLM API 호출 (Claude, GPT 등)
    
    3. 응답 파싱 및 검증
    
    4. 설명 반환
    """
    # 프롬프트 예시
    prompt = f"""
    사용자가 "{user_text}"라고 말했습니다.
    
    영화 "{movie_title}"의 매칭률은 {match_rate}%입니다.
    
    주요 매칭 요소:
    {', '.join([f"{tag}({cat})" for cat, tag, _ in contributors])}
    
    이 영화를 추천하는 이유를 2-3문장으로 자연스럽게 설명해주세요.
    친근하고 따뜻한 톤으로 작성하되, 과장하지 마세요.
    """
    
    # TODO: LLM API 호출
    # response = llm_api.generate(prompt)
    # return response.text
    
    return "[LLM 미구현 - 향후 추가 예정]"


# CLI 메인 함수
def main():
    parser = argparse.ArgumentParser(description='A-4 Explainable Recommendation (LLM explanation)')
    parser.add_argument('--movies', default='movies_dataset_final.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-text', required=True, help='사용자 취향 텍스트')
    parser.add_argument('--movie-id', required=True, help='설명할 영화 ID')
    parser.add_argument('--top-factors', type=int, default=3, help='주요 기여 요소 개수')
    parser.add_argument('--use-llm', action='store_true', help='LLM 사용 (미구현)')
    args = parser.parse_args()
    
    # 데이터 로드
    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    movies = movie_a_2.load_json(args.movies)
    
    # 특정 영화 찾기
    target_movie = None
    for m in movies:
        if str(m.get('id')) == str(args.movie_id):
            target_movie = m
            break
    
    if not target_movie:
        print(json.dumps({'error': f'Movie ID {args.movie_id} not found'}, ensure_ascii=False))
        return
    
    # 사용자 프로필 생성
    e_keys = taxonomy['emotion']['tags']
    n_keys = taxonomy['story_flow']['tags']
    
    user_profile = {
        'emotion_scores': movie_a_2.score_tags(args.user_text, e_keys),
        'narrative_traits': movie_a_2.score_tags(args.user_text, n_keys),
        'ending_preference': {
            'happy': movie_a_2.stable_score(args.user_text, 'ending_happy'),
            'open': movie_a_2.stable_score(args.user_text, 'ending_open'),
            'bittersweet': movie_a_2.stable_score(args.user_text, 'ending_bittersweet'),
        },
    }
    
    # 영화 프로필 생성
    movie_profile = movie_a_2.build_profile(target_movie, taxonomy)
    
    # 매칭률 계산 (간단한 코사인 유사도)
    from movie_a_3 import cosine_sim, align_vector
    
    e_sim = cosine_sim(
        align_vector(user_profile['emotion_scores'], e_keys),
        align_vector(movie_profile['emotion_scores'], e_keys)
    )
    n_sim = cosine_sim(
        align_vector(user_profile['narrative_traits'], n_keys),
        align_vector(movie_profile['narrative_traits'], n_keys)
    )
    
    # 가중 평균 매칭률
    match_rate = (0.6 * e_sim + 0.4 * n_sim) * 100
    
    # 주요 기여 요소 추출
    contributors = find_top_contributors(user_profile, movie_profile, args.top_factors)
    
    # 설명 생성
    explanation = generate_explanation(
        target_movie.get('title', 'Unknown'),
        match_rate,
        contributors,
        use_llm=args.use_llm
    )
    
    # 출력
    print(json.dumps(explanation, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
