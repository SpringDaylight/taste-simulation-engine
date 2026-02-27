import math
from typing import Dict, List


def _cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _align_vector(d: Dict[str, float], keys: List[str]) -> List[float]:
    return [float(d.get(k, 0.0)) for k in keys]


def _calculate_dislike_penalty(movie_profile: Dict, dislikes: List[str]) -> float:
    penalty = 0.0
    categories = ["emotion_scores", "narrative_traits", "direction_mood", "character_relationship"]
    for category in categories:
        if category in movie_profile:
            for tag in dislikes:
                if tag in movie_profile[category]:
                    penalty += float(movie_profile[category][tag])
    return penalty


def _calculate_boost_score(movie_profile: Dict, boost_tags: List[str]) -> float:
    boost = 0.0
    categories = ["emotion_scores", "narrative_traits", "direction_mood", "character_relationship"]
    for category in categories:
        if category in movie_profile:
            for tag in boost_tags:
                if tag in movie_profile[category]:
                    boost += float(movie_profile[category][tag])
    return boost


def _top_factors(sim_e: float, sim_n: float, sim_d: float) -> List[str]:
    factors = [
        ("정서 톤", sim_e),
        ("서사 초점", sim_n),
        ("결말 취향", sim_d),
    ]
    factors.sort(key=lambda x: x[1], reverse=True)
    return [f[0] for f in factors[:2]]


def calculate_satisfaction_probability(
    user_profile: Dict,
    movie_profile: Dict,
    dislikes: List[str] | None = None,
    boost_tags: List[str] | None = None,
    weights: Dict[str, float] | None = None,
    penalty_weight: float = 0.7,
    boost_weight: float = 0.5,
) -> Dict:
    if dislikes is None:
        dislikes = []
    if boost_tags is None:
        boost_tags = []
    if weights is None:
        weights = {"emotion": 0.5, "narrative": 0.3, "ending": 0.2}

    e_keys = list(user_profile.get("emotion_scores", {}).keys())
    n_keys = list(user_profile.get("narrative_traits", {}).keys())
    d_keys = list(user_profile.get("ending_preference", {}).keys())

    sim_e = _cosine_sim(
        _align_vector(user_profile.get("emotion_scores", {}), e_keys),
        _align_vector(movie_profile.get("emotion_scores", {}), e_keys),
    )
    sim_n = _cosine_sim(
        _align_vector(user_profile.get("narrative_traits", {}), n_keys),
        _align_vector(movie_profile.get("narrative_traits", {}), n_keys),
    )
    sim_d = _cosine_sim(
        _align_vector(user_profile.get("ending_preference", {}), d_keys),
        _align_vector(movie_profile.get("ending_preference", {}), d_keys),
    )

    boost_score = _calculate_boost_score(movie_profile, boost_tags)
    dislike_penalty = _calculate_dislike_penalty(movie_profile, dislikes)

    w_e = weights.get("emotion", 0.5)
    w_n = weights.get("narrative", 0.3)
    w_d = weights.get("ending", 0.2)

    raw_score = (
        (w_e * sim_e + w_n * sim_n + w_d * sim_d)
        + (boost_weight * boost_score)
        - (penalty_weight * dislike_penalty)
    )

    probability = (raw_score + 1) / 2
    probability = max(0.0, min(1.0, probability))

    sims = [sim_e, sim_n, sim_d]
    mean = sum(sims) / len(sims)
    variance = sum((x - mean) ** 2 for x in sims) / len(sims)
    confidence = 1 - min(math.sqrt(variance), 1.0)

    breakdown = {
        "emotion_similarity": round(sim_e, 3),
        "narrative_similarity": round(sim_n, 3),
        "ending_similarity": round(sim_d, 3),
        "boost_score": round(boost_score, 3),
        "dislike_penalty": round(dislike_penalty, 3),
        "top_factors": _top_factors(sim_e, sim_n, sim_d),
    }

    return {
        "probability": round(probability, 3),
        "confidence": round(confidence, 3),
        "raw_score": round(raw_score, 3),
        "breakdown": breakdown,
    }


def predict_satisfaction(payload: dict) -> dict:
    """
    A-3: 사용자 + 영화 -> 만족 확률 계산
    """
    user_profile = payload.get("user_profile", {})
    movie_profile = payload.get("movie_profile", {})
    dislikes = payload.get("dislike_tags") or user_profile.get("dislike_tags") or []
    boost_tags = payload.get("boost_tags") or user_profile.get("boost_tags") or []

    result = calculate_satisfaction_probability(
        user_profile=user_profile,
        movie_profile=movie_profile,
        dislikes=dislikes,
        boost_tags=boost_tags,
    )

    return {
        "movie_id": movie_profile.get("movie_id"),
        "title": movie_profile.get("title", "Unknown"),
        "probability": result["probability"],
        "confidence": result["confidence"],
        "raw_score": result["raw_score"],
        "match_rate": round(result["probability"] * 100, 2),
        "breakdown": result["breakdown"],
    }
