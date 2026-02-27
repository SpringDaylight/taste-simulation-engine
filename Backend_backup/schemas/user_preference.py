"""
User preference schemas for request/response validation
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class UserPreferenceBase(BaseModel):
    """Base user preference schema"""
    preference_vector_json: Dict[str, Any] = Field(
        ...,
        description="Preference vector containing emotion_scores, narrative_traits, direction_mood, character_relationship, ending_preference"
    )
    persona_code: Optional[str] = Field(None, description="User persona code")
    boost_tags: List[str] = Field(default_factory=list, description="List of liked tags")
    dislike_tags: List[str] = Field(default_factory=list, description="List of disliked tags")
    penalty_tags: List[str] = Field(default_factory=list, description="List of penalty tags")


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preference"""
    pass


class UserPreferenceUpdate(BaseModel):
    """Schema for updating user preference"""
    preference_vector_json: Optional[Dict[str, Any]] = None
    persona_code: Optional[str] = None
    boost_tags: Optional[List[str]] = None
    dislike_tags: Optional[List[str]] = None
    penalty_tags: Optional[List[str]] = None


class UserPreferenceResponse(UserPreferenceBase):
    """Schema for user preference response"""
    id: int
    user_id: str
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
