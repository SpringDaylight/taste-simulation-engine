"""
User Preferences API
Endpoints for saving and retrieving user taste preferences
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import io

from db import get_db
from repositories.user_preference import UserPreferenceRepository
from schemas import UserPreferenceResponse, MessageResponse
from pydantic import BaseModel, Field

try:
    from wordcloud import WordCloud
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import threading
    plot_lock = threading.Lock()
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False


router = APIRouter(prefix="/api/user-preferences", tags=["User Preferences"])


# ============================================
# Request Schemas
# ============================================

class SaveUserPreferenceRequest(BaseModel):
    """Request schema for saving user preference"""
    user_id: str = Field(..., description="User ID")
    preference_vector_json: Dict[str, Any] = Field(
        ...,
        description="Preference vector containing emotion_scores, narrative_traits, direction_mood, character_relationship, ending_preference"
    )
    persona_code: Optional[str] = Field(None, description="User persona code")
    boost_tags: List[str] = Field(default_factory=list, description="List of liked tags")
    dislike_tags: List[str] = Field(default_factory=list, description="List of disliked tags")
    penalty_tags: List[str] = Field(default_factory=list, description="List of penalty tags")
    
    # Survey fields
    favorite_genres: Optional[List[str]] = Field(None, description="좋아하는 장르 리스트")
    disliked_genres: Optional[List[str]] = Field(None, description="싫어하는 장르 리스트")
    viewing_context: Optional[str] = Field(None, description="영화 감상 맥락")
    preferred_vibe: Optional[str] = Field(None, description="선호 분위기")
    interest_keywords: Optional[List[str]] = Field(None, description="관심 키워드 리스트")
    preferred_origin: Optional[str] = Field(None, description="선호 국적")


# ============================================
# Endpoints
# ============================================

@router.get("/{user_id}", response_model=UserPreferenceResponse)
def get_user_preference(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user preference by user_id
    
    Returns the saved user taste preference including:
    - preference_vector_json: emotion_scores, narrative_traits, etc.
    - boost_tags: liked tags
    - dislike_tags: disliked tags
    - penalty_tags: penalty tags
    - Survey fields: favorite_genres, disliked_genres, viewing_context, etc.
    """
    repo = UserPreferenceRepository(db)
    preference = repo.get_by_user_id(user_id)
    
    if not preference:
        raise HTTPException(
            status_code=404,
            detail=f"User preference not found for user_id: {user_id}"
        )
    
    return UserPreferenceResponse(
        user_id=preference.user_id,
        preference_vector_json=preference.preference_vector_json,
        persona_code=preference.persona_code,
        boost_tags=preference.boost_tags,
        penalty_tags=preference.penalty_tags,
        favorite_genres=preference.favorite_genres,
        disliked_genres=preference.disliked_genres,
        viewing_context=preference.viewing_context,
        preferred_vibe=preference.preferred_vibe,
        interest_keywords=preference.interest_keywords,
        preferred_origin=preference.preferred_origin,
        updated_at=preference.updated_at
    )


@router.post("", response_model=UserPreferenceResponse, status_code=201)
def save_user_preference(
    request: SaveUserPreferenceRequest,
    db: Session = Depends(get_db)
):
    """
    Save or update user preference (upsert)
    
    If preference exists for the user, it will be updated.
    Otherwise, a new preference will be created.
    
    Request body should include:
    - user_id: User identifier
    - preference_vector_json: Complete preference vector
    - boost_tags: List of liked tags (optional)
    - dislike_tags: List of disliked tags (optional)
    - penalty_tags: List of penalty tags (optional)
    """
    repo = UserPreferenceRepository(db)
    
    preference = repo.upsert(
        user_id=request.user_id,
        preference_vector_json=request.preference_vector_json,
        persona_code=request.persona_code,
        boost_tags=request.boost_tags,
        dislike_tags=request.dislike_tags,
        penalty_tags=request.penalty_tags,
        favorite_genres=request.favorite_genres,
        disliked_genres=request.disliked_genres,
        viewing_context=request.viewing_context,
        preferred_vibe=request.preferred_vibe,
        interest_keywords=request.interest_keywords,
        preferred_origin=request.preferred_origin
    )
    
    return UserPreferenceResponse(
        user_id=preference.user_id,
        preference_vector_json=preference.preference_vector_json,
        persona_code=preference.persona_code,
        boost_tags=preference.boost_tags,
        penalty_tags=preference.penalty_tags,
        favorite_genres=preference.favorite_genres,
        disliked_genres=preference.disliked_genres,
        viewing_context=preference.viewing_context,
        preferred_vibe=preference.preferred_vibe,
        interest_keywords=preference.interest_keywords,
        preferred_origin=preference.preferred_origin,
        updated_at=preference.updated_at
    )


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user_preference(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete user preference by user_id
    """
    repo = UserPreferenceRepository(db)
    
    if not repo.exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User preference not found for user_id: {user_id}"
        )
    
    success = repo.delete_by_user_id(user_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user preference"
        )
    
    return MessageResponse(message=f"User preference deleted for user_id: {user_id}")


@router.get("/{user_id}/exists")
def check_user_preference_exists(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if user preference exists
    """
    repo = UserPreferenceRepository(db)
    exists = repo.exists(user_id)
    
    return {
        "user_id": user_id,
        "exists": exists
    }


@router.post("/{user_id}/update-from-review", response_model=dict)
def update_preference_from_review(
    user_id: str,
    movie_id: int = Query(..., description="Movie ID"),
    rating: float = Query(..., ge=0.5, le=5.0, description="Rating (0.5~5.0)"),
    review_text: Optional[str] = Query(None, description="Review text (optional)"),
    learning_rate: float = Query(0.15, ge=0.01, le=0.5, description="Learning rate (0.01~0.5)"),
    db: Session = Depends(get_db)
):
    """
    Update user preference based on review
    
    리뷰 작성 시 자동으로 호출되어 사용자 취향을 업데이트합니다.
    
    Parameters:
    - user_id: User ID
    - movie_id: Movie ID
    - rating: Review rating (0.5~5.0)
    - review_text: Review text (optional, for movie vector update)
    - learning_rate: How much to adjust preference (default: 0.15)
    
    Returns:
    - success: Whether update was successful
    - message: Status message
    - updated_at: Timestamp of update
    """
    from services.preference_updater import PreferenceUpdater
    
    updater = PreferenceUpdater(db)
    result = updater.update_from_review(
        user_id=user_id,
        movie_id=movie_id,
        rating=rating,
        review_text=review_text,
        learning_rate=learning_rate
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Failed to update preference")
        )
    
    return result


@router.get("/{user_id}/wordcloud")
def get_user_wordcloud(
    user_id: str,
    type: str = "both",
    db: Session = Depends(get_db)
):
    """
    Generate and return a word cloud image for the user's taste tags.
    type: 'boost' (liked), 'dislike' (disliked), 'both'
    """
    if not HAS_WORDCLOUD:
        raise HTTPException(
            status_code=501,
            detail="wordcloud / matplotlib not installed. Run: pip install wordcloud matplotlib"
        )

    repo = UserPreferenceRepository(db)
    preference = repo.get_by_user_id(user_id)

    if not preference:
        raise HTTPException(status_code=404, detail=f"No preference found for user {user_id}")

    boost_tags: list = preference.boost_tags or []
    pref_vector = preference.preference_vector_json or {}
    
    # preference_vector_json에서 global 프로필 추출
    if 'global' in pref_vector:
        # 신 형식: global 키가 있는 경우
        pref_vector = pref_vector['global']
    # 구 형식은 그대로 사용
    
    # emotion_scores: {"감동적이에요": 0.85, ...}
    emotion_scores: dict = pref_vector.get("emotion_scores", {})

    import os as _os
    _FONT_CANDIDATES = [
        "C:/Windows/Fonts/malgun.ttf",                              # Windows
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",          # Ubuntu/Debian (fonts-nanum)
        "/usr/share/fonts/nanum/NanumGothic.ttf",                   # Amazon Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Noto CJK
        "/Library/Fonts/AppleGothic.ttf",                          # macOS
    ]
    FONT_PATH = next(
        (p for p in _FONT_CANDIDATES if _os.path.exists(p)),
        None  # 없으면 None → wordcloud 기본폰트 사용 (한글 깨질 수 있음)
    )

    def make_wc_from_freq(freq: dict, colormap: str, width=600, height=400):
        """주파수 딕셔너리로 워드클라우드 생성"""
        return WordCloud(
            font_path=FONT_PATH,
            width=width,
            height=height,
            background_color="white",
            colormap=colormap,
            relative_scaling=0.5,
            min_font_size=10,
        ).generate_from_frequencies(freq)

    def make_wc_from_list(tags: list, colormap: str, width=600, height=400):
        """태그 리스트로 워드클라우드 생성 (앞쪽 태그일수록 가중치 높음)"""
        freq = {tag: (len(tags) - i) for i, tag in enumerate(tags)}
        return make_wc_from_freq(freq, colormap, width, height)

    from matplotlib.font_manager import FontProperties
    # FONT_PATH가 None이면 fname 인자 없이 기본 폰트 사용
    fp = FontProperties(fname=FONT_PATH) if FONT_PATH else FontProperties()
    fp_bold = FontProperties(fname=FONT_PATH, weight='bold') if FONT_PATH else FontProperties(weight='bold')

    with plot_lock:
        if type == "boost":
            narrative_traits: dict = pref_vector.get("narrative_traits", {})
            freq = {}
            for k, v in narrative_traits.items():
                if v >= 0.1:
                    freq[k] = v * 10
            for i, tag in enumerate(boost_tags):
                freq[tag] = freq.get(tag, 0) + max(2, len(boost_tags) - i)
                
            fig, ax = plt.subplots(figsize=(10, 5))
            if not freq:
                ax.text(0.5, 0.5, "단어 부족", ha="center", va="center", fontsize=13, fontproperties=fp, color="#888888")
                ax.axis("off")
            else:
                ax.imshow(make_wc_from_freq(freq, "Blues"), interpolation="bilinear")
                ax.axis("off")
                
        elif type == "emotion":
            # 영화 영양 성분표 (Nutrition Facts)
            
            # 취향 데이터 파싱 및 통계 생성
            emotions = pref_vector.get("emotion_scores", {})
            moods = pref_vector.get("direction_mood", {})
            narratives = pref_vector.get("narrative_traits", {})
            
            # 핵심 4개 성분 점수 (평균 기반 → 0~100 범위 유지)
            dopamine_score = max(0, moods.get("긴장되는", 0)) * 100
            sensitivity_score = max(0, (emotions.get("감동적이에요", 0) + emotions.get("슬퍼요", 0) + emotions.get("따뜻해요", 0)) / 3) * 100
            brain_score = max(0, (narratives.get("생각하면서 봐야 해요", 0) + pref_vector.get("ending_preference", {}).get("open", 0) * 0.3) / 2) * 100
            eye_score = max(0, (moods.get("영상미가 뛰어나요", 0) + emotions.get("몽환적이에요", 0)) / 2) * 100

            # 칼로리 동적 계산 (4개 성분 합산 기반, 400~2800 kcal 범위)
            total_energy = dopamine_score + sensitivity_score + brain_score + eye_score
            calories_kcal = int(total_energy * 6 + 400)
            
            # 특별 첨가물 추출 (가장 높은 3개 특징)
            all_traits = {**emotions, **moods, **narratives}
            top_traits = sorted(all_traits.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # 캔버스 설정 (가로로 좀 더 길게 8:8 -> 10:8)
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.set_facecolor('white')
            ax.axis([0, 10, 0, 15]) # x: 0~10, y: 0~15 가상 좌표계
            ax.axis('off')
            
            y = 14.5
            
            # 헤더
            ax.text(0.5, y, "Nutrition Facts", fontsize=32, fontproperties=fp_bold)
            y -= 0.8
            ax.text(0.5, y, "당신의 영화 영양 성분표", fontsize=16, fontproperties=fp, color="#4b5563")
            y -= 0.6
            ax.axhline(y, color='black', linewidth=14, xmin=0.05, xmax=0.95)
            y -= 0.8
            
            # 칼로리 정보
            ax.text(0.5, y, "영화 관람 열량 (리뷰 에너지)", fontsize=14, fontproperties=fp_bold)
            y -= 1.0
            ax.text(0.5, y, "Calories", fontsize=24, fontproperties=fp_bold)
            ax.text(9.5, y, f"{calories_kcal:,} kcal", fontsize=28, ha='right', fontproperties=fp_bold)
            y -= 0.5
            ax.axhline(y, color='black', linewidth=6, xmin=0.05, xmax=0.95)
            y -= 0.7
            
            ax.text(9.5, y, "% Daily Value*", fontsize=11, ha='right', fontproperties=fp_bold)
            y -= 0.4
            ax.axhline(y, color='black', linewidth=1, xmin=0.05, xmax=0.95)
            y -= 0.8
            
            # 영양소 항목들 그리기
            def draw_nutrient(y_pos, name, score, color_hex):
                ax.text(0.5, y_pos, name, fontsize=15, fontproperties=fp_bold)
                # 퍼센트 표시: 상한 80% (100%가 나오지 않도록)
                pct_val = min(90, max(0, int(score)))
                
                # 퍼센트가 0일 경우에도 약간은 채워지게 보이는 버그 수정 
                # (pct_val이 표시 퍼센트이자 막대 길이를 결정하도록 통일)
                ax.text(9.5, y_pos, f"{pct_val}%", fontsize=15, ha='right', fontproperties=fp_bold)
                
                # 배경 빈 막대
                ax.axhline(y_pos - 0.35, color='#f3f4f6', linewidth=16, xmin=0.05, xmax=0.95)
                # 채워진 % 막대 (최소 0.05에서 최대 0.95까지, 퍼센트에례)
                # 예를 들어 pct_val이 50%이면 0.05 + 0.9 * 0.5 = 0.5
                fill_xmax = 0.05 + 0.9 * (pct_val / 100.0)
                if pct_val > 0:
                    ax.axhline(y_pos - 0.35, color=color_hex, linewidth=16, xmin=0.05, xmax=fill_xmax)
                
                # 하단 구분선
                ax.axhline(y_pos - 0.7, color='black', linewidth=1, xmin=0.05, xmax=0.95)
                return y_pos - 1.4
                
            y = draw_nutrient(y, "도파민 (스릴/전개속도)", dopamine_score, "#ef4444")
            y = draw_nutrient(y, "감수성 (감동/가족/눈물)", sensitivity_score, "#3b82f6")
            y = draw_nutrient(y, "두뇌회전 (사색/열린결말)", brain_score, "#8b5cf6")
            y = draw_nutrient(y, "안구정화 (영상미/연출)", eye_score, "#10b981")
            
            # 하단 굵은 줄
            y += 0.2
            ax.axhline(y, color='black', linewidth=10, xmin=0.05, xmax=0.95)
            y -= 0.6
            
            # 첨가물
            ax.text(0.5, y, "Contains:", fontsize=13, fontproperties=fp_bold)
            y -= 0.6
            ingredients = ", ".join([f"[{k}] {int(v*100)}mg" for k, v in top_traits]) if top_traits else "없음"
            ax.text(0.5, y, f"특별 첨가물: {ingredients}", fontsize=12, fontproperties=fp, color="#374151")
            
            y -= 0.8
            ax.axhline(y, color='black', linewidth=1, xmin=0.05, xmax=0.95)
            y -= 0.5
            ax.text(0.5, y, "* 1일 장르 권장량은 관람자의 감정 상태에 따라 다를 수 있습니다.", fontsize=10, fontproperties=fp, color="#6b7280")
            
        else:  # both: 왼쪽=정서태그(리뷰 기반), 오른쪽=좋아하는태그
            fig, axes = plt.subplots(1, 2, figsize=(20, 6))
            # 두 패널 사이 간격 조정
            plt.subplots_adjust(wspace=0.25)
    
            # 왼쪽: 정서태그 - emotion_scores 중 임계값 이상만 (설문 초기값 제외)
            EMOTION_THRESHOLD = 0.25
            review_emotions = {k: v for k, v in emotion_scores.items() if v >= EMOTION_THRESHOLD}
    
            if review_emotions:
                axes[0].imshow(make_wc_from_freq(review_emotions, "Purples"), interpolation="bilinear")
            else:
                axes[0].text(0.5, 0.5, "리뷰를 더 남겨보세요!", ha="center", va="center",
                             fontsize=13, fontproperties=fp, color="#888888")
            axes[0].axis("off")
    
            # 오른쪽: 좋아하는 태그 (boost_tags, 파랑 계열)
            if boost_tags:
                axes[1].imshow(make_wc_from_list(boost_tags, "Blues"), interpolation="bilinear")
            else:
                axes[1].text(0.5, 0.5, "데이터 없음", ha="center", va="center",
                             fontsize=14, fontproperties=fp)
            axes[1].axis("off")
    
        plt.tight_layout(pad=0)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
