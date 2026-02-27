"""
실제 DB 연결 테스트 스크립트
movie_vectors 테이블에 데이터가 있는지 확인
"""
from db import SessionLocal
from models import MovieVector, Movie
from repositories.movie_vector import MovieVectorRepository

def test_db_connection():
    """DB 연결 및 데이터 확인"""
    db = SessionLocal()
    
    try:
        # 1. movie_vectors 테이블 데이터 개수 확인
        repo = MovieVectorRepository(db)
        total_vectors = repo.count_all()
        print(f"\n✅ movie_vectors 테이블 연결 성공!")
        print(f"📊 총 영화 벡터 개수: {total_vectors}")
        
        if total_vectors == 0:
            print("\n⚠️ movie_vectors 테이블이 비어있습니다!")
            print("   영화 벡터 데이터를 먼저 생성해야 합니다.")
            return
        
        # 2. 샘플 데이터 조회
        print("\n📋 샘플 영화 벡터 (최대 5개):")
        sample_vectors = db.query(MovieVector).limit(5).all()
        
        for mv in sample_vectors:
            movie = db.query(Movie).filter(Movie.id == mv.movie_id).first()
            if movie:
                print(f"\n  - ID: {mv.movie_id}")
                print(f"    제목: {movie.title}")
                print(f"    장르: {[g.genre for g in movie.genres]}")
                print(f"    개봉: {movie.release.year if movie.release else 'N/A'}")
                
                # 감성 점수 상위 3개
                if mv.emotion_scores:
                    top_emotions = sorted(
                        mv.emotion_scores.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:3]
                    print(f"    주요 감성: {', '.join([f'{k}({v:.2f})' for k, v in top_emotions])}")
        
        # 3. movies 테이블 데이터 개수 확인
        total_movies = db.query(Movie).count()
        print(f"\n📊 총 영화 개수 (movies 테이블): {total_movies}")
        
        # 4. 벡터가 없는 영화 개수
        movies_without_vectors = total_movies - total_vectors
        if movies_without_vectors > 0:
            print(f"⚠️ 벡터가 없는 영화: {movies_without_vectors}개")
        
        print("\n✅ DB 연결 테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ DB 연결 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    test_db_connection()
