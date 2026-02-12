"""
Input validation components for Emotion Cocktail Generator

입력 데이터의 유효성을 검증하는 컴포넌트들을 포함합니다.
"""

from .models import TasteInput, ValidationResult


class TasteInputValidator:
    """
    맛 입력 데이터의 유효성을 검증하는 클래스
    
    Requirements:
    - 1.1: 7개의 필수 키 검증
    - 1.2: 음수가 아닌 정수 검증
    - 1.3: 검증 실패 시 오류 메시지 반환
    """
    
    REQUIRED_KEYS = {'sweet', 'spicy', 'onion', 'cheese', 'dark', 'salty', 'mint'}
    
    def validate(self, taste_input: dict) -> ValidationResult:
        """
        입력 데이터 검증
        
        Args:
            taste_input: 7가지 맛 값을 포함하는 딕셔너리
            
        Returns:
            ValidationResult: 검증 결과 (is_valid, error_message, normalized_input)
        """
        # 1. 필수 키 존재 확인 (Requirement 1.1)
        missing_keys = self.REQUIRED_KEYS - set(taste_input.keys())
        if missing_keys:
            return ValidationResult(
                is_valid=False,
                error_message=f"필수 키가 누락되었습니다: {', '.join(sorted(missing_keys))}",
                normalized_input=None
            )
        
        # 2. 타입 및 음수 검증 (Requirement 1.2)
        for key in self.REQUIRED_KEYS:
            value = taste_input[key]
            
            # 타입 검증: 정수인지 확인
            if not isinstance(value, int):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"'{key}' 값은 정수여야 합니다. 현재 타입: {type(value).__name__}",
                    normalized_input=None
                )
            
            # 음수 검증
            if value < 0:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"'{key}' 값은 음수일 수 없습니다. 현재 값: {value}",
                    normalized_input=None
                )
        
        # 3. 검증 성공 - TasteInput 객체 생성
        try:
            normalized_input = TasteInput(
                sweet=taste_input['sweet'],
                spicy=taste_input['spicy'],
                onion=taste_input['onion'],
                cheese=taste_input['cheese'],
                dark=taste_input['dark'],
                salty=taste_input['salty'],
                mint=taste_input['mint']
            )
            
            return ValidationResult(
                is_valid=True,
                error_message=None,
                normalized_input=normalized_input
            )
        except Exception as e:
            # 예상치 못한 오류 처리
            return ValidationResult(
                is_valid=False,
                error_message=f"입력 데이터 변환 중 오류 발생: {str(e)}",
                normalized_input=None
            )
