from datetime import date
import random
from typing import Dict, Optional

class ProbabilityEngine:
    """
    확률 기반 상품 선택 엔진
    
    각 상품의 등급별 확률:
    - C등급 (팝콘): 50%
    - B등급 (핫도그): 25%, (콤보): 15%
    - A등급 (오징어): 9%
    - S등급 (치킨): 1%
    """
    
    def __init__(self):
        """5개 상품의 확률 설정"""
        self.probabilities = {
            "팝콘": 0.50,    # C등급 - 가장 흔함
            "핫도그": 0.25,  # B등급
            "콤보": 0.15,    # B등급
            "오징어": 0.09,  # A등급 - 희귀
            "치킨": 0.01     # S등급 - 매우 희귀
        }
    
    def select_prize(self):
        """
        가중치 기반 랜덤 선택
        """
        random_value = random.random()
        cumulative = 0.0
        
        for prize, probability in self.probabilities.items():
            cumulative += probability
            if random_value < cumulative:
                return prize
        
        # fallback
        return "팝콘"


class AngleCalculator:
    """
    상품명을 룰렛 각도로 변환하는 계산기
    """
    
    def __init__(self):
        """
        각 상품의 중심 각도 매핑
        """
        self.angle_map = {
            "팝콘": 36,
            "핫도그": 108,
            "콤보": 180,
            "오징어": 252,
            "치킨": 324
        }
    
    def get_target_angle(self, prize):
        return self.angle_map.get(prize, 0)


class FeedingMixin:
    """
    밥주기 (Feeding) 관련 로직 (룰렛 게임)
    """
    
    def play_roulette(self) -> Dict:
        """
        룰렛 돌리기
        
        Returns:
            Dict: {
                "prize": str,        # 상품명
                "target_angle": int, # 각도
                "message": str       # 결과 메시지
            }
        """
        # 0. 1일 1회 제한 확인 (오늘 이미 밥을 줬는지 체크)
        user_data = self.get_user_data()
        today = date.today().isoformat()
        
        if user_data.get('last_feeding_date') == today:
            return {
                "success": False,
                "prize": "None",
                "target_angle": 0,
                "message": "오늘은 이미 밥을 주셨어요! 내일 또 오세요. 🌙",
                "reward": {"exp": 0, "popcorn": 0}
            }

        # 엔진 초기화 (또는 클래스 멤버로 유지 가능)
        prob_engine = ProbabilityEngine()
        angle_calc = AngleCalculator()
        
        # 1. 상품 선택
        prize = prob_engine.select_prize()
        
        # 2. 각도 계산
        angle = angle_calc.get_target_angle(prize)
        
        # 메시지 생성
        messages = {
            "팝콘": "고소한 팝콘이네요! (Standard)",
            "핫도그": "든든한 핫도그 당첨! (Good)",
            "콤보": "알찬 콤보 세트! (Great)",
            "오징어": "쫄깃한 오징어! (Rare)",
            "치킨": "대박! 치킨 당첨!!! (Legendary)"
        }
        
        # 3. 보상 설정 및 적용
        rewards = {
            "팝콘": {"exp": 15, "popcorn": 5},
            "핫도그": {"exp": 40, "popcorn": 15},
            "콤보": {"exp": 80, "popcorn": 30},
            "오징어": {"exp": 150, "popcorn": 50},
            "치킨": {"exp": 500, "popcorn": 200}
        }
        
        reward = rewards.get(prize, {"exp": 0, "popcorn": 0})
        
        # Core 메서드 호출 (믹스인 사용 시 self가 Core 인스턴스임)
        if hasattr(self, 'add_exp'):
            self.add_exp(reward['exp'])
        if hasattr(self, 'add_popcorn'):
            self.add_popcorn(reward['popcorn'])

        # 4. 마지막 밥준 날짜 업데이트
        self._update_user_data('last_feeding_date', today)

        return {
            "success": True,
            "prize": prize,
            "target_angle": angle,
            "message": messages.get(prize, "축하합니다!"),
            "reward": reward
        }
