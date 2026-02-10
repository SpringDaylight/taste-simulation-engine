
import os
import json
from datetime import datetime
from typing import Dict, Optional

# ==========================================
# 상수 데이터 (Configuration)
# ==========================================

# 경험치 테이블 (Level Design)
LEVEL_TABLE = {
    1: 0,
    2: 50,      # 유아기 진입 (부화)
    3: 150,
    4: 300,
    5: 500,     # 1차 진화
    6: 800,
    7: 1200,
    8: 1700,
    9: 2300,
    10: 3000,   # 2차 진화
    15: 7500,
    20: 13500,  # 3차 진화
    25: 21500,
    30: 30000   # 최종 진화
}

# 성장 단계 명칭
GROWTH_STAGES = {
    1: "Egg",
    2: "Toddler",
    6: "Child",
    15: "Teen",
    26: "Adult"
}

# 캐릭터 이미지 매핑 (예시)
# 프론트엔드에서 assets/images/character/ 경로 하위에 위치시킬 파일명 생성 규칙
# 포맷: character_{stage}_{flavor}.png (단, Egg는 flavor 무관)

# 맛(Flavor) 속성
FLAVORS = {
    "Sweet":  {"name": "달콤",   "keywords": ["로맨스", "멜로", "사랑", "따뜻한", "힐링", "행복", "가족"]},
    "Spicy":  {"name": "매운",   "keywords": ["공포", "호러", "무서운", "충격", "긴장", "비명", "잔인"]},
    "Onion":  {"name": "어니언", "keywords": ["스릴러", "미스터리", "반전", "범인", "추리", "복잡", "심리"]},
    "Cheese": {"name": "치즈",   "keywords": ["액션", "히어로", "블록버스터", "폭발", "전투", "시원한", "통쾌"]},
    "Dark":   {"name": "초코",   "keywords": ["느와르", "범죄", "어두운", "피카레스크", "비극", "폭력", "지하"]},
    "Salty":  {"name": "소금",   "keywords": ["드라마", "다큐", "슬픈", "눈물", "감동", "현실", "고통"]},
    "Mint":   {"name": "민트",   "keywords": ["SF", "판타지", "우주", "미래", "마법", "독특한", "예술"]},
    "Original": {"name": "오리지널", "keywords": ["가족", "아이", "무난", "그냥", "보통", "킬링타임", "팝콘"]}
}


class MovieMongCore:
    def __init__(self, user_id: str, data_file: str = "moviemong_data.json"):
        self.user_id = user_id
        self.data_file = data_file
        self.data = self._load_data()
        
        # Bedrock 클라이언트 (Core에 보관)
        self.bedrock_client = None
        
        # 사용자 초기화
        if self.user_id not in self.data:
            self._init_user()

    def _load_data(self) -> Dict:
        """데이터 로드 및 정합성 체크"""
        if not os.path.exists(self.data_file):
            return {}
            
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 데이터 마이그레이션 (누락된 키 추가)
            modified = False
            for uid, udata in data.items():
                if "flavor_stats" in udata:
                    for f_key in FLAVORS.keys():
                        if f_key not in udata["flavor_stats"]:
                            udata["flavor_stats"][f_key] = 0
                            modified = True
            
            # 변경사항이 있으면 저장 (선택 사항이나, 여기선 메모리 상에서만 수정하고 나중에 저장될 때 반영되도록 함)
            # 하지만 _load_data는 초기화 시점에만 불리므로, 여기서 저장하는 것도 나쁘지 않음.
            if modified:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
            return data
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ 데이터 로드 중 오류: {e}")
            return {}

    def _save_data(self):
        """데이터 저장"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _init_user(self):
        """신규 사용자 초기화"""
        self.data[self.user_id] = {
            "level": 1,
            "exp": 0,
            "popcorn": 0,
            "flavor_stats": {k: 0 for k in FLAVORS.keys()},
            "main_flavor": "Sweet",  # 기본값
            "last_feeding_date": None,
            "last_question_date": None,
            "current_question_index": 0,
            "question_history": [],  # 질문/답변 기록
            "owned_themes": ["basic"], # 보유 테마
            "applied_theme": "basic",  # 현재 적용 테마
            "created_at": datetime.now().isoformat()
        }
        self._save_data()
        print(f"🎉 환영합니다! 당신의 리뷰몽 '알'이 생성되었습니다.")

    def get_user_data(self) -> Dict:
        return self.data[self.user_id]

    def _update_user_data(self, key: str, value):
        self.data[self.user_id][key] = value
        self._save_data()

    def add_exp(self, amount: int):
        """경험치 획득 및 레벨업 체크"""
        user_data = self.get_user_data()
        current_exp = user_data["exp"]
        current_level = user_data["level"]
        
        new_exp = current_exp + amount
        self.data[self.user_id]["exp"] = new_exp
        
        # 레벨업 체크
        next_level = current_level + 1
        
        if current_level >= 30:
            self._save_data()
            return

        while next_level in LEVEL_TABLE and new_exp >= LEVEL_TABLE[next_level]:
            current_level = next_level
            print(f"\n🎊 축하합니다! 레벨이 올랐습니다! Lv.{current_level}")
            next_level += 1
            
        self.data[self.user_id]["level"] = current_level
        self._save_data()

    def add_popcorn(self, amount: int):
        """팝콘(재화) 획득"""
        user_data = self.get_user_data()
        self.data[self.user_id]["popcorn"] = user_data["popcorn"] + amount
        self._save_data()

    # ==========================================
    # 헬퍼 메소드 (프론트엔드 지원)
    # ==========================================
    def get_current_stage(self) -> str:
        """현재 레벨에 따른 성장 단계 반환"""
        level = self.data[self.user_id]["level"]
        stage = "Egg" # Default
        for s_lvl in sorted(GROWTH_STAGES.keys()):
            if level >= s_lvl:
                stage = GROWTH_STAGES[s_lvl]
        return stage

    def get_character_image(self) -> str:
        """현재 상태에 맞는 이미지 파일명 반환"""
        stage = self.get_current_stage()
        
        # 사용자 제공 이미지 매핑
        IMAGE_MAP = {
            "Egg": "리뷰몽_1차.png",       # 1단계 (알)
            "Toddler": "리뷰몽_유아기.png", # 2단계 (유아기)
            "Child": "리뷰몽_2차.png",     # 3단계 (아동기)
            "Teen": "리뷰몽_3차.png",      # 4단계 (청소년기)
            "Adult": "리뷰몽_최종.png"     # 5단계 (성체)
        }
        
        return IMAGE_MAP.get(stage, "리뷰몽_1차.png")
