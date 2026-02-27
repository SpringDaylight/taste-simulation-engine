"""
User auth repository
"""
from typing import Optional
from sqlalchemy.orm import Session

from models import UserAuth
from repositories.base import BaseRepository


class UserAuthRepository(BaseRepository[UserAuth]):
    """User auth repository"""

    def __init__(self, db: Session):
        super().__init__(UserAuth, db)

    def get_by_provider(self, provider: str, provider_user_id: str) -> Optional[UserAuth]:
        return (
            self.db.query(UserAuth)
            .filter(
                UserAuth.provider == provider,
                UserAuth.provider_user_id == provider_user_id,
            )
            .first()
        )
