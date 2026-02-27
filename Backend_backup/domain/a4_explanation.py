"""
A-4: 설명 가능한 추천
만족 확률 결과를 자연어로 설명
"""
from typing import Dict, List
import os
import boto3


def _generate_template_explanation(
    prediction_result: Dict,
    movie_title: str,
    user_liked_tags: List[str] = None,
    user_disliked_tags: List[str] = None
) -> str:
    """
    템플릿 기반 설명 생성 (LLM 없이도 작동)
    
    Args:
        prediction_result: A-3의 결과
        movie_title: 영화 제목
        user_liked_tags: 좋아하는 태그
        user_disliked_tags: 싫어하는 태그
    
    Returns:
        자연어 설명
    """
    prob = prediction_result.get("probability", 0) * 100
    breakdown = prediction_result.get("breakdown", {})
    top_factors = breakdown.get("top_factors", ["취향 요소"])
    
    # 30% 이하: 부정적 설명
    if prob <= 30:
        explanation = f'"{movie_title}"은 당신의 취향과 잘 맞지 않을 수 있습니다. '
        explanation += f'{", ".join(top_factors)} 측면에서 차이가 있습니다. '
        
        if user_disliked_tags and len(user_disliked_tags) > 0:
            explanation += f'특히 당신이 선호하지 않는 {", ".join(user_disliked_tags[:3])} 요소가 포함되어 있습니다. '
    
    # 30-70%: 중립적 설명
    elif prob <= 70:
        explanation = f'"{movie_title}"은 당신의 취향과 {prob:.0f}% 일치합니다. '
        explanation += f'{", ".join(top_factors)} 측면에서 어느 정도 맞을 수 있습니다. '
        
        if user_liked_tags and len(user_liked_tags) > 0:
            explanation += f'당신이 좋아하는 {", ".join(user_liked_tags[:2])} 요소가 일부 포함되어 있습니다. '
    
    # 70% 이상: 긍정적 설명
    else:
        explanation = f'"{movie_title}"은 당신의 취향과 {prob:.0f}% 일치합니다! '
        explanation += f'특히 {", ".join(top_factors)} 측면에서 잘 맞습니다. '
        
        if user_liked_tags and len(user_liked_tags) > 0:
            explanation += f'당신이 좋아하는 {", ".join(user_liked_tags[:3])} 요소가 강하게 나타납니다. '
    
    # 면책 조항
    explanation += '이 예측은 정서·서사 분석 기반이므로 개인차가 있을 수 있습니다.'
    
    return explanation


def explain_prediction(payload: dict) -> dict:
    """
    A-4: 설명 가능한 추천 (캐싱 적용)
    
    Args:
        payload: {
            "movie_title": str,
            "match_rate": float (0-100),
            "probability": float (0-1),
            "breakdown": Dict,
            "user_liked_tags": List[str] (선택),
            "user_disliked_tags": List[str] (선택)
        }
    
    Returns:
        {
            "movie_title": str,
            "match_rate": float,
            "explanation": str,
            "key_factors": List[Dict],
            "disclaimer": str
        }
    """
    from utils.cache import cache_get, cache_set
    import hashlib
    import json
    
    movie_title = payload.get("movie_title", "Unknown")
    match_rate = payload.get("match_rate", 0.0)
    probability = payload.get("probability", match_rate / 100.0)
    breakdown = payload.get("breakdown", {})
    user_liked_tags = payload.get("user_liked_tags", [])
    user_disliked_tags = payload.get("user_disliked_tags", [])
    
    # 캐시 키 생성: explanation_detail:{movie_title}:{probability_rounded}
    # probability를 반올림하여 유사한 확률은 같은 캐시 사용
    prob_rounded = round(probability, 2)
    cache_key = f"explanation_detail:{movie_title}:{prob_rounded}"
    
    # 캐시 확인
    cached_result = cache_get(cache_key)
    if cached_result:
        print(f"✅ [ExplainDetail] Cache hit: {cache_key}")
        return cached_result
    
    print(f"🔍 [ExplainDetail] Cache miss, generating: {cache_key}")
    
    # 예측 결과 재구성
    prediction_result = {
        "probability": probability,
        "breakdown": breakdown
    }
    
    # LLM 기반 설명 생성 시도
    try:
        from ml.model_sample.analysis.description import generate_explanation, get_bedrock_client
        
        bedrock_client = get_bedrock_client()
        if bedrock_client:
            explanation = generate_explanation(
                prediction_result=prediction_result,
                movie_title=movie_title,
                user_liked_tags=user_liked_tags,
                user_disliked_tags=user_disliked_tags,
                bedrock_client=bedrock_client
            )
        else:
            # Bedrock 클라이언트 없으면 템플릿 사용
            explanation = _generate_template_explanation(
                prediction_result,
                movie_title,
                user_liked_tags,
                user_disliked_tags
            )
    except Exception as e:
        print(f"⚠️  LLM 설명 생성 실패, 템플릿 사용: {e}")
        # LLM 실패 시 템플릿 fallback
        explanation = _generate_template_explanation(
            prediction_result,
            movie_title,
            user_liked_tags,
            user_disliked_tags
        )
    
    # 주요 요소 추출
    key_factors = []
    if breakdown:
        emotion_sim   = breakdown.get("emotion_similarity", 0)
        narrative_sim = breakdown.get("narrative_similarity", 0)
        direction_sim = breakdown.get("direction_mood_similarity", breakdown.get("ending_similarity", 0))
        
        key_factors = [
            {"category": "emotion",        "label": "정서 톤",    "score": round(emotion_sim, 2)},
            {"category": "narrative",      "label": "서사 초점",  "score": round(narrative_sim, 2)},
            {"category": "direction_mood", "label": "연출 분위기", "score": round(direction_sim, 2)},
        ]
        
        # 점수 높은 순으로 정렬
        key_factors.sort(key=lambda x: x["score"], reverse=True)
    
    result = {
        "movie_title": movie_title,
        "match_rate": round(match_rate, 2),
        "explanation": explanation,
        "key_factors": key_factors,
        "disclaimer": "추천은 정서·서사 태그 분석 기반이며 개인차가 있을 수 있습니다."
    }
    
    # 캐시에 저장 (TTL 24시간 - 설명은 자주 바뀌지 않음)
    cache_set(cache_key, result, ttl=86400)
    print(f"✅ [ExplainDetail] Cached result: {cache_key}")
    
    return result
