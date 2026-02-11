
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
with app.app_context():
    mong = MovieMong(USER_ID)

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
