"""
Movie Retriever - 영화 후보 생성 (Candidate Generation)
LLM은 이 후보 중에서만 선택할 수 있음 (할루시네이션 방지)
"""
from typing import List, Dict, Optional
from domain.a5_emotional_search import emotional_search
from domain.taxonomy import load_taxonomy


class MovieRetriever:
    """
    영화 후보 생성기
    - LLM이 영화를 '생성'하지 않도록 함
    - 시스템이 통제하는 영화 풀에서만 선택
    """
    
    def __init__(self, use_real_db=True):
        """
        Args:
            use_real_db: 실제 DB 사용 여부 (기본: True)
        """
        self.use_real_db = use_real_db
        self.taxonomy = load_taxonomy()
        self.vector_db = None  # 벡터 DB는 선택사항
        
        # 실제 DB 사용 시 커넥터 초기화
        if use_real_db:
            try:
                from llm_lab.movie_db_connector import MovieDBConnector
                self.db_connector = MovieDBConnector()
                print("✅ 실제 DB 연결 성공 (movie_vectors 테이블)")
            except Exception as e:
                print(f"⚠️ 실제 DB 연결 실패: {e}")
                self.db_connector = None
        else:
            self.db_connector = None
    
    def retrieve_by_emotion(
        self,
        user_input: str,
        top_k: int = 20,
        genres: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[Dict]:
        """
        감성 기반 영화 후보 검색
        
        Args:
            user_input: 사용자 입력 ("우울한 영화 추천해줘")
            top_k: 상위 k개 후보
            genres: 장르 필터
            year_from: 개봉년도 시작
            year_to: 개봉년도 끝
            
        Returns:
            영화 후보 리스트 [{"movie_id": 123, "title": "...", "score": 0.95, ...}]
        """
        # 감성 검색 쿼리 생성
        search_payload = {
            "text": user_input,
            "genres": genres,
            "year_from": year_from,
            "year_to": year_to
        }
        
        search_result = emotional_search(search_payload)
        emotion_scores = search_result["expanded_query"]["emotion_scores"]
        
        # 우선순위 1: 실제 DB 사용 (하이브리드 검색: 감성 + 키워드)
        if self.use_real_db and self.db_connector:
            try:
                candidates = self.db_connector.search_movies_hybrid(
                    user_input=user_input,  # 키워드 추출용
                    emotion_scores=emotion_scores,
                    top_k=top_k,
                    genres=genres,
                    year_from=year_from,
                    year_to=year_to,
                    keyword_weight=0.8,  # 키워드 80% (대폭 증가)
                    emotion_weight=0.2   # 감성 20%
                )
                if candidates:
                    print(f"✅ 실제 DB에서 {len(candidates)}개 영화 검색 완료 (하이브리드)")
                    return candidates
            except Exception as e:
                print(f"⚠️ 실제 DB 검색 실패: {e}")
                # 실패 시 다음 방법으로 fallback
        
        # 우선순위 2: 벡터 DB가 있으면 사용 (선택사항)
        if self.vector_db:
            # 감성 벡터로 변환
            emotion_tags = self.taxonomy.get("emotion", {}).get("tags", [])
            query_vector = [emotion_scores.get(tag, 0.0) for tag in emotion_tags]
            
            # 벡터 검색
            filters = {}
            if genres:
                filters["genres"] = genres
            if year_from:
                filters["year_from"] = year_from
            if year_to:
                filters["year_to"] = year_to
            
            results = self.vector_db.search(
                query_vector=query_vector,
                k=top_k,
                filters=filters
            )
            
            # 결과 포맷팅
            candidates = []
            for result in results:
                meta = result["metadata"]
                movie_id = meta.get("id")
                candidates.append({
                    "movie_id": movie_id,
                    "title": meta.get("title"),
                    "genres": meta.get("genres", []),
                    "release_year": meta.get("release_year"),
                    "similarity_score": result["score"],
                    "emotion_profile": meta.get("profile", {}).get("emotion_scores", {}),
                    "narrative_profile": meta.get("profile", {}).get("narrative_traits", {}),
                    # 프론트엔드 링크 추가
                    "detail_url": f"/movies/{movie_id}",
                    "poster_url": meta.get("poster_url"),  # DB에 있으면 추가
                    "rating": meta.get("rating")  # DB에 있으면 추가
                })
            
            return candidates
        
        # 벡터 DB가 없으면 더미 데이터 (개발용)
        return self._get_dummy_candidates(emotion_scores, top_k)
    
    def retrieve_by_ids(self, movie_ids: List[int]) -> List[Dict]:
        """
        영화 ID로 직접 조회
        
        Args:
            movie_ids: 영화 ID 리스트
            
        Returns:
            영화 정보 리스트
        """
        if self.vector_db:
            # 벡터 DB에서 ID로 검색
            results = []
            for meta in self.vector_db.metadata:
                if meta.get("id") in movie_ids:
                    results.append({
                        "movie_id": meta.get("id"),
                        "title": meta.get("title"),
                        "genres": meta.get("genres", []),
                        "release_year": meta.get("release_year"),
                        "emotion_profile": meta.get("profile", {}).get("emotion_scores", {}),
                        "narrative_profile": meta.get("profile", {}).get("narrative_traits", {})
                    })
            return results
        
        # 더미 데이터
        return [{"movie_id": mid, "title": f"Movie {mid}"} for mid in movie_ids]
    
    def _get_dummy_candidates(self, emotion_scores: Dict, top_k: int) -> List[Dict]:
        """개발용 더미 후보 생성"""
        # 실제로는 DB에서 가져와야 함
        dummy_movies = [
            {
                "movie_id": 1, 
                "title": "리틀 포레스트", 
                "genres": ["드라마"], 
                "release_year": 2018,
                "detail_url": "/movies/1",
                "similarity_score": 0.92
            },
            {
                "movie_id": 2, 
                "title": "어바웃 타임", 
                "genres": ["로맨스", "드라마"], 
                "release_year": 2013,
                "detail_url": "/movies/2",
                "similarity_score": 0.88
            },
            {
                "movie_id": 3, 
                "title": "인사이드 아웃", 
                "genres": ["애니메이션"], 
                "release_year": 2015,
                "detail_url": "/movies/3",
                "similarity_score": 0.85
            },
            {
                "movie_id": 4, 
                "title": "라라랜드", 
                "genres": ["뮤지컬", "로맨스"], 
                "release_year": 2016,
                "detail_url": "/movies/4",
                "similarity_score": 0.82
            },
            {
                "movie_id": 5, 
                "title": "기생충", 
                "genres": ["드라마", "스릴러"], 
                "release_year": 2019,
                "detail_url": "/movies/5",
                "similarity_score": 0.80
            },
        ]
        
        return dummy_movies[:top_k]


def format_candidates_for_llm(candidates: List[Dict]) -> str:
    """
    영화 후보를 LLM이 읽을 수 있는 형식으로 변환
    
    Args:
        candidates: 영화 후보 리스트
        
    Returns:
        포맷팅된 문자열
    """
    lines = []
    lines.append("다음은 시스템이 선별한 영화 후보 목록입니다:")
    lines.append("")
    
    for i, movie in enumerate(candidates, 1):
        lines.append(f"{i}. [ID: {movie['movie_id']}] {movie['title']}")
        lines.append(f"   - 장르: {', '.join(movie.get('genres', []))}")
        lines.append(f"   - 개봉: {movie.get('release_year', 'N/A')}")
        
        # 감성 프로필이 있으면 추가
        if "emotion_profile" in movie:
            top_emotions = sorted(
                movie["emotion_profile"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            emotions_str = ", ".join([f"{k}({v:.2f})" for k, v in top_emotions if v > 0])
            if emotions_str:
                lines.append(f"   - 감성: {emotions_str}")
        
        lines.append("")
    
    lines.append("⚠️ 중요: 반드시 위 목록의 영화 ID만 사용하세요. 다른 영화를 추천하지 마세요.")
    
    return "\n".join(lines)
