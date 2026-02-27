"""
키워드 검색 디버깅
"""
from llm_lab.movie_db_connector import MovieDBConnector

connector = MovieDBConnector()

# 테스트 키워드
keywords = ['트롤', '판타지 생물']

print("=" * 80)
print(f"키워드: {keywords}")
print("=" * 80)

# 키워드 검색
results = connector.search_movies_by_keyword(
    keywords=keywords,
    top_k=20
)

print(f"\n검색 결과: {len(results)}개")
print("=" * 80)

for i, movie in enumerate(results[:10], 1):
    print(f"\n{i}. [{movie['movie_id']}] {movie['title']}")
    print(f"   키워드 점수: {movie['keyword_score']:.3f}")
    print(f"   장르: {', '.join(movie['genres'])}")
    if movie.get('synopsis'):
        print(f"   시놉시스: {movie['synopsis'][:100]}...")

connector.close()
