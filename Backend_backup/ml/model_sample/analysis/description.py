"""
A-5: LLM 기반 추천 근거 문구 생성

A-3에서 계산된 만족 확률 결과를 받아서
자연어로 "왜 이 영화가 당신에게 맞는지" 설명을 생성합니다.
"""

import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import boto3

load_dotenv()


def get_bedrock_client():
    """AWS Bedrock Runtime 클라이언트 생성"""
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        return bedrock_runtime
    except Exception as e:
        print(f"⚠️  Bedrock 클라이언트 초기화 실패: {e}")
        return None


def generate_explanation(
    prediction_result: Dict,
    movie_title: str,
    user_liked_tags: List[str] = None,
    user_disliked_tags: List[str] = None,
    bedrock_client=None
) -> str:
    """
    만족 확률 결과를 자연어 설명으로 변환
    
    Args:
        prediction_result: calculate_satisfaction_probability의 결과
        movie_title: 영화 제목
        user_liked_tags: 사용자가 좋아하는 태그 리스트 (선택)
        user_disliked_tags: 사용자가 싫어하는 태그 리스트 (선택)
        bedrock_client: Bedrock 클라이언트 (선택)
    
    Returns:
        자연어 설명 문자열
    """
    if bedrock_client is None:
        bedrock_client = get_bedrock_client()
    
    if bedrock_client is None:
        # Fallback: 간단한 템플릿 기반 설명
        return _generate_fallback_explanation(
            prediction_result,
            movie_title,
            user_liked_tags=user_liked_tags,
            user_disliked_tags=user_disliked_tags,
        )
    
    breakdown = prediction_result.get("breakdown", {}) or {}
    top_factors = (breakdown.get("top_factors", []) or [])[:2]
    factor_hints = _build_factor_hints(
        top_factors=top_factors,
        user_liked_tags=user_liked_tags,
        user_disliked_tags=user_disliked_tags,
    )

    # LLM 프롬프트 생성
    prompt = _build_explanation_prompt(
        prediction_result,
        movie_title,
        user_liked_tags,
        user_disliked_tags,
        factor_hints=factor_hints,
    )
    
    # Bedrock Claude 호출
    try:
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,  # 설명은 짧게
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3  # 일관성 있는 설명
        }
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'content' in response_body and len(response_body['content']) > 0:
            explanation = response_body['content'][0]['text'].strip()
            explanation = _remove_first_sentence(explanation)
            explanation = _enforce_factor_hint_coverage(explanation, factor_hints)
            return explanation
        else:
            return _generate_fallback_explanation(
                prediction_result,
                movie_title,
                user_liked_tags=user_liked_tags,
                user_disliked_tags=user_disliked_tags,
            )
            
    except Exception as e:
        print(f"⚠️  LLM 설명 생성 실패: {e}")
        return _generate_fallback_explanation(
            prediction_result,
            movie_title,
            user_liked_tags=user_liked_tags,
            user_disliked_tags=user_disliked_tags,
        )


def _remove_first_sentence(text: str) -> str:
    """
    Remove the first sentence from LLM output.
    If only one sentence exists, return original text.
    """
    import re

    if not text:
        return text

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= 1:
        return text.strip()
    return " ".join(sentences[1:]).strip()


def _pick_tag_for_factor(factor: str, tag_pool: List[str]) -> str:
    emotion_keywords = ["감동", "따뜻", "여운", "웃", "긴장", "우울", "슬퍼", "통쾌", "로맨", "무서", "잔인", "폭력", "피"]
    narrative_keywords = ["반전", "전개", "기승전결", "복선", "서사", "스토리", "속도", "구조"]
    ending_keywords = ["결말", "해피", "열린", "비터", "엔딩", "happy", "open", "bittersweet"]

    if factor == "정서 톤":
        keywords = emotion_keywords
    elif factor == "서사 초점":
        keywords = narrative_keywords
    elif factor == "결말 취향":
        keywords = ending_keywords
    else:
        keywords = []

    for tag in tag_pool:
        if any(k.lower() in str(tag).lower() for k in keywords):
            return str(tag)
    return ""


def _naturalize_tag(tag: str, factor: str) -> str:
    t = (tag or "").strip()

    if not t:
        if factor == "정서 톤":
            return "감정선이 또렷한 분위기"
        if factor == "서사 초점":
            return "전개가 분명한 이야기 흐름"
        if factor == "결말 취향":
            return "결말의 여운이 살아 있는 마무리"
        return "취향 포인트"

    normalized = t.lower()
    mapping = [
        ("감동", "감동과 여운이 남는 분위기"),
        ("따뜻", "따뜻하고 편안한 정서"),
        ("웃", "유쾌하고 웃음이 나는 분위기"),
        ("긴장", "긴장감 있게 몰입되는 분위기"),
        ("통쾌", "통쾌하게 해소되는 감정선"),
        ("우울", "무겁고 가라앉은 정서"),
        ("반전", "반전이 살아 있는 전개"),
        ("전개", "속도감 있게 이어지는 전개"),
        ("기승전결", "기승전결이 뚜렷한 서사 구조"),
        ("복선", "복선이 촘촘하게 깔린 구성"),
        ("happy", "해피엔딩으로 정리되는 결말"),
        ("해피", "해피엔딩으로 정리되는 결말"),
        ("open", "여운을 남기는 열린 결말"),
        ("열린", "여운을 남기는 열린 결말"),
        ("bittersweet", "씁쓸한 여운의 비터스윗 결말"),
        ("비터", "씁쓸한 여운의 비터스윗 결말"),
    ]

    for key, phrase in mapping:
        if key in normalized:
            return phrase

    # 마지막 fallback도 원문 태그를 그대로 노출하지 않고 완곡하게 변환
    return f"'{t}' 성향이 드러나는 포인트"


def _build_factor_hints(
    top_factors: List[str],
    user_liked_tags: Optional[List[str]],
    user_disliked_tags: Optional[List[str]],
) -> Dict[str, str]:
    tag_pool = (user_liked_tags or []) + (user_disliked_tags or [])
    hints: Dict[str, str] = {}

    for factor in (top_factors or [])[:2]:
        raw_tag = _pick_tag_for_factor(factor, tag_pool)
        hints[factor] = _naturalize_tag(raw_tag, factor)
    return hints


def _enforce_factor_hint_coverage(explanation: str, factor_hints: Dict[str, str]) -> str:
    """
    핵심 힌트가 설명에 포함되지 않은 경우에만 보강
    중복 방지를 위해 엄격하게 체크
    """
    if not explanation:
        explanation = ""
    explanation = explanation.strip()

    if not factor_hints:
        return explanation

    # 각 힌트의 핵심 키워드 추출 (더 포괄적으로)
    def extract_keywords(hint: str) -> List[str]:
        """힌트에서 핵심 키워드 추출"""
        keywords = []
        keyword_map = {
            "감동": ["감동", "눈물", "울", "가슴"],
            "여운": ["여운", "잔상", "기억"],
            "따뜻": ["따뜻", "포근", "편안", "안정"],
            "웃음": ["웃", "유쾌", "재미", "코믹"],
            "긴장": ["긴장", "몰입", "집중", "긴박"],
            "통쾌": ["통쾌", "시원", "해소", "카타르시스"],
            "무겁": ["무겁", "가라앉", "우울", "침울"],
            "반전": ["반전", "트위스트", "반전"],
            "전개": ["전개", "흐름", "속도", "템포", "진행"],
            "복선": ["복선", "떡밥", "암시"],
            "해피": ["해피", "행복", "밝은"],
            "열린": ["열린", "오픈", "여운"],
            "비터": ["비터", "씁쓸", "아쉬운"]
        }
        
        for key, synonyms in keyword_map.items():
            if any(syn in hint for syn in synonyms):
                keywords.extend(synonyms)
        
        return list(set(keywords))

    # 설명에 이미 포함된 힌트 확인 (더 엄격하게)
    missing_hints = []
    for factor, hint in factor_hints.items():
        if not hint:
            continue
        
        # 힌트의 핵심 키워드가 설명에 하나라도 있으면 이미 언급된 것으로 간주
        keywords = extract_keywords(hint)
        if keywords:
            already_mentioned = any(kw in explanation for kw in keywords)
            if not already_mentioned:
                missing_hints.append(hint)
        else:
            # 키워드 추출 실패 시 전체 문자열로 확인
            if hint not in explanation:
                missing_hints.append(hint)

    # 모든 힌트가 이미 언급되었거나, 설명이 충분히 길면 추가하지 않음
    if not missing_hints or len(explanation) > 100:
        return explanation

    # 누락된 힌트만 추가 (하지만 매우 보수적으로)
    hint_text = " 그리고 ".join(missing_hints)
    supplement = f"특히 {hint_text} 부분이 취향과 잘 맞아요."

    if not explanation:
        return supplement
    if explanation.endswith((".", "!", "?")):
        return f"{explanation} {supplement}"
    return f"{explanation}. {supplement}"


def _build_explanation_prompt(
    prediction_result: Dict,
    movie_title: str,
    user_liked_tags: List[str],
    user_disliked_tags: List[str],
    factor_hints: Optional[Dict[str, str]] = None,
) -> str:
    """
    LLM용 프롬프트 생성
    """
    prob = prediction_result.get("probability", 0) * 100
    breakdown = prediction_result.get("breakdown", {})
    
    emotion_sim = breakdown.get("emotion_similarity", 0) * 100
    narrative_sim = breakdown.get("narrative_similarity", 0) * 100
    ending_sim = breakdown.get("ending_similarity", 0) * 100
    boost_score = breakdown.get("boost_score", 0)
    dislike_penalty = breakdown.get("dislike_penalty", 0)
    top_factors = breakdown.get("top_factors", [])
    
    # 사용자 취향 정보
    liked_str = ""
    if user_liked_tags and len(user_liked_tags) > 0:
        liked_str = f"좋아하는 태그: {', '.join(user_liked_tags[:5])}"
    
    disliked_str = ""
    if user_disliked_tags and len(user_disliked_tags) > 0:
        disliked_str = f"싫어하는 태그: {', '.join(user_disliked_tags[:5])}"

    factor_hint_lines = []
    for factor, hint in (factor_hints or {}).items():
        factor_hint_lines.append(f"- {factor}: {hint}")
    factor_hint_text = "\n".join(factor_hint_lines) if factor_hint_lines else "- 정서 톤: 감정선이 또렷한 분위기\n- 서사 초점: 전개가 분명한 이야기 흐름"
    
    # 30% 이하는 불일치 중심, 그 외는 일치 중심
    if prob <= 30:
        prompt = f"""다음 정보를 바탕으로 왜 이 영화가 사용자의 취향과 맞지 않는지 2-3줄로 친근하게 설명해주세요.

영화: "{movie_title}"

주요 불일치 요소: {", ".join(top_factors)}
- 감정 유사사: {emotion_sim:.0f}%
- 서사 유사사: {narrative_sim:.0f}%
- 결말 유사사: {ending_sim:.0f}%

{liked_str}
{disliked_str}

좋아하는 것 보너스: {boost_score:.1f}
싫어하는 것 페널티: {dislike_penalty:.1f}

요구사항:
1. 첫 문장은 확률/부합도 소개 문장으로 쓰지 마세요
2. 퍼센트(%) 및 숫자 수치를 설명에 쓰지 마세요
3. 아래 '핵심 설명 소재' 2개를 모두 구체적으로 언급하세요
4. '정서적 측면/서사적 측면' 같은 모호한 표현만 쓰지 마세요
5. 태그 원문을 그대로 인용하지 말고 자연어로 풀어 쓰세요
6. 2-3줄로 간결하게

핵심 설명 소재:
{factor_hint_text}

설명만 출력하고 다른 텍스트는 포함하지 마세요"""
    else:
        prompt = f"""다음 정보를 바탕으로 왜 이 영화가 사용자 취향에 맞는지 2-3줄로 친근하게 설명해주세요.

영화: "{movie_title}"
만족 확률(참고용): {prob:.0f}%

주요 일치 요소: {", ".join(top_factors)}
- 감정 유사사: {emotion_sim:.0f}%
- 서사 유사사: {narrative_sim:.0f}%
- 결말 유사사: {ending_sim:.0f}%

{liked_str}
{disliked_str}

좋아하는 것 보너스: {boost_score:.1f}
싫어하는 것 페널티: {dislike_penalty:.1f}

요구사항:
1. 첫 문장은 확률/부합도 소개 문장으로 쓰지 마세요
2. 퍼센트(%) 및 숫자 수치를 설명에 쓰지 마세요
3. 아래 '핵심 설명 소재' 2개를 모두 구체적으로 언급하세요
4. '정서적 측면/서사적 측면' 같은 모호한 표현만 쓰지 마세요
5. 태그 원문을 그대로 인용하지 말고 자연어로 풀어 쓰세요
6. 2-3줄로 간결하게

핵심 설명 소재:
{factor_hint_text}

설명만 출력하고 다른 텍스트는 포함하지 마세요"""

    return prompt


def _generate_fallback_explanation(
    prediction_result: Dict,
    movie_title: str,
    user_liked_tags: List[str] = None,
    user_disliked_tags: List[str] = None,
) -> str:
    """
    LLM 사용 불가 시 템플릿 기반 설명.
    top_factors에 따라 정서/서사/결말 중 2개 요소를 사용합니다.
    """
    breakdown = prediction_result.get("breakdown", {})
    top_factors = (breakdown.get("top_factors", []) or [])[:2]
    if not top_factors:
        top_factors = ["정서 톤", "서사 초점"]

    liked_tags = user_liked_tags or []
    disliked_tags = user_disliked_tags or []
    tag_pool = liked_tags + disliked_tags

    emotion_keywords = ["감동", "따뜻", "여운", "웃", "긴장", "우울", "슬퍼", "통쾌", "로맨", "무서", "잔인", "폭력", "피"]
    narrative_keywords = ["반전", "전개", "기승전결", "복선", "서사", "스토리", "속도", "구조"]
    ending_keywords = ["결말", "해피", "열린", "비터", "엔딩"]

    def pick_tag(keywords: List[str]) -> str:
        for t in tag_pool:
            if any(k in t for k in keywords):
                return t
        return ""

    factor_phrase = {
        "정서 톤": f"정서 톤에서는 '{pick_tag(emotion_keywords) or '감정선'}'",
        "서사 초점": f"서사 측면에서는 '{pick_tag(narrative_keywords) or '전개'}'",
        "결말 취향": f"결말 취향에서는 '{pick_tag(ending_keywords) or '엔딩'}'",
    }

    selected = [factor_phrase.get(f, f"'{f}'") for f in top_factors]
    if len(selected) == 1:
        core = selected[0]
    else:
        core = f"{selected[0]}와 {selected[1]}"

    explanation = f'"{movie_title}"은 {core} 요소가 맞아 취향 적합성이 높아 보입니다.'
    explanation += "\n이 예측은 정서 특성 기반이므로 개인차게 있을 수 있습니다."
    
    return explanation


# CLI 테스트
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='A-5 설명 생성 테스트')
    parser.add_argument('--movie-title', default='인생은 아름다워')
    parser.add_argument('--prob', type=float, default=0.87)
    
    args = parser.parse_args()
    
    # 테스트 데이터
    test_result = {
        "probability": args.prob,
        "confidence": 0.92,
        "breakdown": {
            "emotion_similarity": 0.91,
            "narrative_similarity": 0.85,
            "ending_similarity": 0.78,
            "boost_score": 5.2,
            "dislike_penalty": 1.3,
            "top_factors": ["정서 톤", "서사 초점"]
        }
    }
    
    bedrock_client = get_bedrock_client()
    
    explanation = generate_explanation(
        test_result,
        args.movie_title,
        user_liked_tags=["따뜻해요", "여운이 길어요", "웅장해요"],
        user_disliked_tags=["무서워요", "긴장돼요"],
        bedrock_client=bedrock_client
    )
    
    print("\n" + "="*60)
    print(f"영화: {args.movie_title}")
    print(f"만족 확률: {test_result['probability']:.1%}")
    print("="*60)
    print(f"\nAI 설명:\n{explanation}\n")
