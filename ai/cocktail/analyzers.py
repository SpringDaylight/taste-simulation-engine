"""
Taste analysis components for Emotion Cocktail Generator

맛 비율 계산 및 감정-색상 매핑을 담당하는 컴포넌트들을 포함합니다.
"""

from .models import TasteInput, TasteInfo


class TasteAnalyzer:
    """
    맛 비율 계산 및 감정-색상 매핑을 담당하는 클래스
    
    Requirements:
    - 2.1~2.7: 각 맛을 특정 감정과 색상에 매핑
    - 3.1: 각 맛의 비율 계산
    """
    
    # 맛-감정-색상 매핑 테이블 (Requirements 2.1~2.7)
    TASTE_EMOTION_COLOR_MAP = {
        'sweet': ('설렘, 행복', '#FFB7C5'),
        'spicy': ('분노, 긴장', '#FF4500'),
        'onion': ('호기심, 추리', '#E0FFFF'),
        'cheese': ('즐거움, 활기', '#FFD700'),
        'dark': ('우울, 진지', '#4B0082'),
        'salty': ('슬픔, 감동', '#87CEEB'),
        'mint': ('신비, 경이', '#98FF98')
    }
    
    def calculate_ratios(self, taste_input: TasteInput) -> dict[str, float]:
        """
        각 맛의 비율 계산 (Requirement 3.1)
        
        Args:
            taste_input: 검증된 맛 데이터
            
        Returns:
            dict: 각 맛의 비율 (0.0 ~ 1.0)
        """
        total = taste_input.total()
        
        # 합계가 0인 경우 모든 비율을 0으로 반환
        if total == 0:
            return {
                'sweet': 0.0,
                'spicy': 0.0,
                'onion': 0.0,
                'cheese': 0.0,
                'dark': 0.0,
                'salty': 0.0,
                'mint': 0.0
            }
        
        # 각 맛의 비율 계산
        return {
            'sweet': taste_input.sweet / total,
            'spicy': taste_input.spicy / total,
            'onion': taste_input.onion / total,
            'cheese': taste_input.cheese / total,
            'dark': taste_input.dark / total,
            'salty': taste_input.salty / total,
            'mint': taste_input.mint / total
        }
    
    def get_emotion_and_color(self, taste: str) -> tuple[str, str]:
        """
        맛에 해당하는 감정과 색상 반환 (Requirements 2.1~2.7)
        
        Args:
            taste: 맛 이름 (sweet, spicy, onion, cheese, dark, salty, mint)
            
        Returns:
            tuple: (감정 라벨, HEX 색상 코드)
            
        Raises:
            KeyError: 유효하지 않은 맛 이름인 경우
        """
        if taste not in self.TASTE_EMOTION_COLOR_MAP:
            raise KeyError(f"유효하지 않은 맛 이름입니다: {taste}")
        
        return self.TASTE_EMOTION_COLOR_MAP[taste]



class TopNSelector:
    """
    주요 맛 선정 클래스 (5% 이상, 최대 3개)
    
    Requirements:
    - 3.2: 5% 미만 비율을 가진 맛 제외
    - 3.3: 비율이 높은 순으로 정렬하고 상위 최대 3개 선정
    - 3.4: Top_N_Tastes가 1개에서 3개 사이의 맛을 포함하도록 보장
    """
    
    MINIMUM_RATIO_THRESHOLD = 0.05  # 5% 최소 비율 임계값
    MAX_TOP_N = 3  # 최대 선정 개수
    
    def __init__(self, taste_analyzer: TasteAnalyzer):
        """
        TopNSelector 초기화
        
        Args:
            taste_analyzer: 감정-색상 매핑을 위한 TasteAnalyzer 인스턴스
        """
        self.taste_analyzer = taste_analyzer
    
    def select_top_n(self, taste_ratios: dict[str, float]) -> list[TasteInfo]:
        """
        Top-N 맛 선정 (Requirements 3.2, 3.3, 3.4)
        
        Args:
            taste_ratios: 각 맛의 비율 (0.0 ~ 1.0)
            
        Returns:
            list[TasteInfo]: 선정된 1~3개의 맛 정보 (비율 높은 순)
        """
        # 1. 5% 이상 비율을 가진 맛만 필터링 (Requirement 3.2)
        filtered_tastes = [
            (taste_name, ratio)
            for taste_name, ratio in taste_ratios.items()
            if ratio >= self.MINIMUM_RATIO_THRESHOLD
        ]
        
        # 2. 비율이 높은 순으로 정렬 (Requirement 3.3)
        filtered_tastes.sort(key=lambda x: x[1], reverse=True)
        
        # 3. 최대 3개 선정 (Requirement 3.3)
        top_n_tastes = filtered_tastes[:self.MAX_TOP_N]
        
        # 4. TasteInfo 객체 리스트로 변환
        result = []
        for taste_name, ratio in top_n_tastes:
            emotion_label, hex_color = self.taste_analyzer.get_emotion_and_color(taste_name)
            result.append(TasteInfo(
                taste_name=taste_name,
                ratio=ratio,
                emotion_label=emotion_label,
                hex_color=hex_color
            ))
        
        return result



class CocktailImageGenerator:
    """
    칵테일 이미지 생성 클래스 (베이스 선택 + 그라데이션)
    
    Requirements:
    - 4.1: 미리 준비된 3개의 Base_Image 중 하나를 무작위로 선택
    - 4.2: Top_N_Tastes가 1개이면 단색 칵테일 생성
    - 4.3: Top_N_Tastes가 2개이면 2색 Gradient 생성
    - 4.4: Top_N_Tastes가 3개이면 3색 Gradient 생성
    - 4.5: 각 색상의 스톱 위치를 해당 맛의 Taste_Ratio에 비례하여 설정
    - 4.6: Gradient의 방향을 세로(위에서 아래)로 설정
    """
    
    # 단일 베이스 이미지 ID
    DEFAULT_BASE_IMAGE = 'static/배경제거W.png'
    
    def select_random_base(self) -> str:
        """
        베이스 이미지 선택

        Returns:
            str: 베이스 이미지 ID
        """
        return self.DEFAULT_BASE_IMAGE
    
    def generate_gradient(self, top_n_tastes: list[TasteInfo]) -> 'GradientInfo':
        """
        비율 기반 세로 그라데이션 생성 (Requirements 4.2, 4.3, 4.4, 4.5, 4.6)
        
        Args:
            top_n_tastes: Top-N 맛 정보 (1~3개)
            
        Returns:
            GradientInfo: 그라데이션 정보 (색상, 스톱 위치)
        """
        from .models import GradientInfo
        
        # 색상 리스트 추출
        colors = [taste.hex_color for taste in top_n_tastes]
        
        # 비율 리스트 추출
        ratios = [taste.ratio for taste in top_n_tastes]
        
        # 스톱 위치 계산 (Requirement 4.5)
        # 1개: 단색 (스톱 없음) - Requirements 4.2
        if len(top_n_tastes) == 1:
            stops = [1.0]
        
        # 2개: 2색 그라데이션 - Requirements 4.3
        elif len(top_n_tastes) == 2:
            # 첫 번째 색상의 비율만큼 스톱 설정
            # 예: 0.7, 0.3 비율이면 stops = [0.7, 1.0]
            total_ratio = sum(ratios)
            normalized_ratio_1 = ratios[0] / total_ratio
            stops = [normalized_ratio_1, 1.0]
        
        # 3개: 3색 그라데이션 - Requirements 4.4
        elif len(top_n_tastes) == 3:
            # 각 색상의 비율에 비례하여 스톱 설정
            # 예: 0.5, 0.3, 0.2 비율이면 stops = [0.5, 0.8, 1.0]
            total_ratio = sum(ratios)
            normalized_ratio_1 = ratios[0] / total_ratio
            normalized_ratio_2 = (ratios[0] + ratios[1]) / total_ratio
            stops = [normalized_ratio_1, normalized_ratio_2, 1.0]
        
        else:
            # 예외 상황: 1~3개가 아닌 경우 (설계상 발생하지 않아야 함)
            raise ValueError(f"Top-N 맛은 1~3개여야 합니다. 현재: {len(top_n_tastes)}개")
        
        # 세로 방향 그라데이션 반환 (Requirement 4.6)
        return GradientInfo(
            direction='vertical',
            colors=colors,
            stops=stops
        )



class IngredientLabelGenerator:
    """
    성분표 텍스트 생성 클래스
    
    Requirements:
    - 5.1: 각 맛의 Emotion_Label과 백분율 Taste_Ratio를 포함하는 Ingredient_Label 생성
    - 5.2: "감정명 비율% + 감정명 비율% + ..." 형식으로 텍스트 구성
    - 5.3: Ingredient_Label에 Top_N_Tastes에 포함된 맛만 표시
    """
    
    def generate_label(self, top_n_tastes: list[TasteInfo]) -> str:
        """
        성분표 텍스트 생성 (Requirements 5.1, 5.2, 5.3)
        
        Args:
            top_n_tastes: Top-N 맛 정보 (1~3개)
            
        Returns:
            str: "감정명 비율% + 감정명 비율% + ..." 형식의 텍스트
            
        Examples:
            >>> # 1개 맛
            >>> generate_label([TasteInfo('sweet', 1.0, '설렘, 행복', '#FFB7C5')])
            '설렘, 행복 100%'
            
            >>> # 2개 맛
            >>> generate_label([
            ...     TasteInfo('sweet', 0.7, '설렘, 행복', '#FFB7C5'),
            ...     TasteInfo('dark', 0.3, '우울, 진지', '#4B0082')
            ... ])
            '설렘, 행복 70% + 우울, 진지 30%'
            
            >>> # 3개 맛
            >>> generate_label([
            ...     TasteInfo('sweet', 0.5, '설렘, 행복', '#FFB7C5'),
            ...     TasteInfo('spicy', 0.3, '분노, 긴장', '#FF4500'),
            ...     TasteInfo('dark', 0.2, '우울, 진지', '#4B0082')
            ... ])
            '설렘, 행복 50% + 분노, 긴장 30% + 우울, 진지 20%'
        """
        # Top-N 맛이 비어있는 경우 예외 처리
        if not top_n_tastes:
            raise ValueError("Top-N 맛 리스트가 비어있습니다.")
        
        # 각 맛의 감정 라벨과 백분율을 "감정명 비율%" 형식으로 변환
        label_parts = []
        for taste_info in top_n_tastes:
            # 비율을 백분율로 변환 (소수점 반올림)
            percentage = round(taste_info.ratio * 100)
            label_part = f"{taste_info.emotion_label} {percentage}%"
            label_parts.append(label_part)
        
        # " + "로 연결하여 최종 성분표 생성 (Requirement 5.2)
        ingredient_label = " + ".join(label_parts)
        
        return ingredient_label



class LLMCommentGenerator:
    """
    LLM 기반 칵테일 이름 및 위로 코멘트 생성 클래스
    
    Requirements:
    - 6.1: Ingredient_Label을 LLM에 입력으로 제공
    - 6.2: 영화적인 칵테일 이름 생성
    - 6.3: 사용자 심리를 위트 있게 위로하는 2줄 이내의 코멘트 생성
    - 6.4: Bartender_Tone 사용 (부드럽고 위트 있음)
    - 6.5: 진단, 조언, 판단형 문장 금지
    - 6.6: 특정 영화 제목이나 스포일러 금지
    - 8.3: LLM 호출 실패 시 기본값 반환
    """
    
    # 기본 칵테일 이름 및 코멘트 (Requirement 8.3)
    DEFAULT_COCKTAIL_NAME = "감정의 칵테일"
    DEFAULT_COMFORT_MESSAGE = "오늘 하루도 수고하셨어요.\n당신의 감정을 담아 특별한 한 잔을 준비했습니다."
    
    # LLM 호출 설정
    TIMEOUT_SECONDS = 10  # 타임아웃 10초
    MAX_RETRIES = 1  # 1회 재시도
    
    def __init__(self, region_name: str | None = None, model_id: str | None = None):
        """
        LLMCommentGenerator 초기화
        
        Args:
            region_name: AWS region
            model_id: Bedrock model id
        """
        import os
        from dotenv import load_dotenv
        
        # .env 파일 로드
        load_dotenv()
        
        # Bedrock 설정
        self.region_name = (
            region_name
            or os.getenv('BEDROCK_REGION')
            or os.getenv('AWS_REGION')
            or os.getenv('AWS_DEFAULT_REGION')
            or 'us-east-1'
        )
        self.model_id = model_id or os.getenv(
            'BEDROCK_MODEL_ID',
            'anthropic.claude-3-5-haiku-20241022-v1:0'
        )
    
    def _build_prompt(self, ingredient_label: str) -> str:
        """
        LLM 프롬프트 구성 (Requirements 6.1, 6.4, 6.5, 6.6)
        
        Args:
            ingredient_label: 성분표 텍스트
            
        Returns:
            str: 구성된 프롬프트
        """
        prompt = f"""당신은 감성적이고 위트 있는 바텐더입니다. 고객의 감정 상태를 담은 칵테일을 만들고 있습니다.

다음은 고객의 감정 성분표입니다:
{ingredient_label}

다음 규칙을 엄격히 따라 응답해주세요:

1. **칵테일 이름**: 영화적이고 감성적인 칵테일 이름을 하나 만들어주세요. (특정 영화 제목은 사용하지 마세요)
2. **위로 메시지**: 고객의 감정에 공감하고 부드럽게 위로하는 메시지를 2줄 이내로 작성해주세요.
   - 바텐더처럼 부드럽고 위트 있는 톤을 사용하세요
   - 진단, 조언, 판단형 문장은 절대 사용하지 마세요
   - "~해야 합니다", "~하세요", "~인 것 같아요" 같은 표현은 피하세요
   - 특정 영화 제목이나 스포일러는 포함하지 마세요

응답 형식 (정확히 이 형식으로만 응답하세요):
칵테일 이름: [칵테일 이름]
위로 메시지: [2줄 이내의 위로 메시지]"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str) -> tuple[str, str]:
        """
        LLM 응답 파싱
        
        Args:
            response_text: LLM 응답 텍스트
            
        Returns:
            tuple: (칵테일 이름, 위로 메시지)
        """
        lines = response_text.strip().split('\n')
        
        cocktail_name = self.DEFAULT_COCKTAIL_NAME
        comfort_message = self.DEFAULT_COMFORT_MESSAGE
        
        for line in lines:
            line = line.strip()
            if line.startswith('칵테일 이름:'):
                cocktail_name = line.replace('칵테일 이름:', '').strip()
            elif line.startswith('위로 메시지:'):
                comfort_message = line.replace('위로 메시지:', '').strip()
        
        # 칵테일 이름이 비어있으면 기본값 사용
        if not cocktail_name or cocktail_name == "":
            cocktail_name = self.DEFAULT_COCKTAIL_NAME
        
        # 위로 메시지가 비어있으면 기본값 사용
        if not comfort_message or comfort_message == "":
            comfort_message = self.DEFAULT_COMFORT_MESSAGE
        
        return cocktail_name, comfort_message
    
    def _call_llm_api(self, prompt: str) -> str:
        """
        AWS Bedrock LLM API 호출
        
        Args:
            prompt: LLM 프롬프트
            
        Returns:
            str: LLM 응답 텍스트
            
        Raises:
            Exception: API 호출 실패 시
        """
        import json
        import boto3

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }

        client = boto3.client("bedrock-runtime", region_name=self.region_name)
        response = client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )

        payload = json.loads(response["body"].read())

        if isinstance(payload.get("content"), list):
            texts = []
            for item in payload["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            text = "\n".join(t for t in texts if t).strip()
            if text:
                return text

        if isinstance(payload.get("results"), list) and payload["results"]:
            text = payload["results"][0].get("outputText", "")
            if text:
                return text

        if isinstance(payload.get("output"), dict):
            text = payload["output"].get("text", "")
            if text:
                return text

        if payload.get("completion"):
            return str(payload["completion"])

        raise ValueError(f"Unsupported Bedrock response format: {payload}")
    
    def generate_comment(self, ingredient_label: str) -> 'LLMComment':
        """
        LLM 기반 코멘트 생성 (Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.3)
        
        Args:
            ingredient_label: 성분표 텍스트
            
        Returns:
            LLMComment: 칵테일 이름과 위로 코멘트 (2줄 이내)
        """
        from cocktail.models import LLMComment
        
        # 프롬프트 구성 (Requirement 6.1)
        prompt = self._build_prompt(ingredient_label)
        
        # LLM 호출 (재시도 로직 포함)
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # API 호출
                response_text = self._call_llm_api(prompt)
                
                # 응답 파싱
                cocktail_name, comfort_message = self._parse_llm_response(response_text)
                
                # 성공 시 결과 반환
                return LLMComment(
                    cocktail_name=cocktail_name,
                    comfort_message=comfort_message
                )
            
            except Exception as e:
                # 마지막 시도가 아니면 재시도
                if attempt < self.MAX_RETRIES:
                    continue
                
                # 모든 시도 실패 시 기본값 반환 (Requirement 8.3)
                print(f"LLM 호출 실패: {e}. 기본값을 반환합니다.")
                return LLMComment(
                    cocktail_name=self.DEFAULT_COCKTAIL_NAME,
                    comfort_message=self.DEFAULT_COMFORT_MESSAGE
                )



class CocktailOutputAssembler:
    """
    최종 출력 데이터 조립 클래스
    
    모든 컴포넌트의 결과를 받아 CocktailOutput으로 조립합니다.
    
    Requirements:
    - 7.1: 선택된 Base_Image ID를 출력에 포함
    - 7.2: Top_N_Tastes 목록(1~3개)을 출력에 포함
    - 7.3: 각 Top_N_Tastes의 Taste_Ratio와 HEX_Color를 출력에 포함
    - 7.4: Gradient 스톱 정보를 출력에 포함
    - 7.5: Ingredient_Label 텍스트를 출력에 포함
    - 7.6: LLM이 생성한 칵테일 이름을 출력에 포함
    - 7.7: LLM이 생성한 위로 코멘트(2줄 이내)를 출력에 포함
    """
    
    def assemble(
        self,
        base_image_id: str,
        top_n_tastes: list['TasteInfo'],
        gradient_info: 'GradientInfo',
        ingredient_label: str,
        llm_comment: 'LLMComment'
    ) -> 'CocktailOutput':
        """
        최종 출력 데이터 조립 (Requirements 7.1~7.7)
        
        모든 컴포넌트의 결과를 받아 CocktailOutput 객체로 조립합니다.
        
        Args:
            base_image_id: 선택된 베이스 이미지 ID (Requirement 7.1)
            top_n_tastes: Top-N 맛 정보 리스트 (1~3개) (Requirements 7.2, 7.3)
            gradient_info: 그라데이션 정보 (Requirement 7.4)
            ingredient_label: 성분표 텍스트 (Requirement 7.5)
            llm_comment: LLM이 생성한 칵테일 이름과 위로 코멘트 (Requirements 7.6, 7.7)
            
        Returns:
            CocktailOutput: 모든 정보를 포함하는 최종 출력 객체
        """
        from .models import CocktailOutput
        
        # 모든 필드를 포함하는 CocktailOutput 생성
        return CocktailOutput(
            base_image_id=base_image_id,  # Requirement 7.1
            top_n_tastes=top_n_tastes,  # Requirements 7.2, 7.3
            gradient_info=gradient_info,  # Requirement 7.4
            ingredient_label=ingredient_label,  # Requirement 7.5
            cocktail_name=llm_comment.cocktail_name,  # Requirement 7.6
            comfort_message=llm_comment.comfort_message  # Requirement 7.7
        )
