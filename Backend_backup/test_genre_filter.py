"""
장르 필터 테스트
"""
from llm_lab.movie_db_connector import MovieDBConnector

connector = MovieDBConnector()

# 테스트 1: 장르 필터 없이
print("=" * 80)
print("테스트 1: 장르 필터 없이")
print("=" * 80)

results = connector.search_movies_by_keyword(
    keywords=['트롤', '판타지 생물'],
    top_k=20,
    genres=None
)

print(f"결과: {len(results)}개\n")
for i, movie in enumerate(results[:5], 1):
    print(f"{i}. [{movie['movie_id']}] {movie['title']}")
    print(f"   장르: {', '.join(movie['genres'])}")
    print(f"   점수: {movie['keyword_score']:.3f}\n")

# 테스트 2: 장르 필터 적용 (애니메이션, 가족, 모험)
print("=" * 80)
print("테스트 2: 장르 필터 적용 ['애니메이션', '가족', '모험']")
print("=" * 80)

results = connector.search_movies_by_keyword(
    keywords=['트롤', '판타지 생물'],
    top_k=20,
    genres=['애니메이션', '가족', '모험']
)

print(f"결과: {len(results)}개\n")
for i, movie in enumerate(results[:5], 1):
    print(f"{i}. [{movie['movie_id']}] {movie['title']}")
    print(f"   장르: {', '.join(movie['genres'])}")
    print(f"   점수: {movie['keyword_score']:.3f}\n")

connector.close()
