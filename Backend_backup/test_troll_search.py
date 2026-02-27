"""
트롤 영화 검색 테스트
"""
from db import SessionLocal
from models import Movie
from sqlalchemy import or_

db = SessionLocal()

# 1. 제목에 '트롤' 포함된 영화 검색
print("=" * 80)
print("1. 제목에 '트롤' 포함된 영화")
print("=" * 80)

movies = db.query(Movie).filter(
    or_(
        Movie.title.ilike('%트롤%'),
        Movie.title.ilike('%troll%')
    )
).all()

if movies:
    for movie in movies:
        print(f"\nID: {movie.id}")
        print(f"제목: {movie.title}")
        print(f"개봉: {movie.release}")
        print(f"시놉시스: {movie.synopsis[:100] if movie.synopsis else 'N/A'}...")
else:
    print("제목에 '트롤'이 포함된 영화를 찾을 수 없습니다.")

# 2. 시놉시스에 '트롤' 포함된 영화 검색
print("\n" + "=" * 80)
print("2. 시놉시스에 '트롤' 포함된 영화")
print("=" * 80)

movies = db.query(Movie).filter(
    Movie.synopsis.ilike('%트롤%')
).limit(10).all()

if movies:
    for movie in movies:
        print(f"\nID: {movie.id}")
        print(f"제목: {movie.title}")
        print(f"시놉시스: {movie.synopsis[:100] if movie.synopsis else 'N/A'}...")
else:
    print("시놉시스에 '트롤'이 포함된 영화를 찾을 수 없습니다.")

# 3. '습격' 키워드로 검색
print("\n" + "=" * 80)
print("3. 제목에 '습격' 포함된 영화")
print("=" * 80)

movies = db.query(Movie).filter(
    Movie.title.ilike('%습격%')
).all()

if movies:
    for movie in movies:
        print(f"\nID: {movie.id}")
        print(f"제목: {movie.title}")
        print(f"개봉: {movie.release}")
else:
    print("제목에 '습격'이 포함된 영화를 찾을 수 없습니다.")

db.close()
