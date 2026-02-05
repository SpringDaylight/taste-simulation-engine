## A-3 취향 시뮬레이터

import argparse
import json
import math
from typing import Dict, List

import moviea2


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


# 사용자 취향과 영화 취향의 유사도 계산
def compute_score(user_profile: Dict, movie_profile: Dict, dislikes: List[str], w_e=0.5, w_n=0.3, w_d=0.2, penalty_weight=0.7):
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

    penalty = 0.0
    for tag in dislikes:
        if tag in movie_profile['emotion_scores']:
            penalty += movie_profile['emotion_scores'][tag]

    raw = (w_e * sim_e + w_n * sim_n + w_d * sim_d) - (penalty_weight * penalty)
    match = sigmoid(raw)
    return raw, match



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

    taxonomy = moviea2.load_taxonomy(args.taxonomy)
    movies = moviea2.load_json(args.movies)

    # Build user profile from text
    user_profile = {
        'emotion_scores': moviea2.score_tags(args.user_text, taxonomy['emotion']['tags']),
        'narrative_traits': moviea2.score_tags(args.user_text, taxonomy['story_flow']['tags']),
        'ending_preference': {
            'happy': moviea2.stable_score(args.user_text, 'ending_happy'),
            'open': moviea2.stable_score(args.user_text, 'ending_open'),
            'bittersweet': moviea2.stable_score(args.user_text, 'ending_bittersweet'),
        },
    }

    dislikes = [t.strip() for t in args.dislikes.split(',') if t.strip()]

    scored = []
    for m in movies:
        mp = moviea2.build_profile(m, taxonomy)
        raw, match = compute_score(user_profile, mp, dislikes)
        scored.append({
            'movie_id': m.get('id'),
            'title': m.get('title'),
            'raw_score': round(raw, 4),
            'match_rate': round(match * 100, 2),
        })

    scored.sort(key=lambda x: x['match_rate'], reverse=True)

    print(json.dumps(scored[: args.limit], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
