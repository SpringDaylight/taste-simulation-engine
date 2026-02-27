# 감성 검색 로직
def emotional_search(payload: dict) -> dict:
    """
    A-5: 의도 분류 + 쿼리 확장 + 하이브리드 검색 페이로드
    (taste-simulation-engine 형식 맞춤)
    """
    text = payload.get("text", "")

    from domain.taxonomy import load_taxonomy

    # taste-simulation-engine의 키워드/태그 확장 매핑
    keyword_map = {
        "우울": "우울해요",
        "슬프": "슬퍼요",
        "긴장": "긴장돼요",
        "무서": "무서워요",
        "설레": "설레요",
        "로맨": "로맨틱해요",
        "웃기": "웃겨요",
        "밝": "밝은 분위기예요",
        "어둡": "어두운 분위기예요",
        "잔잔": "잔잔해요",
        "현실": "현실적이에요",
        "몽환": "몽환적이에요",
        "감동": "감동적이에요",
        "힐링": "힐링돼요",
        "희망": "희망적이에요",
        "통쾌": "통쾌해요",
    }

    taxonomy = load_taxonomy()
    emotion_tags = taxonomy.get("emotion", {}).get("tags", [])
    emotion_scores = {tag: 0.0 for tag in emotion_tags}
    if isinstance(text, str):
        for k, tag in keyword_map.items():
            if k in text:
                if tag in emotion_scores:
                    emotion_scores[tag] = max(emotion_scores.get(tag, 0.0), 0.8)

    if isinstance(text, str):
        if "무겁지 않" in text or "가볍" in text:
            emotion_scores["밝은 분위기예요"] = max(
                emotion_scores.get("밝은 분위기예요", 0.0), 0.7
            )
            emotion_scores["잔잔해요"] = max(
                emotion_scores.get("잔잔해요", 0.0), 0.6
            )

    if max(emotion_scores.values()) == 0.0:
        # fallback deterministic scores
        emotion_scores = {tag: 0.0 for tag in emotion_tags}
        if "감동적이에요" in emotion_scores:
            emotion_scores["감동적이에요"] = 0.6
        if "잔잔해요" in emotion_scores:
            emotion_scores["잔잔해요"] = 0.4
    query_vector = [emotion_scores[tag] for tag in emotion_tags]
    filters = []
    genres = payload.get("genres") or []
    if genres:
        filters.append({"terms": {"genres": genres}})
    year_from = payload.get("year_from")
    year_to = payload.get("year_to")
    if year_from is not None or year_to is not None:
        rng = {}
        if year_from is not None:
            rng["gte"] = year_from
        if year_to is not None:
            rng["lte"] = year_to
        filters.append({"range": {"release_year": rng}})

    return {
        "intent": "search",
        "expanded_query": {
            "emotion_scores": emotion_scores
        },
        "hybrid_query": {
            "query": {
                "bool": {
                    "must": [],
                    "filter": filters
                }
            },
            "knn": {
                "field": "emotion_vector",
                "query_vector": query_vector,
                "k": 50,
                "num_candidates": 200
            }
        }
    }
