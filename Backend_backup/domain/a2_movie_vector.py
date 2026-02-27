"""
A-2: 영화 특성 벡터링
영화 메타데이터를 분석하여 정서·서사 기반 특성 벡터 생성
"""
import hashlib
from typing import Dict, List
from domain.taxonomy import load_taxonomy


def _stable_score(text: str, tag: str) -> float:
    """Deterministic score generation"""
    h = hashlib.sha256((text + '||' + tag).encode('utf-8')).hexdigest()
    v = int(h[:8], 16) / 0xFFFFFFFF
    return round(v, 3)


def _score_tags(text: str, tags: List[str]) -> Dict[str, float]:
    """Generate scores for all tags"""
    return {tag: _stable_score(text, tag) for tag in tags}


def _movie_text(movie_payload: dict) -> str:
    """영화 데이터에서 분석용 텍스트 추출"""
    parts = []
    
    # 기본 정보
    for key in ["title", "overview", "synopsis"]:
        val = movie_payload.get(key)
        if val:
            parts.append(str(val))
    
    # 리스트 형태 정보
    for key in ["keywords", "genres", "directors", "cast"]:
        val = movie_payload.get(key)
        if isinstance(val, list):
            parts.extend([str(v) for v in val])
    
    return " ".join(parts)


def _top_tags(scores: dict, top_n: int = 3) -> List[str]:
    """상위 N개 태그 추출"""
    return [k for k, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]]


def process_movie_vector(movie_payload: dict) -> dict:
    """
    A-2: 영화 입력 -> 영화 프로필
    
    Args:
        movie_payload: {
            "movie_id": int or str,
            "title": str,
            "overview": str (선택),
            "synopsis": str (선택),
            "keywords": List[str] (선택),
            "genres": List[str] (선택),
            "directors": List[str] (선택),
            "cast": List[str] (선택)
        }
    
    Returns:
        {
            "movie_id": int or str,
            "title": str,
            "emotion_scores": Dict[str, float],
            "narrative_traits": Dict[str, float],
            "direction_mood": Dict[str, float],
            "character_relationship": Dict[str, float],
            "ending_preference": Dict[str, float],
            "embedding_text": str,
            "embedding": List[float] (빈 리스트, 향후 Bedrock 연동용)
        }
    """
    movie_id = movie_payload.get("movie_id", "dummy_movie")
    title = movie_payload.get("title", "Dummy Movie")
    text = _movie_text(movie_payload)
    
    taxonomy = load_taxonomy()
    e_keys = taxonomy.get("emotion", {}).get("tags", [])
    n_keys = taxonomy.get("story_flow", {}).get("tags", [])
    d_keys = taxonomy.get("direction_mood", {}).get("tags", [])
    c_keys = taxonomy.get("character_relationship", {}).get("tags", [])
    
    # 각 차원별 점수 계산
    emotion_scores = _score_tags(text, e_keys)
    narrative_traits = _score_tags(text, n_keys)
    direction_mood = _score_tags(text, d_keys)
    character_relationship = _score_tags(text, c_keys)
    
    ending_preference = {
        "happy": _stable_score(text, "ending_happy"),
        "open": _stable_score(text, "ending_open"),
        "bittersweet": _stable_score(text, "ending_bittersweet"),
    }
    
    # 임베딩 텍스트 생성 (검색용)
    top_emotions = ", ".join(_top_tags(emotion_scores))
    top_narrative = ", ".join(_top_tags(narrative_traits))
    embedding_text = f"Title: {title}. Emotions: {top_emotions}. Narrative: {top_narrative}."
    
    profile = {
        "movie_id": movie_id,
        "title": title,
        "emotion_scores": emotion_scores,
        "narrative_traits": narrative_traits,
        "direction_mood": direction_mood,
        "character_relationship": character_relationship,
        "ending_preference": ending_preference,
        "embedding_text": embedding_text,
        "embedding": []  # 향후 Bedrock Titan Embedding 연동용
    }
    
    return profile
