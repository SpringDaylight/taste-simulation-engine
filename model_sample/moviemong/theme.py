from typing import Dict, List

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
        user_data = self.get_user_data()
        owned = user_data.get("owned_themes", ["basic"])
        applied = user_data.get("applied_theme", "basic")
        
        items = []
        for tid, info in self.THEMES.items():
            items.append({
                "id": tid,
                "name": info["name"],
                "price": info["price"],
                "desc": info["desc"],
                "is_owned": tid in owned,
                "is_applied": tid == applied
            })
        return items

    def buy_theme(self, theme_id: str) -> Dict:
        """테마 구매"""
        if theme_id not in self.THEMES:
            return {"success": False, "message": "존재하지 않는 테마입니다."}
            
        user_data = self.get_user_data()
        owned = user_data.get("owned_themes", ["basic"])
        
        if theme_id in owned:
            return {"success": False, "message": "이미 보유한 테마입니다."}
            
        price = self.THEMES[theme_id]["price"]
        if user_data["popcorn"] < price:
            return {"success": False, "message": f"팝콘이 부족합니다. (필요: {price})"}
            
        # 구매 처리
        self.data[self.user_id]["popcorn"] -= price
        self.data[self.user_id].setdefault("owned_themes", []).append(theme_id)
        self._save_data()
        
        return {
            "success": True, 
            "message": f"'{self.THEMES[theme_id]['name']}' 테마를 구매했습니다!",
            "new_popcorn": self.data[self.user_id]["popcorn"]
        }

    def apply_theme(self, theme_id: str) -> Dict:
        """테마 적용"""
        user_data = self.get_user_data()
        owned = user_data.get("owned_themes", ["basic"])
        
        if theme_id not in owned:
             return {"success": False, "message": "보유하지 않은 테마입니다."}
             
        self.data[self.user_id]["applied_theme"] = theme_id
        self._save_data()
        
        return {"success": True, "message": f"테마가 적용되었습니다!"}
