"""
User preference repository for storing and retrieving user taste vectors
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from models import UserPreference
from repositories.base import BaseRepository


class UserPreferenceRepository(BaseRepository[UserPreference]):
    """User preference repository with custom queries"""
    
    def __init__(self, db: Session):
        super().__init__(UserPreference, db)
    
    def get_by_user_id(self, user_id: str) -> Optional[UserPreference]:
        """Get user preference by user_id"""
        return self.db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    
    def upsert(
        self,
        user_id: str,
        preference_vector_json: dict,
        persona_code: str = None,
        boost_tags: list = None,
        dislike_tags: list = None,
        penalty_tags: list = None,
        favorite_genres: list = None,
        disliked_genres: list = None,
        viewing_context: str = None,
        preferred_vibe: str = None,
        interest_keywords: list = None,
        preferred_origin: str = None
    ) -> UserPreference:
        """
        Insert or update user preference (upsert operation)
        
        Args:
            user_id: User ID
            preference_vector_json: Preference vector containing emotion_scores, narrative_traits, etc.
            persona_code: User persona code
            boost_tags: List of liked tags
            dislike_tags: List of disliked tags
            penalty_tags: List of penalty tags
            favorite_genres: 좋아하는 장르 리스트
            disliked_genres: 싫어하는 장르 리스트
            viewing_context: 영화 감상 맥락
            preferred_vibe: 선호 분위기
            interest_keywords: 관심 키워드 리스트
            preferred_origin: 선호 국적
        
        Returns:
            UserPreference object
        """
        from utils.cache import cache_delete_pattern
        
        existing = self.get_by_user_id(user_id)
        
        if existing:
            # Update existing preference
            existing.preference_vector_json = preference_vector_json
            existing.persona_code = persona_code
            existing.boost_tags = boost_tags or []
            existing.dislike_tags = dislike_tags or []
            existing.penalty_tags = penalty_tags or []
            existing.favorite_genres = favorite_genres or []
            existing.disliked_genres = disliked_genres or []
            existing.viewing_context = viewing_context
            existing.preferred_vibe = preferred_vibe
            existing.interest_keywords = interest_keywords or []
            existing.preferred_origin = preferred_origin
            existing.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(existing)
            
            # 캐시 무효화: 해당 사용자의 모든 만족도 캐시 삭제
            satisfaction_deleted = cache_delete_pattern(f"satisfaction:{user_id}:*")
            if satisfaction_deleted > 0:
                print(f"✅ [Cache] Invalidated {satisfaction_deleted} satisfaction cache entries for user {user_id}")
            
            # 설명 캐시는 영화별로 저장되므로 사용자 변경 시 무효화 불필요
            # (영화 제목과 확률 기반 캐시)
            
            return existing
        else:
            # Create new preference
            new_preference = UserPreference(
                user_id=user_id,
                preference_vector_json=preference_vector_json,
                persona_code=persona_code,
                boost_tags=boost_tags or [],
                dislike_tags=dislike_tags or [],
                penalty_tags=penalty_tags or [],
                favorite_genres=favorite_genres or [],
                disliked_genres=disliked_genres or [],
                viewing_context=viewing_context,
                preferred_vibe=preferred_vibe,
                interest_keywords=interest_keywords or [],
                preferred_origin=preferred_origin
            )
            self.db.add(new_preference)
            self.db.commit()
            self.db.refresh(new_preference)
            return new_preference
    
    def delete_by_user_id(self, user_id: str) -> bool:
        """Delete user preference by user_id"""
        preference = self.get_by_user_id(user_id)
        if not preference:
            return False
        
        self.db.delete(preference)
        self.db.commit()
        return True
    
    def exists(self, user_id: str) -> bool:
        """Check if user preference exists"""
        return self.db.query(UserPreference).filter(UserPreference.user_id == user_id).count() > 0
