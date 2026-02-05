import argparse
import hashlib
import json
import os
from typing import Dict, List


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 정서 태그 taxonomy(템플릿) 생성 - LLM으로 정서 태그 추출 시 사용
def load_taxonomy(path: str = 'emotion_tag.json'):
    return load_json(path)

# 정서 태그 값으로 더미 값 입력(LLM 연결 후 삭제)
def stable_score(text: str, tag: str) -> float:
    h = hashlib.sha256((text + '||' + tag).encode('utf-8')).hexdigest()
    v = int(h[:8], 16) / 0xFFFFFFFF
    return round(v, 3)

# LLM 활용 실제 분석 로직(추가 필요)
def analyze_with_llm(text: str, taxonomy: Dict) -> Dict:
    # 1. 프롬프트 생성 (Taxonomy 리스트 포함)
    # 2. LLM API 호출 (OpenAI JSON Mode 등)
    # 3. 결과 파싱 및 반환
    pass


def score_tags(text: str, tags: List[str]) -> Dict[str, float]:
    return {tag: stable_score(text, tag) for tag in tags}

# 텍스트 추출
def movie_text(movie: Dict) -> str:
    parts = []
    for key in ['title', 'overview']:
        if movie.get(key):
            parts.append(str(movie[key]))
    for key in ['keywords', 'genres', 'directors', 'cast']:
        val = movie.get(key)
        if isinstance(val, list):
            parts.extend([str(v) for v in val])
    return ' '.join(parts)

# 영화 데이터셋 설정(정서 태그 추가)
def build_profile(movie: Dict, taxonomy: Dict) -> Dict:
    text = movie_text(movie)
    emotion_tags = taxonomy['emotion']['tags']
    narrative_tags = taxonomy['story_flow']['tags']

    profile = {
        'movie_id': movie.get('id'),
        'title': movie.get('title'),
        'emotion_scores': score_tags(text, emotion_tags),
        'narrative_traits': score_tags(text, narrative_tags),
        'ending_preference': {
            'happy': stable_score(text, 'ending_happy'),
            'open': stable_score(text, 'ending_open'),
            'bittersweet': stable_score(text, 'ending_bittersweet'),
        },
    }
    return profile

# 임베딩 벡터 생성 규칙 설정(추가 필요)
def embedding_text():
    pass

# 임베딩 벡터 생성 및 OpenSearch로 저장(추가 필요)
def embedding_vector():
    pass


def main():
    parser = argparse.ArgumentParser(description='A-1 Emotion Taxonomy Scoring (dummy LLM)')
    parser.add_argument('--movies', default='movies_dataset_final.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--movie-id', type=int, default=None)
    parser.add_argument('--output', default=None)
    parser.add_argument('--pretty', action='store_true')
    args = parser.parse_args()

    taxonomy = load_taxonomy(args.taxonomy)
    movies = load_json(args.movies)

    if args.movie_id is not None:
        movies = [m for m in movies if m.get('id') == args.movie_id]

    if args.limit is not None:
        movies = movies[: args.limit]

    profiles = [build_profile(m, taxonomy) for m in movies]

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2 if args.pretty else None)
    else:
        print(json.dumps(profiles, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == '__main__':
    main()
