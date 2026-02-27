"""
A-1: 사용자 텍스트 기반 취향 분석
사용자가 입력한 텍스트(리뷰, 소감, 질의)를 분석하여 정서·서사 기반 취향 벡터 생성
"""
import hashlib
import re
from typing import Dict, List
from domain.taxonomy import load_taxonomy


def _stable_score(text: str, tag: str) -> float:
    """Deterministic score generation for fallback"""
    h = hashlib.sha256((text + '||' + tag).encode('utf-8')).hexdigest()
    v = int(h[:8], 16) / 0xFFFFFFFF
    return round(v, 3)


def _score_tags(text: str, tags: List[str]) -> Dict[str, float]:
    """Generate scores for all tags"""
    return {tag: _stable_score(text, tag) for tag in tags}


def _detect_negation_fallback(text: str, taxonomy: Dict) -> Dict:
    """
    규칙 기반 부정어 감지 (LLM 없이도 작동)
    v3: 연결어 처리 + 부분 매칭 + 키워드 확장
    """
    # 부정어 키워드 (확장)
    NEGATION_KEYWORDS = [
        "싫어", "제외", "말고", "빼고", "아니", "안", "싫다",
        "NO", "싫고", "제거", "거부", "없이"
    ]
    
    # 긍정어 키워드
    POSITIVE_KEYWORDS = [
        "좋아", "추천", "원해", "보고 싶", "찾아", "선호"
    ]
    
    # 태그 매핑 (부분 매칭용)
    TAG_MAP = {
        "무서": "무서워요",
        "긴장": "긴장돼요",
        "우울": "우울해요",
        "웃": "웃겨요",
        "밝": "밝은 분위기예요",
        "어둡": "어두운 분위기예요",
        "슬": "슬퍼요",
        "감동": "감동적이에요",
        "따뜻": "따뜻해요",
        "힐링": "힐링돼요",
        "여운": "여운이 길어요",
        "희망": "희망적이에요",
        "설레": "설레요",
        "로맨": "로맨틱해요",
        "통쾌": "통쾌해요",
        "잔잔": "잔잔해요",
        "현실": "현실적이에요",
        "몽환": "몽환적이에요",
        "소름": "소름 돋아요"
    }
    
    # 연결어 전처리 ("무섭거나" -> "무섭, ")
    text = re.sub(r'[하]?거나', ',', text)
    
    exclude_tags = []
    include_tags = []
    
    # 문장 분리
    sentences = re.split(r'[.!?;]', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # 부정어 감지
        has_negation = any(neg in sentence for neg in NEGATION_KEYWORDS)
        has_positive = any(pos in sentence for pos in POSITIVE_KEYWORDS)
        
        # 태그 추출
        found_tags = []
        for keyword, tag in TAG_MAP.items():
            if keyword in sentence:
                found_tags.append(tag)
        
        # 분류
        if has_negation and not has_positive:
            # 부정어만 있음 -> 제외
            exclude_tags.extend(found_tags)
        elif has_positive and not has_negation:
            # 긍정어만 있음 -> 포함
            include_tags.extend(found_tags)
        elif has_negation and has_positive:
            # 둘 다 있음 -> 부정어 앞은 제외, 긍정어 뒤는 포함
            words = sentence.split()
            neg_idx = next((i for i, w in enumerate(words) if any(neg in w for neg in NEGATION_KEYWORDS)), -1)
            pos_idx = next((i for i, w in enumerate(words) if any(pos in w for pos in POSITIVE_KEYWORDS)), -1)
            
            if neg_idx < pos_idx:
                # "스릴러 말고 로맨스 추천"
                for tag in found_tags:
                    if any(kw in sentence[:sentence.find(words[pos_idx])] for kw, t in TAG_MAP.items() if t == tag):
                        exclude_tags.append(tag)
                    else:
                        include_tags.append(tag)
            else:
                # "로맨스 좋아하는데 무서운 건 싫어"
                for tag in found_tags:
                    if any(kw in sentence[sentence.find(words[neg_idx]):] for kw, t in TAG_MAP.items() if t == tag):
                        exclude_tags.append(tag)
                    else:
                        include_tags.append(tag)
    
    # 중복 제거 및 충돌 해결 (exclude 우선)
    exclude_tags = list(set(exclude_tags))
    include_tags = [t for t in set(include_tags) if t not in exclude_tags]
    
    return {
        "exclude_tags": exclude_tags,
        "include_tags": include_tags
    }


def analyze_preference(payload: dict) -> dict:
    """
    A-1: 사용자 텍스트 -> 취향 벡터
    
    Args:
        payload: {
            "text": "사용자 입력 텍스트",
            "dislikes": "싫어하는 것 (선택, 쉼표 구분)"
        }
    
    Returns:
        {
            "user_text": str,
            "emotion_scores": Dict[str, float],
            "narrative_traits": Dict[str, float],
            "direction_mood": Dict[str, float],
            "character_relationship": Dict[str, float],
            "ending_preference": Dict[str, float],
            "dislike_tags": List[str],
            "boost_tags": List[str]
        }
    """
    text = payload.get("text", "")
    dislikes_text = payload.get("dislikes", "")
    
    # 명시적 dislike 태그 파싱
    explicit_dislike_tags = []
    if isinstance(dislikes_text, str) and dislikes_text.strip():
        explicit_dislike_tags = [t.strip() for t in dislikes_text.split(",") if t.strip()]
    
    taxonomy = load_taxonomy()
    e_keys = taxonomy.get("emotion", {}).get("tags", [])
    n_keys = taxonomy.get("story_flow", {}).get("tags", [])
    d_keys = taxonomy.get("direction_mood", {}).get("tags", [])
    c_keys = taxonomy.get("character_relationship", {}).get("tags", [])
    
    # 부정어 자동 감지
    negation_result = _detect_negation_fallback(text, taxonomy)
    auto_exclude_tags = negation_result["exclude_tags"]
    auto_include_tags = negation_result["include_tags"]
    
    # 최종 dislike/boost 태그 결합
    all_dislike_tags = list(set(explicit_dislike_tags + auto_exclude_tags))
    boost_tags = auto_include_tags
    
    # 기본 점수 생성
    emotion_scores = _score_tags(text, e_keys)
    narrative_traits = _score_tags(text, n_keys)
    direction_mood = _score_tags(text, d_keys)
    character_relationship = _score_tags(text, c_keys)
    
    ending_preference = {
        "happy": _stable_score(text, "ending_happy"),
        "open": _stable_score(text, "ending_open"),
        "bittersweet": _stable_score(text, "ending_bittersweet"),
    }
    
    return {
        "user_text": text,
        "emotion_scores": emotion_scores,
        "narrative_traits": narrative_traits,
        "direction_mood": direction_mood,
        "character_relationship": character_relationship,
        "ending_preference": ending_preference,
        "dislike_tags": all_dislike_tags,
        "boost_tags": boost_tags
    }
