## A-3 취향 시뮬레이터

import argparse
import json
import math
from typing import Dict, List

import numpy as np
import movie_a_2


# 코사인 유사도 계산
# 1.0: 완전히 같은 방향 (취향 일치)
# 0.0: 직각 (무관계)
# -1.0: 정반대 방향 (취향 불일치)
def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# Sigmoid 함수 - 확률로 변환
def sigmoid(x: float, k: float = 8.0, x0: float = 0.5) -> float:
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


# 딕셔너리를 정렬된 벡터로 변환
def align_vector(d: Dict[str, float], keys: List[str]) -> List[float]:
    return [d.get(k, 0.0) for k in keys]


# 싫어하는 것 페널티 계산 (모든 카테고리)
def _calculate_dislike_penalty(movie_profile: Dict, dislikes: List[str]) -> float:
    """
    사용자가 싫어하는 태그에 대한 페널티 계산
    모든 카테고리(감정, 서사, 연출, 캐릭터)에서 체크
    
    Args:
        movie_profile: 영화 프로필
        dislikes: 싫어하는 태그 리스트
    
    Returns:
        페널티 점수 (0 이상)
    """
    penalty = 0.0
    
    # 모든 카테고리에서 싫어하는 태그 확인
    categories = ['emotion_scores', 'narrative_traits', 'direction_mood', 'character_relationship']
    
    for category in categories:
        if category in movie_profile:
            for tag in dislikes:
                if tag in movie_profile[category]:
                    penalty += movie_profile[category][tag]
    
    return penalty


# 좋아하는 것 보너스 계산 (모든 카테고리)
def _calculate_boost_score(movie_profile: Dict, boost_tags: List[str]) -> float:
    """
    사용자가 좋아하는 태그에 대한 보너스 점수 계산
    모든 카테고리(감정, 서사, 연출, 캐릭터)에서 체크
    
    Args:
        movie_profile: 영화 프로필
        boost_tags: 좋아하는 태그 리스트
    
    Returns:
        보너스 점수 (0 이상)
    """
    boost = 0.0
    
    # 모든 카테고리에서 좋아하는 태그 확인
    categories = ['emotion_scores', 'narrative_traits', 'direction_mood', 'character_relationship']
    
    for category in categories:
        if category in movie_profile:
            for tag in boost_tags:
                if tag in movie_profile[category]:
                    boost += movie_profile[category][tag]
    
    return boost


# 주요 기여 요소 식별
def _get_top_factors(sim_e: float, sim_n: float, sim_d: float) -> List[str]:
    """
    매칭에 가장 크게 기여하는 요소 식별
    
    Args:
        sim_e: 감정 유사도
        sim_n: 서사 유사도
        sim_d: 결말 유사도
    
    Returns:
        상위 2개 요소 이름 리스트
    """
    factors = [
        ("정서 톤", sim_e),
        ("서사 초점", sim_n),
        ("결말 취향", sim_d)
    ]
    factors.sort(key=lambda x: x[1], reverse=True)
    return [f[0] for f in factors[:2]]


# 만족 확률 계산 (개선된 버전)
def calculate_satisfaction_probability(
    user_profile: Dict, 
    movie_profile: Dict, 
    dislikes: List[str] = None,
    boost_tags: List[str] = None,
    weights: Dict[str, float] = None,
    penalty_weight: float = 0.7,
    boost_weight: float = 0.5
) -> Dict:
    """
    사용자 취향과 영화 특성 간 만족 확률 계산
    
    Args:
        user_profile: 사용자 취향 프로필
        movie_profile: 영화 특성 프로필
        dislikes: 싫어하는 태그 리스트 (선택)
        boost_tags: 좋아하는 태그 리스트 (선택)
        weights: 가중치 딕셔너리 (기본: emotion=0.5, narrative=0.3, ending=0.2)
        penalty_weight: 싫어하는 것 페널티 가중치 (기본: 0.7)
        boost_weight: 좋아하는 것 보너스 가중치 (기본: 0.5)
    
    Returns:
        dict: {
            "probability": 0.85,          # 만족 확률 (0~1)
            "confidence": 0.92,            # 신뢰도 (0~1)
            "raw_score": 0.74,             # 원본 점수 (-1~1)
            "breakdown": {                 # 상세 분해
                "emotion_similarity": 0.91,
                "narrative_similarity": 0.85,
                "ending_similarity": 0.78,
                "dislike_penalty": 0.12,
                "top_factors": ["정서 톤", "서사 초점"]
            }
        }
    """
    # 기본값 설정
    if dislikes is None:
        dislikes = []
    if boost_tags is None:
        boost_tags = []
    if weights is None:
        weights = {"emotion": 0.5, "narrative": 0.3, "ending": 0.2}
    
    # 1. 차원별 코사인 유사도 계산
    e_keys = list(user_profile['emotion_scores'].keys())
    n_keys = list(user_profile['narrative_traits'].keys())
    d_keys = list(user_profile['ending_preference'].keys())

    sim_e = cosine_sim(
        align_vector(user_profile['emotion_scores'], e_keys),
        align_vector(movie_profile['emotion_scores'], e_keys),
    )
    sim_n = cosine_sim(
        align_vector(user_profile['narrative_traits'], n_keys),
        align_vector(movie_profile['narrative_traits'], n_keys),
    )
    sim_d = cosine_sim(
        align_vector(user_profile['ending_preference'], d_keys),
        align_vector(movie_profile['ending_preference'], d_keys),
    )

    # 2. 좋아하는 것 보너스 계산
    boost_score = _calculate_boost_score(movie_profile, boost_tags)
    
    # 3. 싫어하는 것 페널티 계산
    dislike_penalty = _calculate_dislike_penalty(movie_profile, dislikes)
    
    # 4. 가중치 적용
    w_e = weights.get("emotion", 0.5)
    w_n = weights.get("narrative", 0.3)
    w_d = weights.get("ending", 0.2)
    
    # 5. 최종 점수 계산: (기본식) + (좋아하는 것) - (싫어하는 것)
    raw_score = (w_e * sim_e + w_n * sim_n + w_d * sim_d) \
                + (boost_weight * boost_score) \
                - (penalty_weight * dislike_penalty)
    
    # 6. 확률로 변환 (-1~1 → 0~1)
    # 시그모이드 대신 선형 변환 사용 (더 직관적)
    probability = (raw_score + 1) / 2
    probability = max(0.0, min(1.0, probability))  # 0~1 범위로 클립
    
    # 7. 신뢰도 계산 (차원 간 일관성)
    import numpy as np
    std_dev = np.std([sim_e, sim_n, sim_d])
    confidence = 1 - min(std_dev, 1.0)  # 분산이 낮을수록 신뢰도 높음
    
    # 8. 상세 분석
    breakdown = {
        "emotion_similarity": round(float(sim_e), 3),
        "narrative_similarity": round(float(sim_n), 3),
        "ending_similarity": round(float(sim_d), 3),
        "boost_score": round(float(boost_score), 3),
        "dislike_penalty": round(float(dislike_penalty), 3),
        "top_factors": _get_top_factors(sim_e, sim_n, sim_d)
    }
    
    return {
        "probability": round(float(probability), 3),
        "confidence": round(float(confidence), 3),
        "raw_score": round(float(raw_score), 3),
        "breakdown": breakdown
    }


# 레거시 호환용 (기존 코드와의 호환성 유지)
def compute_score(user_profile: Dict, movie_profile: Dict, dislikes: List[str], w_e=0.5, w_n=0.3, w_d=0.2, penalty_weight=0.7, boost_tags: List[str] = None, boost_weight: float = 0.5):
    """
    레거시 함수 - 기존 코드와의 호환성 유지
    새로운 코드에서는 calculate_satisfaction_probability 사용 권장
    """
    result = calculate_satisfaction_probability(
        user_profile, 
        movie_profile, 
        dislikes,
        boost_tags=boost_tags if boost_tags else [],
        weights={"emotion": w_e, "narrative": w_n, "ending": w_d},
        penalty_weight=penalty_weight,
        boost_weight=boost_weight
    )
    
    # 기존 반환 형식 유지 (raw, match)
    match = sigmoid(result['raw_score'])
    return result['raw_score'], match



# CLI 옵션
# 사용자 프로필 생성 (텍스트 → 정서 벡터)
# 각 영화와 비교 (compute_score 호출)
# 매칭률 기준 정렬 (높은 순)
# 상위 N개 출력
def main():
    parser = argparse.ArgumentParser(description='A-3 Taste Simulator (Cosine + Penalty + Sigmoid)')
    parser.add_argument('--movies', default='movies_dataset_final.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-text', required=True)
    parser.add_argument('--dislikes', default='')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()

    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    movies = movie_a_2.load_json(args.movies)

    # Build user profile from text
    user_profile = {
        'emotion_scores': movie_a_2.score_tags(args.user_text, taxonomy['emotion']['tags']),
        'narrative_traits': movie_a_2.score_tags(args.user_text, taxonomy['story_flow']['tags']),
        'ending_preference': {
            'happy': movie_a_2.stable_score(args.user_text, 'ending_happy'),
            'open': movie_a_2.stable_score(args.user_text, 'ending_open'),
            'bittersweet': movie_a_2.stable_score(args.user_text, 'ending_bittersweet'),
        },
    }

    dislikes = [t.strip() for t in args.dislikes.split(',') if t.strip()]

    scored = []
    for m in movies:
        mp = movie_a_2.build_profile(m, taxonomy)
        
        # 새로운 확률 계산 함수 사용
        result = calculate_satisfaction_probability(
            user_profile, 
            mp, 
            dislikes,
            penalty_weight=0.7
        )
        
        scored.append({
            'movie_id': m.get('id'),
            'title': m.get('title'),
            'satisfaction_probability': result['probability'],
            'confidence': result['confidence'],
            'raw_score': result['raw_score'],
            'match_rate': round(result['probability'] * 100, 2),  # 백분율 표시
            'breakdown': result['breakdown']
        })

    scored.sort(key=lambda x: x['satisfaction_probability'], reverse=True)

    print(json.dumps(scored[: args.limit], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
