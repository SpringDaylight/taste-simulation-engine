
from typing import Dict, List, Optional
from typing import Dict, List, Optional
from datetime import datetime, date
import os

from .core import MovieMongCore, LEVEL_TABLE, GROWTH_STAGES, FLAVORS
from .question import DailyQuestionMixin
from .review import ReviewMixin
from .feeding import FeedingMixin
from .theme import ThemeMixin
from ai.analysis import embedding

class MovieMong(MovieMongCore, DailyQuestionMixin, ReviewMixin, FeedingMixin, ThemeMixin):
    """
    Review Mong Main Class.
    Inherits from functional mixins to provide a unified interface.
    """
    def __init__(self, user_id: str):
        # Initialize Core
        super().__init__(user_id)
        
        # Load Taxonomy (used by ReviewMixin)
        try:
            # 패키지 구조: .../model_sample/moviemong/__init__.py
            # 목표: .../data/emotion_tag.json
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            taxonomy_path = os.path.join(base_dir, "data", "emotion_tag.json")
            
            if os.path.exists(taxonomy_path):
                self.taxonomy = embedding.load_taxonomy(taxonomy_path)
            else:
                 # Fallback
                 self.taxonomy = embedding.load_taxonomy("data/emotion_tag.json")
        except:
                self.taxonomy = {}
                print("⚠️ Taxonomy 로드 실패: 기본 분석만 가능합니다.")

    def get_home_data(self) -> Dict:
        """홈 화면용 전체 데이터 집계 (프론트엔드 연동용)"""
        data = self.get_user_data()
        today = date.today().isoformat()
        
        # 레벨 정보
        lvl = data['level']
        
        # 다음 레벨 경험치 찾기
        next_lvl_exp = "MAX"
        for l in sorted(LEVEL_TABLE.keys()):
                break
                
        # 성장 단계 및 이미지 (Core 메소드 활용)
        stage = self.get_current_stage()
        image_path = self.get_character_image()
                
        # 쿨타임 상태
        can_answer = data.get("last_question_date") != today
        
        # 오늘의 질문 (미리 보기용)
        # DailyQuestionMixin에서 제공
        daily_q_info = self.get_daily_question()
        
        return {
            "user_id": self.user_id,
            "character": {
                "level": lvl,
                "stage": stage,
                "exp": data['exp'],
                "next_level_exp": next_lvl_exp,
                "flavor": data['main_flavor'],
                "flavor_name": FLAVORS[data['main_flavor']]['name'],
                "image_path": image_path
            },
            "currency": {
                "popcorn": data['popcorn']
            },
            "daily_status": {
                "can_answer_question": can_answer,
                "today_question": daily_q_info["question"]
            }
        }

    def print_status(self):
        """(CLI용) 현재 상태 출력"""
        home_data = self.get_home_data()
        char = home_data['character']
        
        print(f"\n[{self.user_id}의 리뷰몽 프로필]")
        print(f"--------------------------------")
        print(f"🥚 단계: {char['stage']}")
        print(f"📊 레벨: Lv.{char['level']} (EXP: {char['exp']} / {char['next_level_exp']})")
        print(f"🍿 팝콘: {home_data['currency']['popcorn']}개")
        print(f"🎨 속성: {char['flavor_name']}맛 ({char['flavor']})")
        print(f"--------------------------------")
