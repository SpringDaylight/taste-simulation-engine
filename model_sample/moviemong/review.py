
from typing import Optional, Dict
from database import db
from models import FlavorStat
from .core import FLAVORS
from analysis import sentiment
from analysis import embedding

class ReviewMixin:
    
    def _get_bedrock_client(self):
        # Core has the attribute, Mixin uses it
        if self.bedrock_client is None:
            self.bedrock_client = embedding.get_bedrock_client()
        return self.bedrock_client

    def add_review(self, review_text: str, is_detailed: bool = False) -> Dict:
        """리뷰 작성 시 보상 및 맛 분석 (LLM 사용)"""
        print(f"Adding review: '{review_text}' (Length: {len(review_text)})")
        # 1. 보상
        if is_detailed and len(review_text) >= 50:
            exp_gain = 30
            popcorn_gain = 12
            reward_type = "detailed"
        else:
            exp_gain = 5
            popcorn_gain = 3
            reward_type = "simple"
            
        # Core 메소드 활용 (DB 커밋 포함됨 - add_exp, add_popcorn)
        self.add_exp(exp_gain)
        self.add_popcorn(popcorn_gain)
        
        # 2. 맛 분석 (LLM)
        flavor_result = self._analyze_flavor_with_llm(review_text)
        flavor_name = FLAVORS[flavor_result]['name']
        
        # 3. 사용자 데이터 갱신 (DB)
        user = self._get_user_model()
        
        # 해당 맛 스탯 업데이트
        stat = FlavorStat.query.filter_by(user_id=user.id, flavor_name=flavor_result).first()
        if stat:
            stat.score += 1
        else:
            # 혹시 없으면 생성 (초기화 시 생성되지만 안전장치)
            stat = FlavorStat(user_id=user.id, flavor_name=flavor_result, score=1)
            db.session.add(stat)
            

        # 메인 맛 갱신 로직 제거 (사용자 요구사항: 성격 변화 기능 미사용)
        # 3. 사용자 데이터 갱신 (DB) - 맛 스탯만 업데이트하고 메인 맛은 변경하지 않음
        
        db.session.commit()
        
        return {
            "success": True,
            "reward": {
                "type": reward_type,
                "exp": exp_gain,
                "popcorn": popcorn_gain
            },
            "analysis": {
                "flavor": flavor_result,
                "flavor_name": flavor_name,
                "main_flavor": user.main_flavor,
                "main_flavor_name": FLAVORS[user.main_flavor]['name']
            },
            "message": f"{flavor_name} 팝콘 획득! (EXP +{exp_gain}, 팝콘 +{popcorn_gain})"
        }

    def _analyze_flavor_with_llm(self, text: str) -> str:
        """LLM을 사용하여 리뷰의 맛(분위기) 분석"""
        # 리뷰가 너무 짧거나(10자 이하) 구체적이지 않으면 'Original' 반환
        if len(text.strip()) < 10:
            return "Original"

        # 기본값 (Taxonomy가 없으면 Original)
        if not hasattr(self, 'taxonomy') or not self.taxonomy:
            return "Original"
            
        try:
            client = self._get_bedrock_client()
            analysis = sentiment.analyze_user_preference_with_llm(text, self.taxonomy, client)
            
            emotion_scores = analysis.get('emotion_scores', {})
            flavor_scores = {k: 0.0 for k in FLAVORS.keys()}
            
            MAPPING = {
                "Sweet": ["따뜻해요", "힐링돼요", "설레요", "로맨틱해요", "감동적이에요", "행복", "사랑"],
                "Spicy": ["무서워요", "소름 돋아요", "긴장돼요", "충격", "공포"],
                "Onion": ["반전이 많아요", "복선이 많아요", "미스터리", "추리"],
                "Cheese": ["통쾌해요", "웃겨요", "액션", "시원한"],
                "Dark": ["우울해요", "어두운 분위기예요", "느와르", "범죄"],
                "Salty": ["슬퍼요", "여운이 길어요", "현실적이에요", "눈물"],
                "Mint": ["몽환적이에요", "독특해요", "스타일이 독특해요", "SF"]
            }
            
            for tag, score in emotion_scores.items():
                for flavor, keywords in MAPPING.items():
                    if tag in keywords:
                        flavor_scores[flavor] += score
                    else:
                        for k in keywords:
                            if k in tag:
                                flavor_scores[flavor] += score * 0.8
            
            best_flavor = max(flavor_scores, key=flavor_scores.get)
            
            if analysis.get('method_used') == 'keyword_matching' or flavor_scores[best_flavor] < 0.1:
                simple_flavor = self._simple_keyword_analysis(text)
                if simple_flavor:
                    return simple_flavor
                return "Original" # 매칭되는 키워드 없으면 오리지널
                
            return best_flavor
            
        except Exception as e:
            print(f"⚠️ LLM 분석 중 오류: {e}")
            simple_flavor = self._simple_keyword_analysis(text)
            return simple_flavor if simple_flavor else "Original"

    def _simple_keyword_analysis(self, text: str) -> Optional[str]:
        """단순 키워드 포함 여부로 맛 결정 (Fallback)"""
        for flavor_key, info in FLAVORS.items():
            for keyword in info["keywords"]:
                if keyword in text:
                    return flavor_key
        return None
