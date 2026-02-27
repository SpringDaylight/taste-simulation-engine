"""
실제 영화 DB 연동 - movie_vectors 테이블 사용
하이브리드 검색: 감성 벡터 + 키워드 검색
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from db import SessionLocal
from repositories.movie_vector import MovieVectorRepository
from models import MovieVector, Movie
import numpy as np


class MovieDBConnector:
    """실제 영화 DB와 연동 (movie_vectors 테이블)"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.repo = MovieVectorRepository(self.db)
    
    def search_movies_by_keyword(
        self,
        keywords: List[str],
        top_k: int = 20,
        genres: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        exclude_movie_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        키워드 기반 영화 검색 (DB에서 직접 검색)
        
        Args:
            keywords: 검색 키워드 리스트
            top_k: 상위 k개 결과
            genres: 장르 필터
            year_from: 개봉년도 시작
            year_to: 개봉년도 끝
            
        Returns:
            영화 후보 리스트
        """
        if not keywords:
            return []
        
        # 1. Movie 테이블에서 검색
        query = self.db.query(Movie)
        
        # 1-1. 이미 본 영화 제외
        if exclude_movie_ids:
            query = query.filter(~Movie.id.in_(exclude_movie_ids))
        
        # 2. 키워드 필터 (title 또는 synopsis에 포함)
        keyword_filters = []
        for keyword in keywords:
            keyword_filters.append(
                or_(
                    Movie.title.ilike(f'%{keyword}%'),
                    Movie.synopsis.ilike(f'%{keyword}%')
                )
            )
        
        # OR 조건으로 결합 (하나라도 매칭되면)
        if keyword_filters:
            query = query.filter(or_(*keyword_filters))
        
        # 3. 연도 필터 적용
        if year_from:
            from sqlalchemy import extract
            query = query.filter(extract('year', Movie.release) >= year_from)
        if year_to:
            from sqlalchemy import extract
            query = query.filter(extract('year', Movie.release) <= year_to)
        
        # 4. 장르 필터 (있으면)
        # Note: 장르는 별도 테이블이므로 join 필요
        
        movies = query.all()
        
        if not movies:
            return []
        
        # 5. 키워드 매칭 점수 계산
        results = []
        for movie in movies:
            # 장르 필터 (있으면)
            if genres:
                movie_genres = [g.genre for g in movie.genres]
                if not any(g in movie_genres for g in genres):
                    continue
            
            # 키워드 매칭 점수
            keyword_score = self._calculate_keyword_score(
                movie_title=movie.title,
                movie_synopsis=movie.synopsis or '',
                keywords=keywords
            )
            
            # movie_vector 정보 가져오기 (있으면)
            movie_vector = self.db.query(MovieVector).filter(
                MovieVector.movie_id == movie.id
            ).first()
            
            results.append({
                "movie_id": movie.id,
                "title": movie.title,
                "genres": [g.genre for g in movie.genres],
                "release_year": movie.release.year if movie.release else None,
                "similarity_score": float(keyword_score),  # 키워드 점수를 유사도로 사용
                "keyword_score": float(keyword_score),
                "detail_url": f"/movies/{movie.id}",
                "poster_url": movie.poster_url,
                "rating": float(movie.avg_rating) if movie.avg_rating else None,
                "synopsis": movie.synopsis,
                "emotion_profile": movie_vector.emotion_scores if movie_vector else {},
                "narrative_profile": movie_vector.narrative_traits if movie_vector else {}
            })
        
        # 6. 키워드 점수 순으로 정렬
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return results[:top_k]
    
    def search_movies_hybrid(
        self,
        user_input: str,
        emotion_scores: Dict[str, float],
        top_k: int = 20,
        genres: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        keyword_weight: float = 0.3,
        emotion_weight: float = 0.7,
        exclude_movie_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        하이브리드 검색: 감성 벡터 + 키워드 매칭
        
        Args:
            user_input: 사용자 입력 원문
            emotion_scores: 감성 점수 딕셔너리
            top_k: 상위 k개 결과
            genres: 장르 필터
            year_from: 개봉년도 시작
            year_to: 개봉년도 끝
            keyword_weight: 키워드 매칭 가중치 (0.0 ~ 1.0)
            emotion_weight: 감성 유사도 가중치 (0.0 ~ 1.0)
            
        Returns:
            영화 후보 리스트
        """
        # 1. 키워드 추출 (간단한 방식)
        keywords = self._extract_keywords(user_input)
        
        # 2. 감성 벡터 검색
        emotion_results = self.search_movies_by_emotion(
            emotion_scores=emotion_scores,
            top_k=top_k * 3,  # 더 많이 가져와서 키워드와 결합
            genres=genres,
            year_from=year_from,
            year_to=year_to,
            exclude_movie_ids=exclude_movie_ids
        )
        
        # 3. 키워드 매칭 점수 계산
        for movie in emotion_results:
            keyword_score = self._calculate_keyword_score(
                movie_title=movie['title'],
                movie_synopsis=movie.get('synopsis', ''),
                keywords=keywords
            )
            
            # 하이브리드 점수 계산
            emotion_sim = movie['similarity_score']
            hybrid_score = (emotion_weight * emotion_sim) + (keyword_weight * keyword_score)
            
            movie['keyword_score'] = keyword_score
            movie['emotion_similarity'] = emotion_sim
            movie['similarity_score'] = hybrid_score  # 최종 점수로 업데이트
        
        # 4. 하이브리드 점수로 재정렬
        emotion_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return emotion_results[:top_k]
    
    def search_movies_by_emotion(
        self,
        emotion_scores: Dict[str, float],
        top_k: int = 20,
        genres: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        exclude_movie_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        감성 점수 기반 영화 검색
        
        Args:
            emotion_scores: 감성 점수 딕셔너리
            top_k: 상위 k개 결과
            genres: 장르 필터
            year_from: 개봉년도 시작
            year_to: 개봉년도 끝
            
        Returns:
            영화 후보 리스트
        """
        # 1. movie_vectors 테이블에서 모든 영화 가져오기
        query = self.db.query(MovieVector).join(Movie, MovieVector.movie_id == Movie.id)
        
        # 1-1. 이미 본 영화 제외
        if exclude_movie_ids:
            query = query.filter(~MovieVector.movie_id.in_(exclude_movie_ids))
        
        # 2. 연도 필터 적용
        if year_from:
            from sqlalchemy import extract
            query = query.filter(extract('year', Movie.release) >= year_from)
        if year_to:
            from sqlalchemy import extract
            query = query.filter(extract('year', Movie.release) <= year_to)
        
        movie_vectors = query.all()
        
        if not movie_vectors:
            return []
        
        # 3. 코사인 유사도 계산
        query_vector = self._emotion_scores_to_vector(emotion_scores)
        similarities = []
        
        for mv in movie_vectors:
            movie_vector = self._emotion_scores_to_vector(mv.emotion_scores)
            similarity = self._cosine_similarity(query_vector, movie_vector)
            
            # 영화 정보 조회
            movie = self.db.query(Movie).filter(Movie.id == mv.movie_id).first()
            if not movie:
                continue
            
            # 장르 필터 (있으면)
            if genres:
                movie_genres = [g.genre for g in movie.genres]
                if not any(g in movie_genres for g in genres):
                    continue
            
            similarities.append({
                "movie_id": mv.movie_id,
                "title": movie.title,
                "genres": [g.genre for g in movie.genres],
                "release_year": movie.release.year if movie.release else None,
                "similarity_score": float(similarity),
                "detail_url": f"/movies/{mv.movie_id}",
                "poster_url": movie.poster_url,
                "rating": float(movie.avg_rating) if movie.avg_rating else None,
                "synopsis": movie.synopsis,
                "emotion_profile": mv.emotion_scores,
                "narrative_profile": mv.narrative_traits
            })
        
        # 4. 유사도 순으로 정렬
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return similarities[:top_k]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        사용자 입력에서 키워드 추출
        
        Args:
            text: 사용자 입력
            
        Returns:
            키워드 리스트
        """
        import re
        
        # 간단한 키워드 추출
        keywords = []
        
        # 불용어 제거 (조사 포함)
        stopwords = {
            '영화', '추천', '해줘', '주세요', '보고', '싶어', '관련', '된', 
            '와', '과', '의', '를', '을', '이', '가', '에', '도', '는', '은',
            '한', '하는', '있는', '없는', '같은', '대한', '위한', '통해',
            '어떤', '무슨', '어느', '몇', '여러', '추천해줘', '관련된',
            '제목', '들어간', '들어가', '포함', '포함된', '나오는', '나온'  # 추가
        }
        
        # 따옴표 제거
        text = text.replace("'", "").replace('"', '').replace(''', '').replace(''', '')
        
        # 공백으로 분리
        words = text.split()
        
        for word in words:
            # 조사 제거 (간단한 방식)
            # "상사와" -> "상사", "영화를" -> "영화"
            cleaned_word = re.sub(r'[와과를을이가에도는은한]$', '', word)
            
            # 2글자 이상, 불용어 아닌 경우
            if len(cleaned_word) >= 2 and cleaned_word not in stopwords:
                keywords.append(cleaned_word.lower())
        
        # 중복 제거
        keywords = list(set(keywords))
        
        return keywords
    
    def _calculate_keyword_score(
        self,
        movie_title: str,
        movie_synopsis: str,
        keywords: List[str]
    ) -> float:
        """
        키워드 매칭 점수 계산
        
        Args:
            movie_title: 영화 제목
            movie_synopsis: 영화 시놉시스
            keywords: 검색 키워드 리스트
            
        Returns:
            키워드 매칭 점수 (0.0 ~ 1.0)
        """
        if not keywords:
            return 0.0
        
        title_lower = movie_title.lower() if movie_title else ""
        synopsis_lower = movie_synopsis.lower() if movie_synopsis else ""
        
        matched_count = 0
        for keyword in keywords:
            # 제목에 있으면 가중치 2배
            if keyword in title_lower:
                matched_count += 2
            # 시놉시스에 있으면 가중치 1배
            elif keyword in synopsis_lower:
                matched_count += 1
        
        # 정규화 (최대 키워드 수 * 2)
        max_score = len(keywords) * 2
        score = min(matched_count / max_score, 1.0) if max_score > 0 else 0.0
        
        return score
    
    def get_movie_by_id(self, movie_id: int) -> Optional[Dict]:
        """영화 ID로 조회"""
        movie_vector = self.repo.get_by_movie_id(movie_id)
        if not movie_vector:
            return None
        
        movie = self.db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return None
        
        return {
            "movie_id": movie.id,
            "title": movie.title,
            "genres": [g.genre for g in movie.genres],
            "release_year": movie.release.year if movie.release else None,
            "detail_url": f"/movies/{movie.id}",
            "poster_url": movie.poster_url,
            "rating": float(movie.avg_rating) if movie.avg_rating else None,
            "synopsis": movie.synopsis,
            "emotion_profile": movie_vector.emotion_scores,
            "narrative_profile": movie_vector.narrative_traits
        }
    
    def _emotion_scores_to_vector(self, emotion_scores: Dict[str, float]) -> np.ndarray:
        """감성 점수를 벡터로 변환"""
        # 감성 태그 순서 (emotion_tag.json의 emotion 카테고리와 동일하게)
        emotion_tags = [
            "감동적이에요",
            "따뜻해요",
            "힐링돼요",
            "슬퍼요",
            "여운이 길어요",
            "희망적이에요",
            "우울해요",
            "긴장돼요",
            "무서워요",
            "소름 돋아요",
            "설레요",
            "로맨틱해요",
            "통쾌해요",
            "웃겨요",
            "밝은 분위기예요",
            "어두운 분위기예요",
            "잔잔해요",
            "감정 기복이 커요",
            "현실적이에요",
            "몽환적이에요"
        ]
        
        vector = []
        for tag in emotion_tags:
            vector.append(emotion_scores.get(tag, 0.0))
        
        return np.array(vector, dtype=float)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """코사인 유사도 계산"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def close(self):
        """DB 연결 종료"""
        self.db.close()
