## A-1 정서 기반 취향 모델링

import argparse
import json
from typing import Dict, List

import movie_a_2


# 사용자 텍스트에서 취향 프로필 생성 (더미 버전)
# LLM 연동 후: 실제 감성 분석으로 대체
def build_user_profile(user_text: str, taxonomy: Dict) -> Dict:
    """
    사용자가 입력한 텍스트를 분석하여 취향 프로필 생성
    
    Args:
        user_text: 사용자 입력 ("저는 감동적이고 따뜻한 영화를 좋아해요")
        taxonomy: 정서 태그 분류 체계
    
    Returns:
        사용자 취향 프로필 (emotion_scores, narrative_traits, ending_preference)
    """
    e_keys = taxonomy['emotion']['tags']
    n_keys = taxonomy['story_flow']['tags']
    
    profile = {
        'user_text': user_text,
        'emotion_scores': movie_a_2.score_tags(user_text, e_keys),
        'narrative_traits': movie_a_2.score_tags(user_text, n_keys),
        'ending_preference': {
            'happy': movie_a_2.stable_score(user_text, 'ending_happy'),
            'open': movie_a_2.stable_score(user_text, 'ending_open'),
            'bittersweet': movie_a_2.stable_score(user_text, 'ending_bittersweet'),
        },
    }
    
    return profile


# 여러 사용자 텍스트를 받아서 프로필 병합
# 예: 리뷰 여러 개, SNS 포스트 여러 개
def build_user_profile_from_multiple(texts: List[str], taxonomy: Dict) -> Dict:
    """
    여러 텍스트를 종합하여 사용자 취향 프로필 생성
    
    Args:
        texts: 사용자가 작성한 여러 리뷰/코멘트
        taxonomy: 정서 태그 분류 체계
    
    Returns:
        평균 취향 프로필
    """
    if not texts:
        raise ValueError("At least one text is required")
    
    # 모든 텍스트를 합쳐서 분석
    combined_text = ' '.join(texts)
    return build_user_profile(combined_text, taxonomy)


# 선호/비선호 텍스트를 명시적으로 분리해서 분석
def build_user_profile_with_dislikes(likes: str, dislikes: str, taxonomy: Dict) -> Dict:
    """
    좋아하는 것과 싫어하는 것을 구분하여 프로필 생성
    
    Args:
        likes: "저는 감동적이고 따뜻한 영화 좋아해요"
        dislikes: "무섭고 잔인한 영화는 싫어요"
        taxonomy: 정서 태그 분류 체계
    
    Returns:
        선호도 프로필 + 비선호 태그 리스트
    """
    e_keys = taxonomy['emotion']['tags']
    n_keys = taxonomy['story_flow']['tags']
    
    # 선호 프로필
    profile = build_user_profile(likes, taxonomy)
    
    # 비선호 태그 추출 (간단한 키워드 매칭)
    dislike_tags = []
    if dislikes:
        dislike_scores = movie_a_2.score_tags(dislikes, e_keys)
        # 점수가 높은 태그들을 비선호 목록에 추가
        for tag, score in dislike_scores.items():
            if score > 0.6:  # 임계값
                dislike_tags.append(tag)
    
    profile['dislike_tags'] = dislike_tags
    
    return profile


# LLM 연동용 함수 (미구현)
def analyze_user_preference_with_llm(user_text: str, taxonomy: Dict) -> Dict:
    """
    LLM을 사용한 실제 사용자 취향 분석
    
    향후 구현:
    1. 프롬프트 생성
       "사용자가 다음과 같이 말했습니다: {user_text}
        이 사용자의 영화 취향을 분석해서 다음 정서 태그별 선호도를 0-1 점수로:
        {taxonomy['emotion']['tags']}"
    
    2. Claude/GPT API 호출
    
    3. JSON 파싱 및 반환
    """
    pass


def main():
    parser = argparse.ArgumentParser(description='A-1 User Preference Analysis (dummy LLM)')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-text', required=True, help='사용자 선호도 텍스트')
    parser.add_argument('--dislikes', default='', help='싫어하는 것 (선택)')
    parser.add_argument('--output', default=None, help='출력 파일 경로')
    parser.add_argument('--pretty', action='store_true', help='JSON 포맷팅')
    args = parser.parse_args()
    
    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    
    if args.dislikes:
        profile = build_user_profile_with_dislikes(args.user_text, args.dislikes, taxonomy)
    else:
        profile = build_user_profile(args.user_text, taxonomy)
    
    # 출력
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2 if args.pretty else None)
        print(f"User profile saved to {args.output}")
    else:
        print(json.dumps(profile, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == '__main__':
    main()