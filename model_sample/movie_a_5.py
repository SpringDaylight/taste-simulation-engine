"""
A-5: LLM 기반 확률 근거 문구 생성

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
        return _generate_fallback_explanation(prediction_result, movie_title)
    
    # LLM 프롬프트 생성
    prompt = _build_explanation_prompt(
        prediction_result,
        movie_title,
        user_liked_tags,
        user_disliked_tags
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
            return explanation
        else:
            return _generate_fallback_explanation(prediction_result, movie_title)
            
    except Exception as e:
        print(f"⚠️  LLM 설명 생성 실패: {e}")
        return _generate_fallback_explanation(prediction_result, movie_title)


def _build_explanation_prompt(
    prediction_result: Dict,
    movie_title: str,
    user_liked_tags: List[str],
    user_disliked_tags: List[str]
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
    
    # 30% 이하일 때는 퍼센트를 언급하지 않음
    if prob <= 30:
        prompt = f"""다음 정보를 바탕으로 왜 이 영화가 사용자의 취향과 맞지 않는지 2-3줄로 친근하게 설명해주세요.

영화: "{movie_title}"

주요 불일치 요소: {", ".join(top_factors)}
- 감정 유사도: {emotion_sim:.0f}%
- 서사 유사도: {narrative_sim:.0f}%
- 결말 유사도: {ending_sim:.0f}%

{liked_str}
{disliked_str}

좋아하는 것 보너스: {boost_score:.1f}
싫어하는 것 페널티: {dislike_penalty:.1f}

요구사항:
1. 사용자 입장에서 "당신"으로 시작
2. 구체적인 퍼센트(%)를 언급하지 마세요
3. 주요 불일치 이유를 설명
4. 2-3줄로 간결하게

설명만 출력하고 다른 텍스트는 포함하지 마세요."""
    else:
        prompt = f"""다음 정보를 바탕으로 왜 이 영화가 사용자에게 {prob:.0f}% 적합한지 2-3줄로 친근하게 설명해주세요.

영화: "{movie_title}"
만족 확률: {prob:.0f}%

주요 일치 요소: {", ".join(top_factors)}
- 감정 유사도: {emotion_sim:.0f}%
- 서사 유사도: {narrative_sim:.0f}%
- 결말 유사도: {ending_sim:.0f}%

{liked_str}
{disliked_str}

좋아하는 것 보너스: {boost_score:.1f}
싫어하는 것 페널티: {dislike_penalty:.1f}

요구사항:
1. 사용자 입장에서 "당신"으로 시작
2. 구체적인 수치(%)를 포함
3. 주요 일치 요소를 언급
4. 2-3줄로 간결하게

설명만 출력하고 다른 텍스트는 포함하지 마세요."""

    return prompt


def _generate_fallback_explanation(
    prediction_result: Dict,
    movie_title: str
) -> str:
    """
    LLM 사용 불가 시 템플릿 기반 설명
    """
    prob = prediction_result.get("probability", 0) * 100
    breakdown = prediction_result.get("breakdown", {})
    top_factors = breakdown.get("top_factors", ["취향 요소"])
    
    explanation = f'"{movie_title}"는 당신의 취향과 {prob:.0f}% 일치합니다. '
    explanation += f'특히 {", ".join(top_factors)}가 잘 맞습니다. '
    explanation += '이 예측은 확률 기반이므로 개인차가 있을 수 있습니다.'
    
    return explanation


# CLI 테스트
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='A-5 설명 생성 테스트')
    parser.add_argument('--movie-title', default='쇼생크 탈출')
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
        user_liked_tags=["따뜻해요", "여운이 길어요", "잔잔해요"],
        user_disliked_tags=["무서워요", "긴장돼요"],
        bedrock_client=bedrock_client
    )
    
    print("\n" + "="*60)
    print(f"영화: {args.movie_title}")
    print(f"만족 확률: {test_result['probability']:.1%}")
    print("="*60)
    print(f"\n📝 설명:\n{explanation}\n")
