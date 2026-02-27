from typing import Dict, List
from typing import Dict, List
# from database import db
from models import ThemeInventory

class ThemeMixin:
    """
    테마 꾸미기 (Theme) 관련 로직
    """
    
    THEMES = {
        "basic": {"name": "기본 (Basic)", "price": 0, "desc": "기본 테마입니다."},
        "dark":  {"name": "다크 (Dark)", "price": 50, "desc": "어두운 영화관 분위기입니다."},
        "pink":  {"name": "핑크 (Pink)", "price": 100, "desc": "러블리한 핑크 테마입니다."},
        "gold":  {"name": "골드 (Gold)", "price": 300, "desc": "럭셔리한 VIP 테마입니다."}
    }

    def get_shop_items(self) -> List[Dict]:
        """상점 아이템 목록 반환"""
        user = self._get_user_model()
        
        # 보유 테마 및 적용 테마 조회
        inventory = {item.theme_id: item for item in user.inventory}
        
        items = []
        for tid, info in self.THEMES.items():
            is_owned = tid in inventory
            is_applied = False
            if is_owned:
                is_applied = inventory[tid].is_applied
                
            items.append({
                "id": tid,
                "name": info["name"],
                "price": info["price"],
                "desc": info["desc"],
                "is_owned": is_owned,
                "is_applied": is_applied
            })
        return items

    def buy_theme(self, theme_id: str) -> Dict:
        """테마 구매"""
        if theme_id not in self.THEMES:
            return {"success": False, "message": "존재하지 않는 테마입니다."}
            
        user = self._get_user_model()
        
        # 이미 보유 중인지 확인
        # Flask: ThemeInventory.query.filter_by(user_id=user.id, theme_id=theme_id).first()
        # FastAPI: self.db.query(ThemeInventory).filter_by(user_id=user.id, theme_id=theme_id).first()
        existing_item = self.db.query(ThemeInventory).filter_by(user_id=user.id, theme_id=theme_id).first()
        if existing_item:
            return {"success": False, "message": "이미 보유한 테마입니다."}
            
        price = self.THEMES[theme_id]["price"]
        if user.popcorn < price:
            return {"success": False, "message": f"팝콘이 부족합니다. (필요: {price})"}
            
        # 구매 처리 (팝콘 차감 및 아이템 추가)
        user.popcorn -= price
        new_item = ThemeInventory(user_id=user.id, theme_id=theme_id, is_applied=False)
        self.db.add(new_item)
        self.db.commit()
        
        return {
            "success": True, 
            "message": f"'{self.THEMES[theme_id]['name']}' 테마를 구매했습니다!",
            "new_popcorn": user.popcorn
        }

    def apply_theme(self, theme_id: str) -> Dict:
        """테마 적용"""
        user = self._get_user_model()
        
        # 보유 확인
        target_item = self.db.query(ThemeInventory).filter_by(user_id=user.id, theme_id=theme_id).first()
        if not target_item:
             return {"success": False, "message": "보유하지 않은 테마입니다."}
             
        # 기존 적용 해제
        self.db.query(ThemeInventory).filter_by(user_id=user.id, is_applied=True).update({"is_applied": False})
        
        # 새 테마 적용
        target_item.is_applied = True
        self.db.commit()
        
        return {"success": True, "message": f"테마가 적용되었습니다!"}
