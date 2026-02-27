"""
개선된 만족 확률 계산 함수
- dislike_penalty를 max로 변경 (가장 즉각적)
- boost/penalty 정규화 (mean 또는 cap)
- 선형 → sigmoid로 변경 (k 조절)
- 센터링/Top-k 희소화 옵션
"""
import math
from typing import Dict, List
import numpy as np


def cosine_sim(a: List[float], b: List[float]) -> float:
    """코사인 유사도 계산"""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def align_vector(d: Dict[str, float], keys: List[str]) -> List[float]:
    """딕셔너리를 정렬된 벡터로 변환"""
    return [d.get(k, 0.0) for k in keys]


def _calculate_dislike_penalty_max(movie_profile: Dict, dislikes: List[str]) -> float:
    """
    싫어하는 태그 페널티 계산 (MAX 방식 - 가장 즉각적)
    
    Args:
        movie_profile: 영화 프로필
        dislikes: 싫어하는 태그 리스트
    
    Returns:
        최대 페널티 점수 (0 이상)
    """
    max_penalty = 0.0
    categories = ['emotion_scores', 'narrative_traits', 'direction_mood', 'character_relationship']
    
    for category in categories:
        if category in movie_profile:
            for tag in dislikes:
                if tag in movie_profile[category]:
                    max_penalty = max(max_penalty, movie_profile[category][tag])
    
    return max_penalty


def _calculate_boost_score_normalized(movie_profile: Dict, boost_tags: List[str], 
                                      normalize_method: str = 'mean') -> float:
    """
    좋아하는 태그 보너스 계산 (정규화 적용)
    
    Args:
        movie_profile: 영화 프로필
        boost_tags: 좋아하는 태그 리스트
        normalize_method: 'mean' (평균) 또는 'cap' (상한)
    
    Returns:
        정규화된 보너스 점수 (0~1 범위)
    """
    boost_scores = []
    categories = ['emotion_scores', 'narrative_traits', 'direction_mood', 'character_relationship']
    
    for category in categories:
        if category in movie_profile:
            for tag in boost_tags:
                if tag in movie_profile[category]:
                    boost_scores.append(movie_profile[category][tag])
    
    if not boost_scores:
        return 0.0
    
    if normalize_method == 'mean':
        # 평균으로 정규화
        return sum(boost_scores) / len(boost_scores)
    elif normalize_method == 'cap':
        # 상한 적용 (최대 1.0)
        return min(sum(boost_scores), 1.0)
    else:
        return sum(boost_scores) / len(boost_scores)


def _apply_top_k_sparsity(scores: Dict[str, float], k: int = 5) -> Dict[str, float]:
    """
    Top-K 희소화: 상위 K개만 유지하고 나머지는 0으로
    
    Args:
        scores: 점수 딕셔너리
        k: 유지할 상위 개수
    
    Returns:
        희소화된 점수 딕셔너리
    """
    if len(scores) <= k:
        return scores
    
    # 상위 k개 선택
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_k_items = sorted_items[:k]
    
    return {tag: score for tag, score in top_k_items}


def _center_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """
    점수 센터링: 평균을 0으로 이동
    
    Args:
        scores: 점수 딕셔너리
    
    Returns:
        센터링된 점수 딕셔너리
    """
    if not scores:
        return scores
    
    mean_score = sum(scores.values()) / len(scores)
    return {tag: score - mean_score for tag, score in scores.items()}


def sigmoid(x: float, k: float = 8.0, x0: float = 0.5) -> float:
    """
    시그모이드 함수
    
    Args:
        x: 입력값
        k: 기울기 (높을수록 급격한 변화)
        x0: 중심점
    
    Returns:
        시그모이드 변환 값 (0~1)
    """
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


def _get_top_factors(sim_e: float, sim_n: float, sim_dm: float = 0.0) -> List[str]:
    """매칭에 가장 크게 기여하는 요소 식별"""
    factors = [
        ("정서 톤", sim_e),
        ("서사 초점", sim_n),
        ("연출 분위기", sim_dm),
    ]
    factors.sort(key=lambda x: x[1], reverse=True)
    return [f[0] for f in factors[:2]]


def calculate_satisfaction_probability_improved(
    user_profile: Dict, 
    movie_profile: Dict, 
    dislikes: List[str] = None,
    boost_tags: List[str] = None,
    weights: Dict[str, float] = None,
    penalty_weight: float = 0.7,
    boost_weight: float = 0.03,
    use_sigmoid: bool = True,
    sigmoid_k: float = 6.0,
    sigmoid_x0: float = 0.5,
    normalize_method: str = 'mean',
    apply_centering: bool = False,
    apply_top_k: bool = False,
    top_k: int = 5
) -> Dict:
    """
    개선된 만족 확률 계산
    
    Args:
        user_profile: 사용자 취향 프로필
        movie_profile: 영화 특성 프로필
        dislikes: 싫어하는 태그 리스트
        boost_tags: 좋아하는 태그 리스트
        weights: 가중치 딕셔너리
        penalty_weight: 페널티 가중치
        boost_weight: 보너스 가중치
        use_sigmoid: 시그모이드 사용 여부
        sigmoid_k: 시그모이드 기울기
        sigmoid_x0: 시그모이드 중심점
        normalize_method: 정규화 방법 ('mean' 또는 'cap')
        apply_centering: 센터링 적용 여부
        apply_top_k: Top-K 희소화 적용 여부
        top_k: 유지할 상위 개수
    
    Returns:
        만족 확률 및 상세 정보
    """
    if dislikes is None:
        dislikes = []
    if boost_tags is None:
        boost_tags = []
    if weights is None:
        weights = {"emotion": 0.4, "narrative": 0.4, "direction_mood": 0.2}
    
    # 센터링 적용 (옵션)
    user_emotion = user_profile['emotion_scores']
    user_narrative = user_profile['narrative_traits']
    
    if apply_centering:
        user_emotion = _center_scores(user_emotion)
        user_narrative = _center_scores(user_narrative)
    
    # Top-K 희소화 적용 (옵션)
    if apply_top_k:
        user_emotion = _apply_top_k_sparsity(user_emotion, top_k)
        user_narrative = _apply_top_k_sparsity(user_narrative, top_k)
    
    # 1. 차원별 코사인 유사도 계산
    e_keys  = list(user_emotion.keys())
    n_keys  = list(user_narrative.keys())
    dm_keys = list(user_profile.get('direction_mood', {}).keys())

    sim_e = cosine_sim(
        align_vector(user_emotion, e_keys),
        align_vector(movie_profile.get('emotion_scores', {}), e_keys),
    )
    sim_n = cosine_sim(
        align_vector(user_narrative, n_keys),
        align_vector(movie_profile.get('narrative_traits', {}), n_keys),
    )
    sim_dm = cosine_sim(
        align_vector(user_profile.get('direction_mood', {}), dm_keys),
        align_vector(movie_profile.get('direction_mood', {}), dm_keys),
    ) if dm_keys else 0.0

    # 2. 좋아하는 것 보너스 계산 (정규화)
    boost_score = _calculate_boost_score_normalized(movie_profile, boost_tags, normalize_method)
    
    # 3. 싫어하는 것 페널티 계산 (MAX 방식)
    dislike_penalty = _calculate_dislike_penalty_max(movie_profile, dislikes)
    
    # 4. 가중치 적용
    w_e  = weights.get("emotion", 0.4)
    w_n  = weights.get("narrative", 0.4)
    w_dm = weights.get("direction_mood", 0.2)

    # 5. 최종 점수 계산
    raw_score = (w_e * sim_e + w_n * sim_n + w_dm * sim_dm) \
                + (boost_weight * boost_score) \
                - (penalty_weight * dislike_penalty)
    
    # 6. 확률로 변환
    if use_sigmoid:
        normalized = (raw_score + 1) / 2
        normalized = max(0.0, min(1.0, normalized))
        probability = sigmoid(normalized, k=sigmoid_k, x0=sigmoid_x0)
    else:
        probability = (raw_score + 1) / 2
        probability = max(0.0, min(1.0, probability))
    
    # 7. 신뢰도 계산
    std_dev = np.std([sim_e, sim_n, sim_dm])
    confidence = 1 - min(std_dev, 1.0)
    
    # 8. 상세 분석
    breakdown = {
        "emotion_similarity":        round(float(sim_e),  3),
        "narrative_similarity":      round(float(sim_n),  3),
        "direction_mood_similarity": round(float(sim_dm), 3),
        "boost_score":               round(float(boost_score), 3),
        "dislike_penalty":           round(float(dislike_penalty), 3),
        "top_factors": _get_top_factors(sim_e, sim_n, sim_dm)
    }
    
    return {
        "probability": round(float(probability), 3),
        "confidence": round(float(confidence), 3),
        "raw_score": round(float(raw_score), 3),
        "breakdown": breakdown
    }
