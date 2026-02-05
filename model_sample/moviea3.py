## A-3 취향 시뮬레이터

import argparse
import json
import math
from typing import Dict, List

import moviea2


def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def sigmoid(x: float, k: float = 8.0, x0: float = 0.5) -> float:
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


def align_vector(d: Dict[str, float], keys: List[str]) -> List[float]:
    return [d.get(k, 0.0) for k in keys]


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


def main():
    parser = argparse.ArgumentParser(description='A-3 Taste Simulator (Cosine + Penalty + Sigmoid)')
    parser.add_argument('--movies', default='movies_dataset_final.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-text', required=True)
    parser.add_argument('--dislikes', default='')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()

    taxonomy = moviea1.load_taxonomy(args.taxonomy)
    movies = moviea1.load_json(args.movies)

    # Build user profile from text
    user_profile = {
        'emotion_scores': moviea1.score_tags(args.user_text, taxonomy['emotion']['tags']),
        'narrative_traits': moviea1.score_tags(args.user_text, taxonomy['story_flow']['tags']),
        'ending_preference': {
            'happy': moviea1.stable_score(args.user_text, 'ending_happy'),
            'open': moviea1.stable_score(args.user_text, 'ending_open'),
            'bittersweet': moviea1.stable_score(args.user_text, 'ending_bittersweet'),
        },
    }

    dislikes = [t.strip() for t in args.dislikes.split(',') if t.strip()]

    scored = []
    for m in movies:
        mp = moviea1.build_profile(m, taxonomy)
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
