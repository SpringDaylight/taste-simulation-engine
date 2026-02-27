"""
A-6: 그룹 취향 시뮬레이션
여러 사용자의 취향을 종합하여 그룹 만족도 계산 (Least Misery Strategy)
"""
from typing import Dict, List
from domain.a3_prediction import calculate_satisfaction_probability


def _level_from_prob(prob: float) -> str:
    """확률을 만족도 레벨로 변환"""
    if prob >= 0.85:
        return "매우 만족"
    if prob >= 0.70:
        return "만족"
    if prob >= 0.50:
        return "보통"
    if prob >= 0.30:
        return "불만"
    return "매우 불만"


def _group_comment(group_prob: float, min_prob: float, max_prob: float) -> str:
    """그룹 만족도에 대한 코멘트 생성"""
    variance = max_prob - min_prob
    
    if group_prob >= 0.70:
        if variance < 0.2:
            return "모두가 만족할 만한 선택입니다!"
        else:
            return "전반적으로 만족도가 높지만, 일부 의견 차이가 있을 수 있습니다."
    elif group_prob >= 0.50:
        if variance < 0.3:
            return "무난한 선택이지만, 더 나은 옵션을 찾아볼 수도 있습니다."
        else:
            return "의견이 갈릴 수 있는 선택입니다. 다른 영화도 고려해보세요."
    else:
        return "그룹 전체의 만족도가 낮을 수 있습니다. 다른 영화를 추천드립니다."


def simulate_group(payload: dict) -> dict:
    """
    A-6: 그룹 취향 시뮬레이터
    
    Least Misery Strategy: 그룹 내 최소 만족도를 그룹 점수로 사용
    (한 명이라도 크게 불만족하면 전체 만족도가 낮아짐)
    
    Args:
        payload: {
            "members": [
                {
                    "user_id": str,
                    "profile": Dict (A-1 결과),
                    "dislikes": List[str],
                    "likes": List[str]
                },
                ...
            ],
            "movie_profile": Dict (A-2 결과),
            "penalty_weight": float (기본 0.7),
            "boost_weight": float (기본 0.5),
            "strategy": str (기본 "least_misery", 옵션: "average", "least_misery")
        }
    
    Returns:
        {
            "group_score": float (0-1),
            "strategy": str,
            "members": [
                {
                    "user_id": str,
                    "probability": float,
                    "confidence": float,
                    "level": str
                },
                ...
            ],
            "comment": str,
            "recommendation": str
        }
    """
    members = payload.get("members", [])
    movie_profile = payload.get("movie_profile", {})
    penalty_weight = float(payload.get("penalty_weight", 0.7))
    boost_weight = float(payload.get("boost_weight", 0.5))
    strategy = payload.get("strategy", "least_misery")
    
    if not members:
        return {
            "group_score": 0.0,
            "strategy": strategy,
            "members": [],
            "comment": "그룹 입력이 없습니다.",
            "recommendation": "멤버를 추가해주세요."
        }
    
    user_probs = []
    member_results = []
    
    # 각 멤버별 만족도 계산
    for m in members:
        profile = m.get("profile", {})
        dislikes = m.get("dislikes", [])
        likes = m.get("likes", [])
        
        result = calculate_satisfaction_probability(
            user_profile=profile,
            movie_profile=movie_profile,
            dislikes=dislikes,
            boost_tags=likes,
            penalty_weight=penalty_weight,
            boost_weight=boost_weight,
        )
        
        prob = float(result["probability"])
        user_probs.append(prob)
        
        member_results.append({
            "user_id": m.get("user_id", ""),
            "probability": result["probability"],
            "confidence": result["confidence"],
            "level": _level_from_prob(prob)
        })
    
    # 그룹 점수 계산
    if strategy == "least_misery":
        # Least Misery: 최소값 사용
        group_prob = min(user_probs)
    else:
        # Average: 평균값 사용
        group_prob = sum(user_probs) / len(user_probs)
    
    min_prob = min(user_probs)
    max_prob = max(user_probs)
    
    # 코멘트 및 추천 생성
    comment = _group_comment(group_prob, min_prob, max_prob)
    
    if group_prob >= 0.70:
        recommendation = "이 영화를 함께 보시는 것을 추천드립니다!"
    elif group_prob >= 0.50:
        recommendation = "괜찮은 선택이지만, 다른 옵션도 고려해보세요."
    else:
        recommendation = "다른 영화를 찾아보시는 것을 권장합니다."
    
    return {
        "group_score": round(group_prob, 3),
        "strategy": strategy,
        "members": member_results,
        "comment": comment,
        "recommendation": recommendation,
        "statistics": {
            "min_satisfaction": round(min_prob, 3),
            "max_satisfaction": round(max_prob, 3),
            "avg_satisfaction": round(sum(user_probs) / len(user_probs), 3),
            "variance": round(max_prob - min_prob, 3)
        }
    }
