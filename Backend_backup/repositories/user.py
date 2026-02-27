"""
User repository with custom queries
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import User, TasteAnalysis
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User repository with custom queries"""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_name(self, name: str) -> Optional[User]:
        """Get user by name"""
        return self.db.query(User).filter(User.name == name).first()

    def get_by_user_id(self, user_id: str) -> Optional[User]:
        """Get user by login ID"""
        return self.db.query(User).filter(User.user_id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_nickname(self, nickname: str) -> Optional[User]:
        """Get user by nickname"""
        return self.db.query(User).filter(User.nickname == nickname).first()

    def search(self, query: str, limit: int = 20) -> list[User]:
        """Search users by name, user_id or nickname"""
        if not query:
            return []
        pattern = f"%{query}%"
        return (
            self.db.query(User)
            .filter(
                or_(
                    User.name.ilike(pattern),
                    User.user_id.ilike(pattern),
                    User.nickname.ilike(pattern),
                )
            )
            .order_by(User.nickname.asc().nulls_last(), User.user_id.asc().nulls_last())
            .limit(limit)
            .all()
        )
    
    def get_taste_analysis(self, user_id: str) -> Optional[TasteAnalysis]:
        """Get user's taste analysis"""
        return (
            self.db.query(TasteAnalysis)
            .filter(TasteAnalysis.user_id == user_id)
            .first()
        )
    
    def update_taste_analysis(self, user_id: str, summary_text: str) -> TasteAnalysis:
        """Update or create taste analysis"""
        taste = self.get_taste_analysis(user_id)
        
        if taste:
            taste.summary_text = summary_text
        else:
            taste = TasteAnalysis(user_id=user_id, summary_text=summary_text)
            self.db.add(taste)
        
        self.db.commit()
        self.db.refresh(taste)
        return taste
