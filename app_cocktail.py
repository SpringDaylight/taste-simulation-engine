"""
Emotion Cocktail Generator - Web Application

媛먯젙 湲곕컲 移듯뀒???앹꽦 ?쒖뒪?쒖쓽 ???좏뵆由ъ??댁뀡?낅땲??
Flask瑜??ъ슜?섏뿬 ???섏씠吏? API瑜??쒓났?⑸땲??
"""

import logging
import os
import json
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

from src.emotion_cocktail_generator import EmotionCocktailGenerator
from src.image_renderer import CocktailImageRenderer

# ?섍꼍 蹂??濡쒕뱶
load_dotenv()

# Flask ??珥덇린??
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# 濡쒓퉭 ?ㅼ젙
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# EmotionCocktailGenerator ?몄뒪?댁뒪 ?앹꽦
bedrock_region = os.getenv('BEDROCK_REGION') or os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION')
bedrock_model_id = os.getenv('BEDROCK_MODEL_ID')
cocktail_generator = None
try:
    cocktail_generator = EmotionCocktailGenerator(
        bedrock_region=bedrock_region,
        bedrock_model_id=bedrock_model_id
    )
except Exception as e:
    logger.exception(f"EmotionCocktailGenerator initialization failed: {e}")

# CocktailImageRenderer ?몄뒪?댁뒪 ?앹꽦
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
image_renderer = CocktailImageRenderer(output_dir=OUTPUT_DIR)

# ?붾? ?곗씠???뚯씪 寃쎈줈
DEMO_DATA_PATH = os.path.join(BASE_DIR, "cocktail_input_demo.json")
MOVIEMONG_DATA_PATH = os.path.join(BASE_DIR, "moviemong_demo_data.json")

FLAVOR_KEY_MAP = {
    'sweet': 'sweet',
    'spicy': 'spicy',
    'onion': 'onion',
    'cheese': 'cheese',
    'dark': 'dark',
    'salty': 'salty',
    'mint': 'mint',
}


def _safe_slug(value: str, max_length: int = 20) -> str:
    """Build a filesystem-safe slug fragment for output filenames."""
    candidate = (value or "").strip().replace(" ", "_")
    candidate = re.sub(r"[^0-9A-Za-z_-]+", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    if not candidate:
        return "cocktail"
    return candidate[:max_length]


def load_demo_data():
    """
    ?붾? ?곗씠???뚯씪?먯꽌 移듯뀒???낅젰 ?곗씠??濡쒕뱶
    
    Returns:
        dict: 移듯뀒???낅젰 ?곗씠??
    """
    try:
        if os.path.exists(DEMO_DATA_PATH):
            with open(DEMO_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"?붾? ?곗씠??濡쒕뱶 ?깃났: {data}")
                return data
        else:
            logger.warning(f"?붾? ?곗씠???뚯씪??李얠쓣 ???놁뒿?덈떎: {DEMO_DATA_PATH}")
            return None
    except Exception as e:
        logger.error(f"?붾? ?곗씠??濡쒕뱶 以??ㅻ쪟 諛쒖깮: {e}")
        return None


def load_taste_input_from_moviemong() -> dict | None:
    """Load flavor_stats from moviemong_demo_data.json and normalize keys."""
    try:
        if not os.path.exists(MOVIEMONG_DATA_PATH):
            logger.warning(f"Moviemong data file not found: {MOVIEMONG_DATA_PATH}")
            return None

        with open(MOVIEMONG_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict) or not data:
            logger.warning("Moviemong data is empty or invalid.")
            return None

        first_user_data = next(iter(data.values()))
        flavor_stats = first_user_data.get('flavor_stats', {}) if isinstance(first_user_data, dict) else {}
        if not isinstance(flavor_stats, dict):
            logger.warning("flavor_stats is missing or invalid.")
            return None

        taste_input = {
            'sweet': 0,
            'spicy': 0,
            'onion': 0,
            'cheese': 0,
            'dark': 0,
            'salty': 0,
            'mint': 0,
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


@app.route('/')
def index():
    """硫붿씤 ?섏씠吏"""
    return render_template('cocktail.html')


@app.route('/generate-cocktail', methods=['POST'])
def generate_cocktail():
    """
    媛먯젙 湲곕컲 移듯뀒???앹꽦 API ?붾뱶?ъ씤??
    
    POST /generate-cocktail
    
    Request Body (JSON):
    {} (鍮?媛앹껜) - cocktail_input_demo.json ?뚯씪?먯꽌 ?곗씠??濡쒕뱶
    ?먮뒗
    {
        "sweet": int,
        "spicy": int,
        "onion": int,
        "cheese": int,
        "dark": int,
        "salty": int,
        "mint": int
    }
    
    Response (JSON):
    {
        "success": true,
        "data": {
            "image_url": str,
            "ingredient_label": str,
            "cocktail_name": str,
            "comfort_message": str,
            "gradient_colors": [str]
        }
    }
    """
    try:
        if cocktail_generator is None:
            return jsonify({
                'success': False,
                'error': 'Cocktail generator is not initialized. Check Bedrock/AWS environment settings.'
            }), 500

        if not request.is_json:
            return jsonify({
                'success': False,
                'error': '?붿껌? JSON ?뺤떇?댁뼱???⑸땲??'
            }), 400
        
        taste_input = request.get_json()
        
        # 鍮?媛앹껜媛 ?ㅼ뼱??寃쎌슦 ?먮뒗 ?꾩닔 ?ㅺ? ?녿뒗 寃쎌슦 ?붾? ?곗씠???뚯씪?먯꽌 濡쒕뱶
        required_keys = ['sweet', 'spicy', 'onion', 'cheese', 'dark', 'salty', 'mint']
        has_all_keys = taste_input and all(key in taste_input for key in required_keys)
        
        if not has_all_keys:
            logger.info("No complete payload. Trying moviemong flavor_stats first.")
            taste_input = load_taste_input_from_moviemong()
            if taste_input is None:
                logger.info("Fallback to cocktail_input_demo.json")
                taste_input = load_demo_data()

            if taste_input is None:
                return jsonify({
                    'success': False,
                    'error': 'No valid input source found. Check moviemong_demo_data.json or cocktail_input_demo.json.'
                }), 400

            logger.info(f"Loaded fallback taste input: {taste_input}")
        else:
            logger.info(f"Client payload used: {taste_input}")
        
        # 移듯뀒???앹꽦
        cocktail_output = cocktail_generator.generate(taste_input)
        
        # ?대?吏 ?앹꽦 (?대━怨?諛⑹떇 ?ъ슜)
        safe_name = _safe_slug(cocktail_output.cocktail_name)
        image_filename = f"cocktail_{safe_name}.png"
        image_path = image_renderer.render_cocktail_with_polygon(
            gradient_colors=cocktail_output.gradient_info.colors,
            output_filename=image_filename
        )
        
        logger.info(f"移듯뀒???대?吏 ?앹꽦 ?꾨즺: {image_path}")
        
        return jsonify({
            'success': True,
            'data': {
                'image_url': f'/output/{image_filename}',
                'ingredient_label': cocktail_output.ingredient_label,
                'cocktail_name': cocktail_output.cocktail_name,
                'comfort_message': cocktail_output.comfort_message,
                'gradient_colors': cocktail_output.gradient_info.colors
            }
        }), 200
    
    except ValueError as e:
        logger.warning(f"?낅젰 寃利??ㅽ뙣: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"移듯뀒???앹꽦 以??ㅻ쪟 諛쒖깮: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': '?쒕쾭 ?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎. ?좎떆 ???ㅼ떆 ?쒕룄?댁＜?몄슂.'
        }), 500


@app.route('/output/<filename>')
def serve_output(filename):
    """?앹꽦???대?吏 ?쒓났"""
    return send_from_directory(OUTPUT_DIR, filename)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Flask ?쒕쾭 ?쒖옉 (?ы듃: {port}, ?붾쾭洹? {debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
