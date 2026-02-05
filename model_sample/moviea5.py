# A-5 자연어 기반 감성 검색(LLM + RAG)

import argparse
import json
import re
from typing import Dict, List

import moviea2


KEYWORD_MAP = {
    '우울': '우울해요',
    '슬프': '슬퍼요',
    '긴장': '긴장돼요',
    '무서': '무서워요',
    '설레': '설레요',
    '로맨': '로맨틱해요',
    '웃기': '웃겨요',
    '밝': '밝은 분위기예요',
    '어둡': '어두운 분위기예요',
    '잔잔': '잔잔해요',
    '현실': '현실적이에요',
    '몽환': '몽환적이에요',
    '감동': '감동적이에요',
    '힐링': '힐링돼요',
    '희망': '희망적이에요',
    '통쾌': '통쾌해요',
}


def classify_intent(text: str) -> str:
    if re.search(r'추천|취향|좋아|싫어|선호', text):
        return 'preference_analysis'
    return 'search'


def expand_query(text: str, emotion_tags: List[str]) -> Dict[str, float]:
    scores = {tag: 0.0 for tag in emotion_tags}
    for k, tag in KEYWORD_MAP.items():
        if k in text:
            scores[tag] = max(scores[tag], 0.8)

    if '무겁지 않' in text or '가볍' in text:
        if '밝은 분위기예요' in scores:
            scores['밝은 분위기예요'] = max(scores['밝은 분위기예요'], 0.7)
        if '잔잔해요' in scores:
            scores['잔잔해요'] = max(scores['잔잔해요'], 0.6)

    # fallback: if nothing matched, use deterministic dummy scores
    if max(scores.values()) == 0.0:
        scores = moviea1.score_tags(text, emotion_tags)

    return scores


def build_hybrid_query(emotion_scores: Dict[str, float], filters: Dict, k=50, num_candidates=200):
    emotion_vector = [emotion_scores[k] for k in emotion_scores.keys()]

    bool_query = {'must': [], 'filter': []}
    genres = filters.get('genres')
    if genres:
        bool_query['filter'].append({'terms': {'genres': genres}})

    year_from = filters.get('year_from')
    year_to = filters.get('year_to')
    if year_from or year_to:
        rng = {}
        if year_from:
            rng['gte'] = year_from
        if year_to:
            rng['lte'] = year_to
        bool_query['filter'].append({'range': {'release_year': rng}})

    return {
        'query': {
            'bool': bool_query
        },
        'knn': {
            'field': 'emotion_vector',
            'query_vector': emotion_vector,
            'k': k,
            'num_candidates': num_candidates
        }
    }


def main():
    parser = argparse.ArgumentParser(description='A-5 Intent + Query Expansion + Hybrid Search (dummy)')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--text', required=True)
    parser.add_argument('--genres', default='')
    parser.add_argument('--year-from', type=int, default=None)
    parser.add_argument('--year-to', type=int, default=None)
    args = parser.parse_args()

    taxonomy = moviea1.load_taxonomy(args.taxonomy)
    emotion_tags = taxonomy['emotion']['tags']

    intent = classify_intent(args.text)
    expanded = expand_query(args.text, emotion_tags)

    filters = {
        'genres': [g.strip() for g in args.genres.split(',') if g.strip()],
        'year_from': args.year_from,
        'year_to': args.year_to,
    }

    hybrid_query = build_hybrid_query(expanded, filters)

    output = {
        'intent': intent,
        'expanded_query': {
            'emotion_scores': expanded
        },
        'hybrid_query': hybrid_query
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
