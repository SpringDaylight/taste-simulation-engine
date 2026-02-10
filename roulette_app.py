from flask import Flask, jsonify, request
from flask_cors import CORS
import random

# ============================================
# ProbabilityEngine 클래스
# ============================================
class ProbabilityEngine:
    """
    확률 기반 상품 선택 엔진
    
    각 상품의 등급별 확률:
    - C등급 (팝콘): 50%
    - B등급 (핫도그): 25%, (콤보): 15%
    - A등급 (오징어): 9%
    - S등급 (치킨): 1%
    """
    
    def __init__(self):
        """5개 상품의 확률 설정"""
        self.probabilities = {
            "팝콘": 0.50,    # C등급 - 가장 흔함
            "핫도그": 0.25,  # B등급
            "콤보": 0.15,    # B등급
            "오징어": 0.09,  # A등급 - 희귀
            "치킨": 0.01     # S등급 - 매우 희귀
        }
    
    def select_prize(self):
        """
        가중치 기반 랜덤 선택
        
        알고리즘:
        1. 0-1 사이 난수 생성
        2. 누적 확률과 비교하여 상품 선택
        
        Returns:
            str: 선택된 상품명
        """
        random_value = random.random()
        cumulative = 0.0
        
        for prize, probability in self.probabilities.items():
            cumulative += probability
            if random_value < cumulative:
                return prize
        
        # fallback (확률 합이 1.0이 아닐 경우)
        return "팝콘"


# ============================================
# AngleCalculator 클래스
# ============================================
class AngleCalculator:
    """
    상품명을 룰렛 각도로 변환하는 계산기
    
    룰렛은 5개 섹션으로 균등 분할 (각 72도)
    각 상품의 중심 각도를 반환
    """
    
    def __init__(self):
        """
        각 상품의 중심 각도 매핑
        - 팝콘: 36° (0-72° 섹션의 중심)
        - 핫도그: 108° (72-144° 섹션의 중심)
        - 콤보: 180° (144-216° 섹션의 중심)
        - 오징어: 252° (216-288° 섹션의 중심)
        - 치킨: 324° (288-360° 섹션의 중심)
        """
        self.angle_map = {
            "팝콘": 36,
            "핫도그": 108,
            "콤보": 180,
            "오징어": 252,
            "치킨": 324
        }
    
    def get_target_angle(self, prize):
        """
        상품의 목표 각도 반환
        
        Args:
            prize (str): 상품명
            
        Returns:
            float: 목표 각도 (0-360)
        """
        return self.angle_map.get(prize, 0)


# ============================================
# Flask 애플리케이션 설정
# ============================================
app = Flask(__name__)

# CORS 설정 - 모든 origin에서의 요청 허용 (로컬 HTML 파일 접근 가능)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

# 확률 엔진과 각도 계산기 초기화
probability_engine = ProbabilityEngine()
angle_calculator = AngleCalculator()


# ============================================
# API 엔드포인트
# ============================================

@app.route('/')
def index():
    """기본 엔드포인트 - 서버 상태 확인"""
    return jsonify({
        "status": "running",
        "message": "Equal Roulette Backend Server"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        "status": "healthy",
        "service": "equal-roulette"
    })

@app.route('/api/spin', methods=['POST'])
def spin():
    """
    룰렛 스핀 API
    
    Request: POST /api/spin
    Response: {
        "prize": str,  # 상품명 (팝콘, 핫도그, 콤보, 오징어, 치킨)
        "target_angle": float  # 목표 각도 (0-360)
    }
    """
    try:
        # 1. 확률 기반으로 상품 선택
        prize = probability_engine.select_prize()
        
        # 2. 선택된 상품의 목표 각도 계산
        target_angle = angle_calculator.get_target_angle(prize)
        
        # 3. JSON 응답 반환
        return jsonify({
            "prize": prize,
            "target_angle": target_angle
        }), 200
        
    except Exception as e:
        # 내부 서버 오류 처리
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


# ============================================
# 서버 실행
# ============================================
if __name__ == '__main__':
    """
    개발 서버 실행
    - host='0.0.0.0': 외부 접근 허용
    - port=5000: 포트 5000에서 실행
    - debug=True: 디버그 모드 활성화 (코드 변경 시 자동 재시작)
    """
    app.run(host='0.0.0.0', port=5000, debug=True)
