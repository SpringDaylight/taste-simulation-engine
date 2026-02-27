from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from db import get_db
from ai.gamification import MovieMong
from pydantic import BaseModel
from typing import List, Dict, Optional

# Router Define
router = APIRouter(prefix="/api", tags=["gamification"])

# Demo User ID (Temporary)
DEMO_USER_ID = "user_demo"

# --- Request Schemas ---
class ReviewRequest(BaseModel):
    review: str

class AnswerRequest(BaseModel):
    answer: str

class ShopRequest(BaseModel):
    theme_id: str

class GroupRecommendRequest(BaseModel):
    users: List[Dict]
    target_movie_id: Optional[int] = None
    target_movie_title: Optional[str] = None

# --- Endpoints ---

@router.get("/home")
def get_home(db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    return mong.get_home_data()

@router.post("/review")
def add_review(req: ReviewRequest, db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    if not req.review:
        raise HTTPException(status_code=400, detail="리뷰 내용을 입력해주세요.")
    
    is_detailed = len(req.review) >= 50
    return mong.add_review(req.review, is_detailed)

@router.post("/feeding")
def play_feeding(db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    return mong.play_roulette()

@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    return mong.get_question_history()

@router.get("/shop")
def get_shop(db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    return mong.get_shop_items()

@router.post("/shop/buy")
def buy_theme(req: ShopRequest, db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    return mong.buy_theme(req.theme_id)

@router.post("/shop/apply")
def apply_theme(req: ShopRequest, db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    return mong.apply_theme(req.theme_id)

@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    user_data = mong.get_user_data()
    return {
        "popcorn": user_data["popcorn"],
        "flavor_stats": user_data["flavor_stats"],
        "owned_themes": user_data.get("owned_themes", ["basic"])
    }

@router.post("/question/answer")
def answer_question(req: AnswerRequest, db: Session = Depends(get_db)):
    mong = MovieMong(DEMO_USER_ID, db)
    if not req.answer:
        raise HTTPException(status_code=400, detail="답변을 입력해주세요.")
    
    return mong.answer_daily_question(req.answer)

# Group Recommendation is stateless, but uses DB for movie data?
# Original code mapped it from embedding.load_json.
# We can include it here or separate router.
# Ideally needs refactoring to use DB instead of JSON if possible, but keep it simple for now.
# Code snippet from app_moviemong:
# result = group_recommendation.analyze_group_satisfaction(...)
# This imported from ai.analysis.
# I'll add it here for completeness if needed, or skip?
# Phase 5 said "Refactor group_recommendation.py for API usage".
# I'll include it.

from ai.analysis import group_recommendation, embedding
import os

# Load Data (Global scope or dependency?)
# For FastAPI, usually lifespan or global.
# We'll keep global for simplicity matching Flask app.
try:
    TAXONOMY = embedding.load_taxonomy()
    # Path might need adjustment depending on where this runs
    # Assuming run from root
    _movies_path = os.path.join("data", "movies_dataset_final.json")
    if os.path.exists(_movies_path):
        GROUPED_MOVIES = embedding.load_json(_movies_path)
    else:
         # Try relative to file
        _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _movies_path = os.path.join(_base, 'data', 'movies_dataset_final.json')
        GROUPED_MOVIES = embedding.load_json(_movies_path)
except:
    TAXONOMY = {}
    GROUPED_MOVIES = []

@router.post("/group/recommend")
def recommend_group(req: GroupRecommendRequest):
    try:
        result = group_recommendation.analyze_group_satisfaction(
            movies=GROUPED_MOVIES,
            taxonomy=TAXONOMY,
            users=req.users,
            target_movie_id=req.target_movie_id,
            target_movie_title=req.target_movie_title
        )
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
