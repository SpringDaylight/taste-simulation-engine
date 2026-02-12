import sys
import os

print(f"Python Path: {sys.path}")
print(f"CWD: {os.getcwd()}")

try:
    print("Testing imports...")
    from ai.gamification import MovieMong
    print("✅ ai.gamification.MovieMong imported")
    
    from ai.cocktail.emotion_cocktail_generator import EmotionCocktailGenerator
    print("✅ ai.cocktail.emotion_cocktail_generator imported")
    
    import database
    print("✅ database imported")
    
    import models
    print("✅ models imported")
    
    from app_moviemong import app
    print("✅ app_moviemong imported")
    
    print("\n🎉 All critical imports successful!")
    
except ImportError as e:
    print(f"\n❌ Import Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
