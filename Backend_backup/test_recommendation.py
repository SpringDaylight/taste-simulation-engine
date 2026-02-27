"""
LLM 추천 시스템 테스트 - 실제 DB 연동 확인
"""
from llm_lab.movie_db_connector import MovieDBConnector
from llm_lab.movie_retriever import MovieRetriever
from llm_lab.recommender import LLMRecommender

def test_db_connector():
    """DB 커넥터 직접 테스트"""
    print("\n" + "="*80)
    print("1. MovieDBConnector 테스트")
    print("="*80)
    
    connector = MovieDBConnector()
    
    try:
        # 감성 점수로 검색
        emotion_scores = {
            "우울해요": 0.8,
            "슬퍼요": 0.7,
            "잔잔해요": 0.6,
            "힐링돼요": 0.5
        }
        
        results = connector.search_movies_by_emotion(
            emotion_scores=emotion_scores,
            top_k=5
        )
        
        print(f"\n✅ 검색 결과: {len(results)}개 영화")
        for i, movie in enumerate(results, 1):
            print(f"\n{i}. {movie['title']}")
            print(f"   ID: {movie['movie_id']}")
            print(f"   장르: {', '.join(movie['genres'])}")
            print(f"   유사도: {movie['similarity_score']:.3f}")
            print(f"   링크: {movie['detail_url']}")
        
    finally:
        connector.close()


def test_movie_retriever():
    """MovieRetriever 테스트"""
    print("\n" + "="*80)
    print("2. MovieRetriever 테스트")
    print("="*80)
    
    retriever = MovieRetriever(use_real_db=True)
    
    # 사용자 입력으로 검색
    user_input = "우울하고 슬픈 영화 추천해줘"
    candidates = retriever.retrieve_by_emotion(
        user_input=user_input,
        top_k=5
    )
    
    print(f"\n✅ 사용자 입력: '{user_input}'")
    print(f"✅ 후보 영화: {len(candidates)}개")
    
    for i, movie in enumerate(candidates, 1):
        print(f"\n{i}. {movie['title']}")
        print(f"   ID: {movie['movie_id']}")
        print(f"   장르: {', '.join(movie['genres'])}")
        print(f"   유사도: {movie['similarity_score']:.3f}")


def test_llm_recommender():
    """LLMRecommender 전체 테스트"""
    print("\n" + "="*80)
    print("3. LLMRecommender 전체 테스트 (실제 LLM 호출)")
    print("="*80)
    
    recommender = LLMRecommender(use_real_db=True)
    
    user_input = "힐링되는 따뜻한 영화 추천해줘"
    
    print(f"\n사용자 입력: '{user_input}'")
    print("LLM 추천 중...")
    
    try:
        result = recommender.recommend(
            user_input=user_input,
            top_k=3,
            candidate_pool_size=10
        )
        
        print(f"\n✅ 추천 완료!")
        print(f"\n📝 설명:\n{result['explanation']}")
        print(f"\n🎬 추천 영화 ({len(result['recommendations'])}개):")
        
        for i, movie in enumerate(result['recommendations'], 1):
            print(f"\n{i}. {movie['title']}")
            print(f"   ID: {movie['movie_id']}")
            print(f"   장르: {', '.join(movie['genres'])}")
            print(f"   유사도: {movie['similarity_score']:.3f}")
            print(f"   링크: {movie['detail_url']}")
        
        print(f"\n📊 후보 풀 크기: {result['candidates_count']}개")
        
    except Exception as e:
        print(f"\n❌ LLM 추천 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 1. DB 커넥터 테스트
    test_db_connector()
    
    # 2. MovieRetriever 테스트
    test_movie_retriever()
    
    # 3. LLM 추천 전체 테스트 (선택사항 - LLM 호출 비용 발생)
    print("\n" + "="*80)
    print("LLM 추천 테스트를 실행하시겠습니까? (y/n)")
    print("(AWS Bedrock 비용이 발생합니다)")
    print("="*80)
    
    choice = input("선택: ").strip().lower()
    if choice == 'y':
        test_llm_recommender()
    else:
        print("\n⏭️ LLM 추천 테스트 건너뜀")
    
    print("\n✅ 모든 테스트 완료!")
