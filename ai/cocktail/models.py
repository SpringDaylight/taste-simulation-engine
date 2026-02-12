"""
Data models for Emotion Cocktail Generator

모든 데이터 모델은 dataclass를 사용하여 불변 데이터 구조로 구현됩니다.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TasteInput:
    """7가지 맛 입력 데이터"""
    sweet: int
    spicy: int
    onion: int
    cheese: int
    dark: int
    salty: int
    mint: int
    
    def total(self) -> int:
        """모든 맛 값의 합계를 반환합니다."""
        return self.sweet + self.spicy + self.onion + self.cheese + \
               self.dark + self.salty + self.mint


@dataclass(frozen=True)
class ValidationResult:
    """입력 검증 결과"""
    is_valid: bool
    error_message: Optional[str]
    normalized_input: Optional[TasteInput]


@dataclass(frozen=True)
class TasteInfo:
    """개별 맛 정보 (비율, 감정, 색상 포함)"""
    taste_name: str
    ratio: float
    emotion_label: str
    hex_color: str


@dataclass(frozen=True)
class GradientInfo:
    """그라데이션 정보"""
    direction: str  # 'vertical'
    colors: list[str]  # HEX 색상 코드 리스트
    stops: list[float]  # 0.0 ~ 1.0 (비율 기반)


@dataclass(frozen=True)
class LLMComment:
    """LLM이 생성한 칵테일 이름과 위로 메시지"""
    cocktail_name: str
    comfort_message: str  # 2줄 이내


@dataclass(frozen=True)
class CocktailOutput:
    """최종 칵테일 출력 데이터"""
    base_image_id: str
    top_n_tastes: list[TasteInfo]
    gradient_info: GradientInfo
    ingredient_label: str
    cocktail_name: str
    comfort_message: str
