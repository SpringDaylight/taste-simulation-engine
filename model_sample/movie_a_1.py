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


# ============================================================
# 부정어 처리 시스템 (The Negation Problem 해결)
# ============================================================

def extract_negative_filters_with_llm(user_text: str, bedrock_client=None) -> Dict:
    """
    LLM을 사용하여 사용자 입력에서 제외 조건 추출 (메인 방식)
    
    Problem: "무서운 거 싫어" → 키워드 매칭 시 "무서운" 감지 → 공포 영화 추천 (잘못됨!)
    Solution: LLM으로 부정 의도 파악 → exclude_tags에 추가 → 필터링
    
    Args:
        user_text: "무서운 거 싫어. 로맨스 좋아해요"
        bedrock_client: AWS Bedrock client (None이면 자동 생성)
    
    Returns:
        {
            "exclude_genres": ["Horror", "Thriller"],
            "exclude_tags": ["무서워요", "소름 돋아요"],
            "include_genres": ["Romance"],
            "include_tags": ["로맨틱해요", "설레요"]
        }
    """
    import os
    import json
    import boto3
    from dotenv import load_dotenv
    
    # 환경 변수 로드
    load_dotenv()
    
    # Bedrock 클라이언트 생성
    if bedrock_client is None:
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'ap-northeast-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    
    # 프롬프트 생성
    prompt = f"""당신은 영화 추천 시스템의 사용자 의도 파서입니다.

사용자 입력: "{user_text}"

이 텍스트에서 다음을 정확히 추출해주세요:

1. **싫어하는/제외하고 싶은** 장르나 감정 태그 (부정어: "싫어", "제외", "말고", "빼고" 등과 함께 언급된 것)
2. **좋아하는/포함하고 싶은** 장르나 감정 태그 (긍정어: "좋아", "원해", "보고싶어" 등과 함께 언급된 것)

다음 장르 목록을 참고하세요:
- 액션(Action), 코미디(Comedy), 드라마(Drama), 로맨스(Romance), 공포(Horror), 스릴러(Thriller), SF(SF), 애니메이션(Animation)

다음 태그 목록을 참고하세요:
- 감정: 감동적이에요, 무서워요, 소름 돋아요, 슬퍼요, 웃겨요, 로맨틱해요, 긴장돼요, 통쾌해요, 우울해요
- 서사: 반전이 많아요, 전개가 빨라요, 기승전결이 뚜렷해요

**중요**: 반드시 JSON 형식으로만 답변하세요. 설명 없이 JSON만 출력하세요.

{{
    "exclude_genres": ["제외할 장르들"],
    "exclude_tags": ["제외할 태그들"],
    "include_genres": ["포함할 장르들"],
    "include_tags": ["포함할 태그들"]
}}

예시:
입력: "무서운 거 싫어. 로맨스 좋아"
출력: {{"exclude_genres": ["Horror"], "exclude_tags": ["무서워요", "소름 돋아요"], "include_genres": ["Romance"], "include_tags": ["로맨틱해요", "설레요"]}}
"""
    
    # Bedrock 호출
    try:
        response = bedrock_client.invoke_model(
            modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": int(os.getenv('BEDROCK_MAX_TOKENS', 512)),
                "temperature": float(os.getenv('BEDROCK_TEMPERATURE', 0.1)),
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            })
        )
        
        # 응답 파싱
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # JSON 추출 (LLM이 설명을 붙일 수 있으므로 JSON만 추출)
        import re
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            filters = json.loads(json_match.group(0))
        else:
            filters = json.loads(content)
        
        # 기본값 설정
        return {
            "exclude_genres": filters.get("exclude_genres", []),
            "exclude_tags": filters.get("exclude_tags", []),
            "include_genres": filters.get("include_genres", []),
            "include_tags": filters.get("include_tags", [])
        }
    
    except Exception as e:
        print(f"⚠️ LLM 부정어 추출 실패: {e}")
        print("   → 규칙 기반 백업 사용")
        
        # Fallback: 규칙 기반 부정어 검출
        return detect_negation_fallback(user_text)


def detect_negation_fallback(text: str) -> Dict:
    """
    LLM 실패 시 백업용 규칙 기반 부정어 검출 (개선 v3)
    
    개선점 v3:
    - 부분 문자열 매칭 강화 ("무섭거나" → "무서" 감지)
    - 연결어 처리 ("거나", "하거나")
    - 부정어/긍정어 키워드 확장
    - 더 정확한 문맥 파싱
    
    Args:
        text: 사용자 입력
    
    Returns:
        필터 딕셔너리
    """
    NEGATION_KEYWORDS = [
        "싫어", "제외", "말고", "빼고", "아니", "안", "싫다", 
        "NO", "No", "싫고", "제거", "거부", "없이", "빼"
    ]
    POSITIVE_KEYWORDS = [
        "좋아", "추천", "원해", "보고싶", "찾", "선호", "좋다", "원함"
    ]
    
    GENRE_MAP = {
        "무서": "Horror",
        "공포": "Horror",
        "호러": "Horror",
        "스릴": "Thriller",
        "액션": "Action",
        "코미디": "Comedy",
        "코메디": "Comedy",
        "로맨": "Romance",
        "드라마": "Drama",
        "SF": "SF",
        "애니": "Animation",
        "판타지": "Fantasy",
        "다큐": "Documentary",
    }
    TAG_MAP = {
        "무서": "무서워요",
        "공포": "무서워요",
        "소름": "소름 돋아요",
        "슬프": "슬퍼요",
        "우울": "우울해요",
        "긴장": "긴장돼요",
        "감동": "감동적이에요",
        "어두": "어두운 분위기예요",
        "반전": "반전이 많아요",
        "웃": "웃겨요",
        "밝": "밝은 분위기예요",
        "잔인": "잔인해요",
        "폭력": "폭력적이에요",
    }
    
    exclude_genres = []
    exclude_tags = []
    include_genres = []
    include_tags = []
    
    # 텍스트 전처리: "거나", "하거나" → "," 로 변환
    import re
    text = re.sub(r'[하]?거나', ',', text)
    
    # 문장을 마침표/쉼표로 분리
    sentences = re.split(r'[.。,]', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        has_negation = any(neg in sentence for neg in NEGATION_KEYWORDS)
        has_positive = any(pos in sentence for pos in POSITIVE_KEYWORDS)
        
        # 케이스 1: 부정어만 있음 → 제외 목록
        if has_negation and not has_positive:
            # 개선: 부분 매칭으로 모든 키워드 검사
            for keyword, genre in GENRE_MAP.items():
                # "무서" in "무섭거나" → True
                if keyword in sentence and genre not in exclude_genres:
                    exclude_genres.append(genre)
            
            for keyword, tag in TAG_MAP.items():
                if keyword in sentence and tag not in exclude_tags:
                    exclude_tags.append(tag)
        
        # 케이스 2: 긍정어만 있음 → 포함 목록
        elif has_positive and not has_negation:
            for keyword, genre in GENRE_MAP.items():
                if keyword in sentence and genre not in include_genres:
                    include_genres.append(genre)
            
            for keyword, tag in TAG_MAP.items():
                if keyword in sentence and tag not in include_tags:
                    include_tags.append(tag)
        
        # 케이스 3: 부정어와 긍정어 둘 다 있음 (복잡)
        # "A 말고 B" → A 제외, B 포함
        elif has_negation and has_positive:
            # 부정어 위치 찾기
            neg_positions = []
            for neg in NEGATION_KEYWORDS:
                if neg in sentence:
                    pos = sentence.find(neg)
                    if pos != -1:
                        neg_positions.append(pos)
            
            # 긍정어 위치 찾기
            pos_positions = []
            for pos in POSITIVE_KEYWORDS:
                if pos in sentence:
                    pos_idx = sentence.find(pos)
                    if pos_idx != -1:
                        pos_positions.append(pos_idx)
            
            if neg_positions and pos_positions:
                min_neg_pos = min(neg_positions)
                max_pos_pos = max(pos_positions)
                
                # 부정어 앞 부분 → 제외 (부분 매칭)
                before_neg = sentence[:min_neg_pos]
                for keyword, genre in GENRE_MAP.items():
                    if keyword in before_neg and genre not in exclude_genres:
                        exclude_genres.append(genre)
                for keyword, tag in TAG_MAP.items():
                    if keyword in before_neg and tag not in exclude_tags:
                        exclude_tags.append(tag)
                
                # 긍정어 주변 부분 → 포함 (부분 매칭)
                around_pos = sentence[max_pos_pos-10:max_pos_pos+20]
                for keyword, genre in GENRE_MAP.items():
                    if keyword in around_pos and genre not in include_genres:
                        include_genres.append(genre)
                for keyword, tag in TAG_MAP.items():
                    if keyword in around_pos and tag not in include_tags:
                        include_tags.append(tag)
    
    # 포함 목록에 있는 것은 제외 목록에서 제거
    exclude_genres = [g for g in exclude_genres if g not in include_genres]
    exclude_tags = [t for t in exclude_tags if t not in include_tags]
    
    return {
        "exclude_genres": exclude_genres,
        "exclude_tags": exclude_tags,
        "include_genres": include_genres,
        "include_tags": include_tags
    }


def build_user_profile_with_negation(user_text: str, taxonomy: Dict, bedrock_client=None) -> Dict:
    """
    부정어 처리를 적용한 사용자 프로필 생성 (A-1 개선 버전)
    
    우선순위:
    1. LLM으로 부정/긍정 의도 파싱 시도
    2. 실패 시 자동으로 규칙 기반 백업 사용
    
    Args:
        user_text: 사용자 입력 ("무서운 거 싫어. 로맨스 좋아해요")
        taxonomy: 정서 태그 분류 체계
        bedrock_client: AWS Bedrock client (선택)
    
    Returns:
        프로필 + 제외 조건
        {
            'emotion_scores': {...},
            'narrative_traits': {...},
            'ending_preference': {...},
            'exclude_genres': ["Horror"],
            'exclude_tags': ["무서워요"],
            'include_genres': ["Romance"],
            'include_tags': ["로맨틱해요"],
            'filters_applied': True,
            'method_used': 'llm' or 'rule_based'
        }
    """
    # 1. LLM으로 부정/긍정 의도 파싱 (자동 Fallback 포함)
    filters = extract_negative_filters_with_llm(user_text, bedrock_client)
    
    # 2. 긍정 부분만으로 프로필 생성
    profile = build_user_profile(user_text, taxonomy)
    
    # 3. 제외/포함 조건 추가
    profile['exclude_genres'] = filters.get('exclude_genres', [])
    profile['exclude_tags'] = filters.get('exclude_tags', [])
    profile['include_genres'] = filters.get('include_genres', [])
    profile['include_tags'] = filters.get('include_tags', [])
    profile['filters_applied'] = (
        len(filters.get('exclude_genres', [])) > 0 or 
        len(filters.get('exclude_tags', [])) > 0
    )
    
    return profile


# LLM 연동용 함수 (구현 완료)
def analyze_user_preference_with_llm(user_text: str, taxonomy: Dict, bedrock_client=None) -> Dict:
    """
    LLM을 사용한 정교한 사용자 취향 분석
    
    키워드 매칭보다 문맥을 더 잘 이해하여 정확한 점수 부여
    
    Args:
        user_text: 사용자 입력 텍스트
        taxonomy: emotion_tag.json
        bedrock_client: Bedrock 클라이언트 (None이면 자동 생성)
    
    Returns:
        {
            'emotion_scores': {...},
            'narrative_traits': {...},
            'ending_preference': {...},
            'method_used': 'llm' or 'keyword_matching'
        }
    """
    import os
    import json
    import boto3
    from dotenv import load_dotenv
    
    # 환경 변수 로드
    load_dotenv()
    
    # Bedrock 클라이언트 생성
    if bedrock_client is None:
        try:
            bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=os.getenv('AWS_REGION', 'ap-northeast-2'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
        except Exception as e:
            print(f"⚠️ Bedrock 클라이언트 생성 실패: {e}")
            print("   → 키워드 매칭으로 대체")
            return _fallback_keyword_matching(user_text, taxonomy)
    
    # 태그 목록 생성
    emotion_tags = taxonomy['emotion']['tags']
    narrative_tags = taxonomy['story_flow']['tags']
    
    # 프롬프트 생성
    prompt = f"""당신은 영화 추천 시스템의 사용자 취향 분석 전문가입니다.

사용자 입력: "{user_text}"

이 사용자의 영화 취향을 분석하여 다음 태그별 선호도를 0.0~1.0 점수로 평가하세요.

**감정 태그:**
{', '.join(emotion_tags)}

**서사 태그:**
{', '.join(narrative_tags)}

**결말 선호도:**
- 해피엔딩 (happy)
- 열린결말 (open)
- 비터스윗 (bittersweet)

**중요 규칙:**
1. 사용자가 명시적으로 언급한 태그는 0.7~1.0 점수
2. 문맥상 관련 있는 태그는 0.4~0.7 점수
3. 관련 없는 태그는 0.0~0.3 점수
4. 모든 태그에 점수를 부여하세요
5. 반드시 JSON 형식으로만 답변하세요 (설명 없이)

JSON 형식:
{{
  "emotion_scores": {{"감동적이에요": 0.8, "슬퍼요": 0.5, ...}},
  "narrative_traits": {{"반전이 많아요": 0.3, ...}},
  "ending_preference": {{"happy": 0.7, "open": 0.5, "bittersweet": 0.3}}
}}
"""
    
    try:
        # Bedrock 호출
        response = bedrock_client.invoke_model(
            modelId=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0'),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": int(os.getenv('BEDROCK_MAX_TOKENS', 2048)),
                "temperature": float(os.getenv('BEDROCK_TEMPERATURE', 0.2)),
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            })
        )
        
        # 응답 파싱
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # JSON 추출
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = json.loads(content)
        
        # 기본값 설정 및 검증
        profile = {
            'emotion_scores': result.get('emotion_scores', {}),
            'narrative_traits': result.get('narrative_traits', {}),
            'ending_preference': result.get('ending_preference', {
                'happy': 0.5, 'open': 0.5, 'bittersweet': 0.5
            }),
            'method_used': 'llm',
            'user_text': user_text
        }
        
        print("✅ LLM 분석 완료 (Claude 사용)")
        return profile
        
    except Exception as e:
        print(f"⚠️ LLM 분석 실패: {e}")
        print("   → 키워드 매칭으로 대체")
        return _fallback_keyword_matching(user_text, taxonomy)


# Fallback: 키워드 매칭 방식
def _fallback_keyword_matching(user_text: str, taxonomy: Dict) -> Dict:
    """
    LLM 실패 시 백업용 키워드 매칭
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
        'method_used': 'keyword_matching'
    }
    
    return profile


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