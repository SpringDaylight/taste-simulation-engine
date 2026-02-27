import json
from pathlib import Path


def _default_taxonomy() -> dict:
    """기본 택소노미 (fallback용)"""
    return {
        "emotion": {
            "description": "영화를 보면서 느끼는 감정적 반응",
            "tags": [
                "감동적이에요", "따뜻해요", "힐링돼요", "슬퍼요", "여운이 길어요",
                "희망적이에요", "우울해요", "긴장돼요", "무서워요", "소름 돋아요",
                "설레요", "로맨틱해요", "통쾌해요", "웃겨요", "밝은 분위기예요",
                "어두운 분위기예요", "잔잔해요", "감정 기복이 커요", "현실적이에요", "몽환적이에요"
            ]
        },
        "story_flow": {
            "description": "영화의 서사 진행과 페이싱에 대한 평가",
            "tags": [
                "전개가 빨라요", "전개가 느긋해요", "초반부터 몰입돼요", "후반부가 강해요",
                "반전이 많아요", "반전이 한 번 크게 있어요", "복선이 많아요", "이해하기 쉬워요",
                "생각하면서 봐야 해요", "결말이 인상적이에요", "열린 결말이에요", "기승전결이 뚜렷해요",
                "일상적인 이야기예요", "사건이 계속 이어져요", "에피소드형 구성이에요", "점점 고조돼요",
                "중반이 지루하지 않아요", "전개가 예측 가능해요", "전개가 예측 불가능해요", "스토리가 단순해요"
            ]
        },
        "direction_mood": {
            "description": "영화의 연출, 분위기, 스타일에 대한 평가",
            "tags": [
                "영상미가 좋아요", "색감이 예뻐요", "화면이 어두운 편이에요", "화면이 밝은 편이에요",
                "음악이 인상적이에요", "분위기 연출이 좋아요", "감각적인 연출이에요", "현실감 있는 연출이에요",
                "스타일이 독특해요", "잔잔한 연출이에요", "몰입감 있는 연출이에요", "연출이 과하지 않아요",
                "연출이 화려해요", "카메라 움직임이 인상적이에요", "배경이 매력적이에요", "공간 연출이 좋아요",
                "전체 분위기가 차분해요", "전체 분위기가 강렬해요", "미장센이 좋아요", "예술적인 느낌이에요"
            ]
        },
        "character_relationship": {
            "description": "영화의 캐릭터와 인물 관계에 대한 평가",
            "tags": [
                "주인공이 매력적이에요", "조연 캐릭터가 좋아요", "캐릭터 성장이 잘 보여요", "캐릭터에 공감돼요",
                "인물 간 관계가 중요해요", "가족 관계 이야기예요", "친구 관계 이야기예요", "연인 관계 이야기예요",
                "팀플레이가 중심이에요", "갈등 관계가 흥미로워요", "악역이 인상적이에요", "인물이 입체적이에요",
                "인물이 현실적이에요", "인물이 독특해요", "대사가 좋아요", "감정 표현이 풍부해요",
                "인물 중심 전개예요", "여러 인물이 골고루 비중이 있어요", "한 인물 중심 이야기예요", "관계 변화가 잘 느껴져요"
            ]
        }
    }


def load_taxonomy() -> dict:
    """
    Taxonomy 파일 로드
    우선순위:
    1. ml/data/emotion_tag.json
    2. 기본 택소노미 (fallback)
    """
    # 현재 파일 기준으로 프로젝트 루트 찾기
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent  # domain -> backend root
    
    # ML 데이터 경로
    ml_taxonomy_path = project_root / "ml" / "data" / "emotion_tag.json"
    
    try:
        if ml_taxonomy_path.exists():
            with ml_taxonomy_path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load taxonomy from {ml_taxonomy_path}: {e}")
    
    # Fallback
    return _default_taxonomy()
