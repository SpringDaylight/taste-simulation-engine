"""
Emotion Cocktail Generator - Web Application

감정 기반 칵테일 생성 시스템의 Flask 웹 애플리케이션.
웹 페이지와 API를 제공한다.
"""

import logging
import os
import json
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

from cocktail.emotion_cocktail_generator import EmotionCocktailGenerator
from cocktail.image_renderer import CocktailImageRenderer

# 환경 변수 로드
load_dotenv()

# Flask 앱 초기화
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# EmotionCocktailGenerator 인스턴스 생성
bedrock_region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
bedrock_model_id = os.getenv("BEDROCK_MODEL_ID")
cocktail_generator = None
try:
    cocktail_generator = EmotionCocktailGenerator(
        bedrock_region=bedrock_region,
        bedrock_model_id=bedrock_model_id,
    )
except Exception as e:
    logger.exception(f"EmotionCocktailGenerator initialization failed: {e}")

# CocktailImageRenderer 인스턴스 생성
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
image_renderer = CocktailImageRenderer(output_dir=OUTPUT_DIR)

# 입력 데이터 파일 경로
DEMO_DATA_PATH = os.path.join(BASE_DIR, "cocktail_input_demo.json")
MOVIEMONG_DATA_PATH = os.path.join(BASE_DIR, "moviemong_demo_data.json")

FLAVOR_KEY_MAP = {
    "sweet": "sweet",
    "spicy": "spicy",
    "onion": "onion",
    "cheese": "cheese",
    "dark": "dark",
    "salty": "salty",
    "mint": "mint",
}


def _safe_slug(value: str, max_length: int = 20) -> str:
    """출력 파일명에 안전한 slug를 생성한다."""
    candidate = (value or "").strip().replace(" ", "_")
    candidate = re.sub(r"[^0-9A-Za-z_-]+", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    if not candidate:
        return "cocktail"
    return candidate[:max_length]


def load_demo_data():
    """
    cocktail_input_demo.json에서 칵테일 입력 데이터를 로드한다.

    Returns:
        dict | None: 칵테일 입력 데이터
    """
    try:
        if os.path.exists(DEMO_DATA_PATH):
            with open(DEMO_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"데모 데이터 로드 성공: {data}")
                return data
        logger.warning(f"데모 데이터 파일을 찾을 수 없습니다: {DEMO_DATA_PATH}")
        return None
    except Exception as e:
        logger.error(f"데모 데이터 로드 중 오류 발생: {e}")
        return None


def load_taste_input_from_moviemong() -> dict | None:
    """moviemong_demo_data.json의 flavor_stats를 칵테일 입력 형식으로 변환한다."""
    try:
        if not os.path.exists(MOVIEMONG_DATA_PATH):
            logger.warning(f"Moviemong data file not found: {MOVIEMONG_DATA_PATH}")
            return None

        with open(MOVIEMONG_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or not data:
            logger.warning("Moviemong data is empty or invalid.")
            return None

        first_user_data = next(iter(data.values()))
        flavor_stats = first_user_data.get("flavor_stats", {}) if isinstance(first_user_data, dict) else {}
        if not isinstance(flavor_stats, dict):
            logger.warning("flavor_stats is missing or invalid.")
            return None

        taste_input = {
            "sweet": 0,
            "spicy": 0,
            "onion": 0,
            "cheese": 0,
            "dark": 0,
            "salty": 0,
            "mint": 0,
        }

        for raw_key, raw_value in flavor_stats.items():
            mapped_key = FLAVOR_KEY_MAP.get(str(raw_key).strip().lower())
            if mapped_key is None:
                continue
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                continue
            taste_input[mapped_key] = max(0, value)

        logger.info(f"Loaded taste input from moviemong flavor_stats: {taste_input}")
        return taste_input
    except Exception as e:
        logger.error(f"Failed to load moviemong flavor_stats: {e}")
        return None


@app.route("/")
def index():
    """메인 페이지"""
    return render_template("cocktail.html")


@app.route("/generate-cocktail", methods=["POST"])
def generate_cocktail():
    """
    감정 기반 칵테일 생성 API 엔드포인트.

    POST /generate-cocktail

    Request Body (JSON):
    {} (빈 객체) - moviemong_demo_data.json / cocktail_input_demo.json에서 로드
    또는
    {
      "sweet": int, "spicy": int, "onion": int, "cheese": int,
      "dark": int, "salty": int, "mint": int
    }
    """
    try:
        if cocktail_generator is None:
            return jsonify(
                {
                    "success": False,
                    "error": "Cocktail generator is not initialized. Check Bedrock/AWS environment settings.",
                }
            ), 500

        if not request.is_json:
            return jsonify({"success": False, "error": "요청은 JSON 형식이어야 합니다."}), 400

        taste_input = request.get_json()
        required_keys = ["sweet", "spicy", "onion", "cheese", "dark", "salty", "mint"]
        has_all_keys = taste_input and all(key in taste_input for key in required_keys)

        if not has_all_keys:
            logger.info("No complete payload. Trying moviemong flavor_stats first.")
            taste_input = load_taste_input_from_moviemong()
            if taste_input is None:
                logger.info("Fallback to cocktail_input_demo.json")
                taste_input = load_demo_data()

            if taste_input is None:
                return jsonify(
                    {
                        "success": False,
                        "error": "No valid input source found. Check moviemong_demo_data.json or cocktail_input_demo.json.",
                    }
                ), 400

            logger.info(f"Loaded fallback taste input: {taste_input}")
        else:
            logger.info(f"Client payload used: {taste_input}")

        cocktail_output = cocktail_generator.generate(taste_input)

        safe_name = _safe_slug(cocktail_output.cocktail_name)
        image_filename = f"cocktail_{safe_name}.png"
        image_path = image_renderer.render_cocktail_with_polygon(
            gradient_colors=cocktail_output.gradient_info.colors,
            output_filename=image_filename,
        )

        logger.info(f"칵테일 이미지 생성 완료: {image_path}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "image_url": f"/output/{image_filename}",
                    "ingredient_label": cocktail_output.ingredient_label,
                    "cocktail_name": cocktail_output.cocktail_name,
                    "comfort_message": cocktail_output.comfort_message,
                    "gradient_colors": cocktail_output.gradient_info.colors,
                },
            }
        ), 200

    except ValueError as e:
        logger.warning(f"입력 검증 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"칵테일 생성 중 오류 발생: {e}", exc_info=True)
        return jsonify(
            {
                "success": False,
                "error": "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            }
        ), 500


@app.route("/output/<filename>")
def serve_output(filename):
    """생성된 이미지를 반환한다."""
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    logger.info(f"Flask 서버 시작 (포트: {port}, 디버그: {debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)
