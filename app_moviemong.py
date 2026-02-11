
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import os
import sys

# moviemong 패키지 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'model_sample'))

from moviemong import MovieMong
from database import db, init_db

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# DB 설정
db_path = os.path.join(os.path.dirname(__file__), 'data', 'moviemong.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB 초기화
init_db(app)

# User ID (데모용 고정)
USER_ID = "user_demo"
# data_file 인자 제거
mong = MovieMong(USER_ID)

# --- Cocktail Feature Integration ---
from cocktail.emotion_cocktail_generator import EmotionCocktailGenerator
from cocktail.image_renderer import CocktailImageRenderer
import re

# Initialize Cocktail Components
bedrock_region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION") or "ap-northeast-2"
bedrock_model_id = os.getenv("BEDROCK_MODEL_ID")
cocktail_generator = None
try:
    cocktail_generator = EmotionCocktailGenerator(
        bedrock_region=bedrock_region,
        bedrock_model_id=bedrock_model_id,
    )
except Exception as e:
    print(f"Warning: Cocktail Generator initialization failed: {e}")

# Image Renderer (Output to 'static/output' for web access)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "output")
image_renderer = CocktailImageRenderer(output_dir=OUTPUT_DIR)

FLAVOR_KEY_MAP = {
    "sweet": "sweet", "spicy": "spicy", "onion": "onion",
    "cheese": "cheese", "dark": "dark", "salty": "salty", "mint": "mint",
}

def _safe_slug(value: str, max_length: int = 20) -> str:
    candidate = (value or "").strip().replace(" ", "_")
    candidate = re.sub(r"[^0-9A-Za-z_-]+", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    return candidate[:max_length] if candidate else "cocktail"

@app.route('/api/cocktail', methods=['POST'])
def generate_cocktail():
    if not cocktail_generator:
        return jsonify({"success": False, "error": "Cocktail generator not initialized"}), 500

    try:
        # 1. Attempt to use provided input
        taste_input = {}
        if request.is_json:
            req_data = request.get_json()
            if req_data:
                taste_input = req_data
        
        # 2. If input is empty/incomplete, try to load from MovieMong user data
        required_keys = ["sweet", "spicy", "onion", "cheese", "dark", "salty", "mint"]
        if not all(k in taste_input for k in required_keys):
            user_data = mong.get_user_data()
            flavor_stats = user_data.get("flavor_stats", {})
            
            # Map flavor stats (strings/ints) to cocktail input
            for k, v in flavor_stats.items():
                mapped_key = FLAVOR_KEY_MAP.get(str(k).lower())
                if mapped_key:
                    try:
                        taste_input[mapped_key] = int(v)
                    except:
                        pass
            
            # Fill missing with 0
            for k in required_keys:
                if k not in taste_input:
                    taste_input[k] = 0
                    
        # 3. Generate Cocktail
        cocktail_output = cocktail_generator.generate(taste_input)
        
        safe_name = _safe_slug(cocktail_output.cocktail_name)
        image_filename = f"cocktail_{safe_name}.png"
        
        # Render image
        image_renderer.render_cocktail_with_polygon(
            gradient_colors=cocktail_output.gradient_info.colors,
            output_filename=image_filename,
        )
        
        return jsonify({
            "success": True,
            "data": {
                "image_url": f"/static/output/{image_filename}",
                "ingredient_label": cocktail_output.ingredient_label,
                "cocktail_name": cocktail_output.cocktail_name,
                "comfort_message": cocktail_output.comfort_message,
                "gradient_colors": cocktail_output.gradient_info.colors,
            }
        })
        
    except Exception as e:
        print(f"Cocktail generation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
# ------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/home', methods=['GET'])
def get_home():
    return jsonify(mong.get_home_data())

@app.route('/api/question/answer', methods=['POST'])
def answer_question():
    data = request.json
    answer = data.get('answer', '')
    if not answer:
        return jsonify({"success": False, "message": "답변을 입력해주세요."})
        
    result = mong.answer_daily_question(answer)
    return jsonify(result)

@app.route('/api/review', methods=['POST'])
def add_review():
    data = request.json
    review_text = data.get('review', '')
    if not review_text:
        return jsonify({"success": False, "message": "리뷰 내용을 입력해주세요."})
        
    is_detailed = len(review_text) >= 50
    result = mong.add_review(review_text, is_detailed)
    return jsonify(result)

@app.route('/api/feeding', methods=['POST'])
def api_feeding():
    result = mong.play_roulette()
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
def api_history():
    history = mong.get_question_history()
    return jsonify(history)

@app.route('/api/shop', methods=['GET'])
def api_shop():
    items = mong.get_shop_items()
    return jsonify(items)

@app.route('/api/shop/buy', methods=['POST'])
def api_shop_buy():
    data = request.json
    theme_id = data.get('theme_id')
    result = mong.buy_theme(theme_id)
    return jsonify(result)

@app.route('/api/shop/apply', methods=['POST'])
def api_shop_apply():
    data = request.json
    theme_id = data.get('theme_id')
    result = mong.apply_theme(theme_id)
    return jsonify(result)

@app.route('/api/inventory', methods=['GET'])
def api_inventory():
    user_data = mong.get_user_data()
    return jsonify({
        "popcorn": user_data["popcorn"],
        "flavor_stats": user_data["flavor_stats"],
        "owned_themes": user_data.get("owned_themes", ["basic"])
    })

if __name__ == '__main__':
    # 템플릿 폴더 생성 확인
    if not os.path.exists('templates'):
        os.makedirs('templates')
        
    port = int(os.environ.get('PORT', 5000))
    print(f"🎬 Review Mong Web Server Started for '{USER_ID}'")
    app.run(host='0.0.0.0', port=port, debug=True)
