
import os
import json
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session
# from database import db  <-- Removed
from models import User, FlavorStat, ThemeInventory, QuestionHistory

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
    def __init__(self, user_id: str, db: Session):
        self.user_id = user_id
        self.db = db
        # Bedrock 클라이언트 (Core에 보관)
        self.bedrock_client = None
        
        # 사용자 존재 확인 및 초기화는 필요 시 외부나 get_user에서 처리하도록 변경
        # 여기서는 DB가 이미 초기화되었다고 가정

    def _get_user_model(self) -> User:
        """DB에서 유저 객체 조회 (없으면 생성)"""
        # Flask: User.query.filter_by(username=self.user_id).first()
        # FastAPI: self.db.query(User).filter(User.username == self.user_id).first() (assuming username is mapped, but wait, User.id is String in Bolrea)
        # In models_merged.py: id = Column(String, primary_key=True), name = Column(String)...
        # In original core.py: username=self.user_id.
        # But Bolrea User model uses `id`. I should use `id`.
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            user = self._init_user()
        return user

    def _init_user(self) -> User:
        """신규 사용자 초기화"""
        new_user = User(
            id=self.user_id,    # Changed from username
            name=self.user_id,  # Set name defaut to ID
            level=1,
            exp=0,
            popcorn=0,
            main_flavor="Sweet",
            stage="Egg",
            created_at=datetime.utcnow()
        )
        self.db.add(new_user)
        
        # 기본 테마 추가
        basic_theme = ThemeInventory(user=new_user, theme_id="basic", is_applied=True)
        self.db.add(basic_theme)
        
        # Flavor Stats 초기화
        for f in FLAVORS.keys():
            stat = FlavorStat(user=new_user, flavor_name=f, score=0)
            self.db.add(stat)

        self.db.commit()
        print(f"🎉 환영합니다! 당신의 리뷰몽 '알'이 생성되었습니다.")
        return new_user

    def get_user_data(self) -> Dict:
        """User 객체를 Dictionary 형태로 변환하여 반환 (하위 호환성 유지)"""
        user = self._get_user_model()
        
        # Flavor Stats 변환
        f_stats = {fs.flavor_name: fs.score for fs in user.flavor_stats}
        for f in FLAVORS.keys():
            if f not in f_stats:
                f_stats[f] = 0
                
        # Inventory 변환
        owned = [item.theme_id for item in user.inventory]
        applied = "basic"
        for item in user.inventory:
            if item.is_applied:
                applied = item.theme_id
                break
                
        # History 변환
        history = []
        for h in user.history:
            history.append({
                "date": h.date,
                "question": h.question,
                "answer": h.answer
            })
        
        return {
            "user_id": user.id, # Changed from username
            "level": user.level,
            "exp": user.exp,
            "popcorn": user.popcorn,
            "main_flavor": user.main_flavor,
            "stage": user.stage, # DB에 저장된 stage 사용
            "last_feeding_date": user.last_feeding_date,
            "last_question_date": user.last_question_date,
            "current_question_index": user.current_question_index,
            "flavor_stats": f_stats,
            "owned_themes": owned,
            "applied_theme": applied,
            "question_history": history
        }

    def _update_user_data(self, key: str, value):
        """단일 필드 업데이트 (DB 반영)"""
        user = self._get_user_model()
        if hasattr(user, key):
            setattr(user, key, value)
            self.db.commit()

    def add_exp(self, amount: int):
        """경험치 획득 및 레벨업 체크"""
        user = self._get_user_model()
        user.exp += amount
        
        # 레벨업 체크
        current_level = user.level
        next_level = current_level + 1
        
        leveled_up = False
        if current_level < 30:
            while next_level in LEVEL_TABLE and user.exp >= LEVEL_TABLE[next_level]:
                current_level = next_level
                print(f"\n🎊 축하합니다! 레벨이 올랐습니다! Lv.{current_level}")
                next_level += 1
                leveled_up = True
        
        if leveled_up:
            user.level = current_level
            # 레벨업 시 Stage 업데이트
            new_stage = self._calculate_stage(current_level)
            if new_stage != user.stage:
                user.stage = new_stage
                
        self.db.commit()

    def add_popcorn(self, amount: int):
        """팝콘(재화) 획득"""
        user = self._get_user_model()
        user.popcorn += amount
        self.db.commit()

    # ==========================================
    # 헬퍼 메소드 (프론트엔드 지원)
    # ==========================================
    def _calculate_stage(self, level: int) -> str:
        """레벨 기반 성장 단계 계산"""
        stage = "Egg"
        for s_lvl in sorted(GROWTH_STAGES.keys()):
            if level >= s_lvl:
                stage = GROWTH_STAGES[s_lvl]
        return stage

    def get_current_stage(self) -> str:
        """현재 레벨에 따른 성장 단계 반환 (DB 값 또는 계산)"""
        user = self._get_user_model()
        # DB에 저장된 stage가 있으면 사용, 아니면 재계산
        if user.stage:
            return user.stage
        return self._calculate_stage(user.level)

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
