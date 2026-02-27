from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict
import os
from ai.cocktail.emotion_cocktail_generator import EmotionCocktailGenerator
from ai.cocktail.image_renderer import CocktailImageRenderer
from ai.gamification import MovieMong
from db import get_db

router = APIRouter(prefix="/api", tags=["cocktail"])

# --- Initialization ---
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

# Image Renderer
# Output to static/output relative to root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "output")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

image_renderer = CocktailImageRenderer(output_dir=OUTPUT_DIR)

FLAVOR_KEY_MAP = {
    "sweet": "sweet", "spicy": "spicy", "onion": "onion",
    "cheese": "cheese", "dark": "dark", "salty": "salty", "mint": "mint",
}

# --- Request Schemas ---
class CocktailRequest(BaseModel):
    sweet: Optional[int] = 0
    spicy: Optional[int] = 0
    onion: Optional[int] = 0
    cheese: Optional[int] = 0
    dark: Optional[int] = 0
    salty: Optional[int] = 0
    mint: Optional[int] = 0
    # Add other optional fields if needed

@router.post("/cocktail")
def generate_cocktail(req: CocktailRequest):
    if not cocktail_generator:
        raise HTTPException(status_code=500, detail="Cocktail generator not initialized")

    try:
        # Convert Pydantic to dict
        taste_input = req.dict()
        
        # If all 0, try to use user data?
        # In this router, we don't have direct access to user session freely unless passed.
        # But for now, let's assume client sends data.
        # If we really want to fetch user data, we need db dependency.
        # But let's keep it simple as per original logic which fell back to MovieMong(USER_ID).
        
        if all(v == 0 for v in taste_input.values()):
            # Fallback to demo user logic
            # We need a DB session to get user data
            # But making this endpoint depend on DB might be overkill if we just want it to work.
            # However, original app_moviemong.py used 'mong' global which had 'user_demo'.
            # Let's try to get DB session manually or require it.
            # Since this is a router, we should inject DB.
            pass

        # 3. Generate Cocktail
        cocktail_output = cocktail_generator.generate(taste_input)
        
        # slugify logic (simple version)
        import re
        def _safe_slug(value):
            candidate = (value or "").strip().replace(" ", "_")
            candidate = re.sub(r"[^0-9A-Za-z_-]+", "_", candidate)
            return candidate[:20] if candidate else "cocktail"

        safe_name = _safe_slug(cocktail_output.cocktail_name)
        image_filename = f"cocktail_{safe_name}.png"
        
        # Render image
        image_renderer.render_cocktail_with_polygon(
            gradient_colors=cocktail_output.gradient_info.colors,
            output_filename=image_filename,
        )
        
        return {
            "success": True,
            "data": {
                "image_url": f"/static/output/{image_filename}",
                "ingredient_label": cocktail_output.ingredient_label,
                "cocktail_name": cocktail_output.cocktail_name,
                "comfort_message": cocktail_output.comfort_message,
                "gradient_colors": cocktail_output.gradient_info.colors,
            }
        }
        
    except Exception as e:
        print(f"Cocktail generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
