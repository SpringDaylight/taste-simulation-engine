"""
Emotion Cocktail Generator - Main Pipeline

감정 기반 칵테일 생성 시스템의 메인 파이프라인 클래스입니다.
모든 컴포넌트를 조합하여 입력부터 최종 출력까지 전체 흐름을 관리합니다.

Pipeline Flow:
1. 입력 검증 (TasteInputValidator)
2. 비율 계산 (TasteAnalyzer)
3. Top-N 선정 (TopNSelector)
4. 이미지 생성 (CocktailImageGenerator)
5. 성분표 생성 (IngredientLabelGenerator)
6. LLM 코멘트 생성 (LLMCommentGenerator)
7. 최종 출력 조립 (CocktailOutputAssembler)
"""

import logging
from typing import Optional

from .models import CocktailOutput, TasteInput
from .validators import TasteInputValidator
from .analyzers import (
    TasteAnalyzer,
    TopNSelector,
    CocktailImageGenerator,
    IngredientLabelGenerator,
    LLMCommentGenerator,
    CocktailOutputAssembler
)


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmotionCocktailGenerator:
    """
    감정 기반 칵테일 생성 시스템의 메인 클래스
    
    모든 컴포넌트를 조합하여 전체 파이프라인을 구성하고,
    입력 데이터를 받아 최종 칵테일 출력을 생성합니다.
    
    Requirements: 모든 요구사항 (1.1~8.3)
    """
    
    def __init__(self, bedrock_region: Optional[str] = None, bedrock_model_id: Optional[str] = None):
        """
        EmotionCocktailGenerator 초기화
        
        모든 컴포넌트 인스턴스를 생성하고 초기화합니다.
        
        Args:
            bedrock_region: AWS Bedrock region
            bedrock_model_id: AWS Bedrock model id
        """
        logger.info("EmotionCocktailGenerator 초기화 중...")
        
        # 각 컴포넌트 초기화
        self.validator = TasteInputValidator()
        self.analyzer = TasteAnalyzer()
        self.top_n_selector = TopNSelector(self.analyzer)
        self.image_generator = CocktailImageGenerator()
        self.label_generator = IngredientLabelGenerator()
        self.llm_generator = LLMCommentGenerator(
            region_name=bedrock_region,
            model_id=bedrock_model_id
        )
        self.output_assembler = CocktailOutputAssembler()
        
        logger.info("EmotionCocktailGenerator 초기화 완료")
    
    def generate(self, taste_input: dict) -> CocktailOutput:
        """
        감정 기반 칵테일 생성 메인 메서드
        
        전체 파이프라인을 실행하여 입력 데이터로부터 최종 칵테일 출력을 생성합니다.
        
        Pipeline Flow:
        1. 입력 검증
        2. 비율 계산
        3. Top-N 선정
        4. 이미지 생성
        5. 성분표 생성
        6. LLM 코멘트 생성
        7. 최종 출력 조립
        
        Args:
            taste_input: 7가지 맛 값을 포함하는 딕셔너리
                        (sweet, spicy, onion, cheese, dark, salty, mint)
        
        Returns:
            CocktailOutput: 최종 칵테일 출력 데이터
        
        Raises:
            ValueError: 입력 검증 실패 시
            Exception: 파이프라인 실행 중 예외 발생 시
        
        Requirements: 모든 요구사항 (1.1~8.3)
        """
        try:
            logger.info("칵테일 생성 파이프라인 시작")
            logger.debug(f"입력 데이터: {taste_input}")
            
            # Step 1: 입력 검증 (Requirements 1.1, 1.2, 1.3)
            logger.info("Step 1: 입력 데이터 검증 중...")
            validation_result = self.validator.validate(taste_input)
            
            if not validation_result.is_valid:
                error_msg = f"입력 검증 실패: {validation_result.error_message}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            normalized_input = validation_result.normalized_input
            logger.info("입력 검증 완료")
            
            # Step 1.5: 합계 0 체크 (Requirement 1.4, 8.1)
            if normalized_input.total() == 0:
                logger.warning("모든 맛 값의 합이 0입니다. 기본 칵테일을 생성합니다.")
                return self._generate_default_cocktail()
            
            # Step 2: 비율 계산 (Requirement 3.1)
            logger.info("Step 2: 맛 비율 계산 중...")
            taste_ratios = self.analyzer.calculate_ratios(normalized_input)
            logger.debug(f"계산된 비율: {taste_ratios}")
            logger.info("비율 계산 완료")
            
            # Step 3: Top-N 선정 (Requirements 3.2, 3.3, 3.4)
            logger.info("Step 3: Top-N 맛 선정 중...")
            top_n_tastes = self.top_n_selector.select_top_n(taste_ratios)
            
            # Top-N이 비어있는 경우 (모든 맛이 5% 미만)
            if not top_n_tastes:
                logger.warning("5% 이상 비율을 가진 맛이 없습니다. 기본 칵테일을 생성합니다.")
                return self._generate_default_cocktail()
            
            logger.info(f"Top-N 맛 선정 완료: {len(top_n_tastes)}개")
            logger.debug(f"선정된 맛: {[taste.taste_name for taste in top_n_tastes]}")
            
            # Step 4: 이미지 생성 (Requirements 4.1~4.6)
            logger.info("Step 4: 칵테일 이미지 생성 중...")
            base_image_id = self.image_generator.select_random_base()
            gradient_info = self.image_generator.generate_gradient(top_n_tastes)
            logger.info(f"이미지 생성 완료 (베이스: {base_image_id})")
            logger.debug(f"그라데이션 정보: {gradient_info}")
            
            # Step 5: 성분표 생성 (Requirements 5.1, 5.2, 5.3)
            logger.info("Step 5: 성분표 생성 중...")
            ingredient_label = self.label_generator.generate_label(top_n_tastes)
            logger.info(f"성분표 생성 완료: {ingredient_label}")
            
            # Step 6: LLM 코멘트 생성 (Requirements 6.1~6.6, 8.3)
            logger.info("Step 6: LLM 코멘트 생성 중...")
            llm_comment = self.llm_generator.generate_comment(ingredient_label)
            logger.info(f"LLM 코멘트 생성 완료: {llm_comment.cocktail_name}")
            logger.debug(f"위로 메시지: {llm_comment.comfort_message}")
            
            # Step 7: 최종 출력 조립 (Requirements 7.1~7.7)
            logger.info("Step 7: 최종 출력 조립 중...")
            cocktail_output = self.output_assembler.assemble(
                base_image_id=base_image_id,
                top_n_tastes=top_n_tastes,
                gradient_info=gradient_info,
                ingredient_label=ingredient_label,
                llm_comment=llm_comment
            )
            logger.info("최종 출력 조립 완료")
            
            logger.info("칵테일 생성 파이프라인 완료")
            return cocktail_output
        
        except ValueError as e:
            # 입력 검증 오류는 그대로 전파
            logger.error(f"입력 검증 오류: {e}")
            raise
        
        except Exception as e:
            # 예상치 못한 오류 처리
            error_msg = f"칵테일 생성 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e
    
    def _generate_default_cocktail(self) -> CocktailOutput:
        """
        기본 칵테일 생성 (합계 0 또는 Top-N 없음 시)
        
        모든 맛이 동일한 비율(1/7)을 가진 기본 칵테일을 생성합니다.
        
        Returns:
            CocktailOutput: 기본 칵테일 출력
        
        Requirements: 1.4, 8.1
        """
        from .models import TasteInfo, GradientInfo, LLMComment
        
        logger.info("기본 칵테일 생성 중...")
        
        # 모든 맛을 동일한 비율로 설정
        default_ratio = 1.0 / 7.0
        default_tastes = []
        
        for taste_name in ['sweet', 'spicy', 'onion', 'cheese', 'dark', 'salty', 'mint']:
            emotion_label, hex_color = self.analyzer.get_emotion_and_color(taste_name)
            default_tastes.append(TasteInfo(
                taste_name=taste_name,
                ratio=default_ratio,
                emotion_label=emotion_label,
                hex_color=hex_color
            ))
        
        # Top-3 선정 (비율이 모두 같으므로 처음 3개)
        top_n_tastes = default_tastes[:3]
        
        # 베이스 이미지 선택
        base_image_id = self.image_generator.select_random_base()
        
        # 그라데이션 생성
        gradient_info = self.image_generator.generate_gradient(top_n_tastes)
        
        # 성분표 생성
        ingredient_label = self.label_generator.generate_label(top_n_tastes)
        
        # 기본 LLM 코멘트
        llm_comment = LLMComment(
            cocktail_name="감정의 칵테일",
            comfort_message="오늘 하루도 수고하셨어요.\n당신의 감정을 담아 특별한 한 잔을 준비했습니다."
        )
        
        # 최종 출력 조립
        cocktail_output = self.output_assembler.assemble(
            base_image_id=base_image_id,
            top_n_tastes=top_n_tastes,
            gradient_info=gradient_info,
            ingredient_label=ingredient_label,
            llm_comment=llm_comment
        )
        
        logger.info("기본 칵테일 생성 완료")
        return cocktail_output
