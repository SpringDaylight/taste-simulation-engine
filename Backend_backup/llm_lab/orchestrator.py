"""
LLM Orchestrator - LLM을 컨트롤러로 사용하는 추천 시스템

아키텍처:
1. Planner LLM: 사용자 요청 분석 → 구조화된 쿼리
2. Multi-source Retrieval: 키워드 검색 + 벡터 검색 + (외부 검색)
3. Candidate Pooling: 후보 합치기 + 필터링
4. Ranker LLM: 재랭킹 + 설명 생성
5. ID Validation: 할루시네이션 방지
"""
from typing import List, Dict, Optional, Set
import json
from llm_lab.client import LLMClient
from llm_lab.movie_db_connector import MovieDBConnector
from llm_lab.debug_utils import (
    print_candidate_retrieval,
    print_weight_decision,
    print_candidate_merge,
    print_debug_separator
)
from domain.a5_emotional_search import emotional_search


class LLMOrchestrator:
    """
    LLM 기반 영화 추천 오케스트레이터
    
    핵심 원칙:
    - LLM은 '결정권'을 가짐
    - '사실/존재성'은 시스템이 강제 검증
    - 후보는 항상 검증된 소스에서만
    """
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.db_connector = MovieDBConnector()
    
    def recommend(
        self,
        user_input: str,
        top_k: int = 5,
        candidate_pool_size: int = 150,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        LLM 오케스트레이션 기반 추천
        
        Args:
            user_input: 사용자 입력
            top_k: 최종 추천 개수
            candidate_pool_size: 후보 풀 크기
            user_id: 사용자 ID (만족도 계산용, 선택사항)
            
        Returns:
            추천 결과 (영화 리스트 + 설명 + 후보군 정보)
        """
        # Step 1: Planner LLM - 요청 분석
        query_plan = self._plan_query(user_input)
        
        # 사용자가 본 영화 ID 가져오기
        exclude_movie_ids = []
        if user_id:
            from repositories.watched import WatchedMovieRepository
            watched_repo = WatchedMovieRepository(self.db_connector.db)
            exclude_movie_ids = watched_repo.get_watched_movie_ids(user_id)
            if exclude_movie_ids:
                print(f"✅ [Orchestrator] 사용자가 본 영화 {len(exclude_movie_ids)}개 제외")
        
        # Step 2: Multi-source Retrieval (가중치 결정 포함)
        candidates, keyword_weight, emotion_weight, keyword_results, vector_results = self._retrieve_candidates_with_weights(
            user_input=user_input,
            query_plan=query_plan,
            pool_size=candidate_pool_size,
            exclude_movie_ids=exclude_movie_ids
        )
        
        if not candidates:
            return {
                "recommendations": [],
                "explanation": "죄송합니다. 조건에 맞는 영화를 찾을 수 없습니다.",
                "candidates_count": 0,
                "keyword_candidates": [],
                "vector_candidates": []
            }
        
        # 소스별 후보 분리 (원본 검색 결과 사용, 상위 10개씩)
        keyword_candidates = keyword_results[:10]
        vector_candidates = vector_results[:10]
        
        # Step 3: Ranker LLM - 재랭킹 + 설명 (가중치 전달)
        ranked_results = self._rank_and_explain(
            user_input=user_input,
            candidates=candidates,
            top_k=top_k,
            keyword_weight=keyword_weight,
            emotion_weight=emotion_weight
        )
        
        # Step 4: ID Validation - 할루시네이션 방지
        validated_results = self._validate_recommendations(
            ranked_results=ranked_results,
            candidate_pool=candidates,
            user_id=user_id
        )
        
        # 선택된 영화 ID 집합
        selected_ids = {m['movie_id'] for m in validated_results['recommendations']}
        
        # 후보군 정보 추가 (선택 여부 포함 + 만족도)
        validated_results['keyword_candidates'] = self._format_candidates_for_display(
            keyword_candidates, selected_ids, user_id
        )
        validated_results['vector_candidates'] = self._format_candidates_for_display(
            vector_candidates, selected_ids, user_id
        )
        validated_results['keyword_weight'] = keyword_weight
        validated_results['emotion_weight'] = emotion_weight
        
        return validated_results
    
    def _retrieve_candidates_with_weights(
        self,
        user_input: str,
        query_plan: Dict,
        pool_size: int,
        exclude_movie_ids: Optional[List[int]] = None
    ) -> tuple[List[Dict], float, float, List[Dict], List[Dict]]:
        """
        후보 수집 + 가중치 반환 + 원본 소스별 결과 반환
        
        Returns:
            (candidates, keyword_weight, emotion_weight, keyword_results, vector_results) 튜플
        """
        # 기존 _retrieve_candidates 로직 + 가중치 + 원본 결과 반환
        candidates, keyword_results, vector_results = self._retrieve_candidates(
            user_input, query_plan, pool_size, exclude_movie_ids
        )
        
        # 가중치 다시 계산 (반환용)
        keyword_weight, emotion_weight = self._determine_weights(
            user_input=user_input,
            query_plan=query_plan
        )
        
        return candidates, keyword_weight, emotion_weight, keyword_results, vector_results
    
    def _plan_query(self, user_input: str) -> Dict:
        """
        Step 1: Planner LLM - 사용자 요청을 구조화된 쿼리로 변환
        
        Args:
            user_input: 사용자 입력
            
        Returns:
            구조화된 쿼리 (키워드, 감성, 필터 등)
        """
        planner_prompt = f"""사용자의 영화 추천 요청을 분석하여 구조화된 검색 쿼리를 생성하세요.

사용자 요청: "{user_input}"

다음 형식의 JSON으로 응답하세요:
{{
    "keywords": ["키워드1", "키워드2"],  // 주제, 소재, 등장인물 등
    "mood": ["분위기1", "분위기2"],      // 우울한, 힐링, 긴장감 등
    "genres": ["장르1", "장르2"],        // 드라마, 로맨스, 액션 등
    "exclude": ["제외할_요소"],          // 너무 잔혹한, 복잡한 등
    "time_context": "시간대",            // 밤, 주말, 비오는날 등
    "attention_level": "집중도"          // high, medium, low
}}

⚠️ 중요:
- genres는 사용자가 명시적으로 언급한 경우에만 포함하세요
- 사용자가 장르를 언급하지 않았다면 genres는 빈 배열로 두세요
- 키워드나 주제로부터 장르를 추측하지 마세요

JSON만 출력하세요:"""

        try:
            response = self.llm_client.generate_simple(planner_prompt)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                query_plan = json.loads(json_str)
                return query_plan
            else:
                # JSON 파싱 실패 시 기본값
                return self._fallback_query_plan(user_input)
                
        except Exception as e:
            print(f"⚠️ Planner LLM 오류: {e}")
            return self._fallback_query_plan(user_input)
    
    def _fallback_query_plan(self, user_input: str) -> Dict:
        """LLM 실패 시 폴백 쿼리 플랜"""
        # 간단한 키워드 추출
        keywords = self.db_connector._extract_keywords(user_input)
        
        return {
            "keywords": keywords,
            "mood": [],
            "genres": [],
            "exclude": [],
            "time_context": "",
            "attention_level": "medium"
        }
    
    def _retrieve_candidates(
        self,
        user_input: str,
        query_plan: Dict,
        pool_size: int,
        exclude_movie_ids: Optional[List[int]] = None
    ) -> tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Step 2: Multi-source Retrieval
        
        소스:
        1. 키워드 검색 (제목, 시놉시스, 등장인물)
        2. 벡터 검색 (감성 유사도)
        3. (선택) 외부 검색
        
        Args:
            user_input: 사용자 입력
            query_plan: 구조화된 쿼리
            pool_size: 후보 풀 크기
            
        Returns:
            (병합된 후보 리스트, 키워드 검색 결과, 벡터 검색 결과) 튜플
        """
        print_debug_separator("🎬 후보군 수집 시작")
        
        all_candidates = {}  # movie_id -> movie_info
        
        # 쿼리 유형 분석 및 가중치 결정
        keyword_weight, emotion_weight = self._determine_weights(
            user_input=user_input,
            query_plan=query_plan
        )
        
        # 가중치 결정 이유 생성
        reason = self._get_weight_reason(keyword_weight, emotion_weight)
        print_weight_decision(keyword_weight, emotion_weight, reason)
        
        # Source 1: 키워드 검색 (DB에서 직접 검색)
        keyword_results = []
        try:
            print(f"\n🔍 키워드 검색 시작 (DB 직접 검색)...")
            
            # LLM이 추출한 키워드 사용 (더 정확함)
            keywords = query_plan.get("keywords", [])
            
            # 폴백: LLM이 키워드를 못 뽑았으면 규칙 기반으로 추출
            if not keywords:
                keywords = self.db_connector._extract_keywords(user_input)
                print(f"   ⚠️ LLM 키워드 없음 - 규칙 기반 추출: {keywords}")
            else:
                print(f"   ✅ LLM 추출 키워드: {keywords}")
            
            if keywords:
                # DB에서 직접 키워드 검색
                keyword_results = self.db_connector.search_movies_by_keyword(
                    keywords=keywords,
                    top_k=pool_size,
                    genres=query_plan.get("genres"),
                    exclude_movie_ids=exclude_movie_ids
                )
                
                # 디버깅: 키워드 검색 결과 출력
                print_candidate_retrieval("keyword", keyword_results, top_n=10, show_details=True)
                
                for movie in keyword_results:
                    movie_id = movie['movie_id']
                    if movie_id not in all_candidates:
                        all_candidates[movie_id] = movie
                        all_candidates[movie_id]['sources'] = []
                    all_candidates[movie_id]['sources'].append('keyword')
            else:
                print("   키워드 없음 - 키워드 검색 스킵")
                
        except Exception as e:
            print(f"⚠️ 키워드 검색 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # Source 2: 벡터 검색 (감성 기반)
        vector_results = []
        try:
            print(f"\n🎭 벡터 검색 시작 (감성 기반)...")
            
            # 감성 분석
            search_result = emotional_search({"text": user_input})
            emotion_scores = search_result["expanded_query"]["emotion_scores"]
            
            vector_results = self.db_connector.search_movies_by_emotion(
                emotion_scores=emotion_scores,
                top_k=pool_size,
                genres=query_plan.get("genres"),
                exclude_movie_ids=exclude_movie_ids
            )
            
            # 디버깅: 벡터 검색 결과 출력
            print_candidate_retrieval("vector", vector_results, top_n=10, show_details=True)
            
            for movie in vector_results:
                movie_id = movie['movie_id']
                if movie_id not in all_candidates:
                    all_candidates[movie_id] = movie
                    all_candidates[movie_id]['sources'] = []
                all_candidates[movie_id]['sources'].append('vector')
                
        except Exception as e:
            print(f"⚠️ 벡터 검색 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 후보 리스트로 변환
        candidates = list(all_candidates.values())
        
        # 다중 소스에서 발견된 영화 개수
        multi_source_count = sum(1 for c in candidates if len(c.get('sources', [])) > 1)
        
        # 디버깅: 병합 정보 출력
        total_count = len(keyword_results) + len(vector_results)
        print_candidate_merge(total_count, len(candidates), multi_source_count)
        
        # 최종 점수 계산 (가중치 반영 + 다중 소스 보너스)
        for candidate in candidates:
            source_count = len(candidate.get('sources', []))
            original_score = candidate.get('similarity_score', 0)
            sources = candidate.get('sources', [])
            
            # 소스별 가중치 적용
            weighted_score = 0.0
            
            if 'keyword' in sources:
                # 키워드 검색 점수에 키워드 가중치 적용
                keyword_score = candidate.get('keyword_score', original_score)
                weighted_score = keyword_score * keyword_weight
            
            if 'vector' in sources:
                # 벡터 검색 점수에 감성 가중치 적용
                emotion_score = candidate.get('similarity_score', original_score)
                if 'keyword' in sources:
                    # 둘 다 있으면 합산
                    weighted_score += emotion_score * emotion_weight
                else:
                    # 벡터만 있으면 그대로
                    weighted_score = emotion_score * emotion_weight
            
            # 다중 소스 보너스: 2개 소스 = +0.05
            multi_source_bonus = (source_count - 1) * 0.05
            
            # 최종 점수 = 가중치 적용 점수 + 다중 소스 보너스
            candidate['final_score'] = weighted_score + multi_source_bonus
            candidate['weighted_score'] = weighted_score
            candidate['multi_source_bonus'] = multi_source_bonus
        
        # 최종 점수로 정렬
        candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        # 최종 후보 풀
        final_candidates = candidates[:pool_size]
        
        print(f"\n✅ 최종 후보 풀: {len(final_candidates)}개")
        print_candidate_retrieval("final", final_candidates, top_n=10, show_details=True)
        
        return final_candidates, keyword_results, vector_results
    
    def _determine_weights(
        self,
        user_input: str,
        query_plan: Dict
    ) -> tuple[float, float]:
        """
        쿼리 유형 분석 및 가중치 결정
        
        Args:
            user_input: 사용자 입력
            query_plan: 구조화된 쿼리
            
        Returns:
            (keyword_weight, emotion_weight) 튜플
        """
        # 1. 키워드 개수 확인
        keywords = query_plan.get("keywords", [])
        keyword_count = len(keywords)
        
        # 2. 감성 단어 개수 확인
        mood_words = query_plan.get("mood", [])
        mood_count = len(mood_words)
        
        # 3. 감성 키워드 리스트 (한국어)
        emotion_keywords = {
            '우울', '슬픈', '슬프', '힐링', '따뜻', '감동', '설레', '로맨틱',
            '무서', '긴장', '스릴', '웃긴', '재미', '유쾌', '밝은', '어두운',
            '잔잔', '몽환', '희망', '통쾌', '소름', '현실', '멜로', '코미디'
        }
        
        # 4. 입력에서 감성 키워드 찾기
        emotion_word_count = sum(
            1 for word in emotion_keywords 
            if word in user_input
        )
        
        # 5. 주제/키워드 단어 리스트 (한국어)
        topic_keywords = {
            '직장', '상사', '학교', '선생', '가족', '부모', '친구', '연인',
            '전쟁', '역사', '정치', '범죄', '의사', '경찰', '군인', '요리',
            '음악', '춤', '스포츠', '게임', '여행', '우주', '좀비', '로봇',
            '마법', '판타지', '시간여행', '평행우주', '복수', '성장', '사랑'
        }
        
        # 6. 입력에서 주제 키워드 찾기
        topic_word_count = sum(
            1 for word in topic_keywords 
            if word in user_input
        )
        
        # 7. 가중치 결정 로직
        
        # 케이스 1: 주제 키워드가 많고 감성 키워드가 적음 → 키워드 중심
        if topic_word_count >= 2 and emotion_word_count == 0:
            return (0.9, 0.1)  # 키워드 90%
        
        if topic_word_count >= 1 and emotion_word_count == 0:
            return (0.8, 0.2)  # 키워드 80%
        
        # 케이스 2: 감성 키워드가 많고 주제 키워드가 적음 → 감성 중심
        if emotion_word_count >= 2 and topic_word_count == 0:
            return (0.2, 0.8)  # 감성 80%
        
        if emotion_word_count >= 1 and topic_word_count == 0:
            return (0.3, 0.7)  # 감성 70%
        
        # 케이스 3: 둘 다 있음 → 균형
        if topic_word_count >= 1 and emotion_word_count >= 1:
            return (0.5, 0.5)  # 균형 50:50
        
        # 케이스 4: 둘 다 없음 (일반적인 쿼리) → 약간 키워드 우선
        return (0.6, 0.4)  # 키워드 60%
    
    def _get_weight_reason(self, keyword_weight: float, emotion_weight: float) -> str:
        """
        가중치 결정 이유 생성
        
        Args:
            keyword_weight: 키워드 가중치
            emotion_weight: 감성 가중치
            
        Returns:
            결정 이유 문자열
        """
        if keyword_weight >= 0.8:
            return "주제 키워드 중심 쿼리 (직장, 상사, 학교 등)"
        elif emotion_weight >= 0.7:
            return "감성 키워드 중심 쿼리 (우울, 힐링, 설레 등)"
        elif abs(keyword_weight - emotion_weight) < 0.1:
            return "주제와 감성이 균형잡힌 쿼리"
        elif keyword_weight > emotion_weight:
            return "약간 주제 중심 쿼리"
        else:
            return "약간 감성 중심 쿼리"
    
    def _rank_and_explain(
        self,
        user_input: str,
        candidates: List[Dict],
        top_k: int,
        keyword_weight: float = 0.5,
        emotion_weight: float = 0.5
    ) -> Dict:
        """
        Step 3: Ranker LLM - 후보 재랭킹 + 설명 생성
        
        Args:
            user_input: 사용자 입력
            candidates: 후보 영화 리스트
            top_k: 최종 추천 개수
            keyword_weight: 키워드 가중치
            emotion_weight: 감성 가중치
            
        Returns:
            랭킹 결과 (영화 ID + 설명)
        """
        # 후보 포맷팅 (LLM이 읽을 수 있게)
        candidates_text = self._format_candidates_for_ranking(candidates)
        
        # 가중치 정보 추가
        weight_info = ""
        if keyword_weight > 0.7:
            weight_info = "\n⚠️ 중요: 이 요청은 키워드/주제 중심입니다. 제목이나 내용에 관련 키워드가 포함된 영화를 우선적으로 선택하세요."
        elif emotion_weight > 0.7:
            weight_info = "\n⚠️ 중요: 이 요청은 감성/분위기 중심입니다. 사용자가 원하는 감정이나 분위기를 제공하는 영화를 우선적으로 선택하세요."
        
        ranker_prompt = f"""당신은 영화 추천 전문가입니다. 사용자의 요청에 가장 적합한 영화를 선택하고 이유를 설명하세요.

사용자 요청: "{user_input}"{weight_info}

후보 영화 목록:
{candidates_text}

⚠️ 중요 규칙:
1. 반드시 위 목록의 영화 ID만 사용하세요
2. 목록에 없는 영화는 절대 추천하지 마세요
3. 상위 {top_k}개를 선택하세요

다음 형식의 JSON으로 응답하세요:
{{
    "selected_movie_ids": [123, 456, 789],
    "explanation": "전체 추천 이유 (2-3문장)",
    "individual_reasons": {{
        "123": "이 영화를 추천하는 이유",
        "456": "이 영화를 추천하는 이유",
        "789": "이 영화를 추천하는 이유"
    }}
}}

JSON만 출력하세요:"""

        try:
            response = self.llm_client.generate_simple(ranker_prompt)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                ranking_result = json.loads(json_str)
                return ranking_result
            else:
                # JSON 파싱 실패 시 폴백
                return self._fallback_ranking(candidates, top_k)
                
        except Exception as e:
            print(f"⚠️ Ranker LLM 오류: {e}")
            return self._fallback_ranking(candidates, top_k)
    
    def _format_candidates_for_ranking(self, candidates: List[Dict]) -> str:
        """후보를 LLM이 읽을 수 있는 형식으로 변환"""
        lines = []
        for i, movie in enumerate(candidates[:50], 1):  # 최대 50개만 (토큰 제한)
            lines.append(f"{i}. [ID: {movie['movie_id']}] {movie['title']}")
            lines.append(f"   장르: {', '.join(movie.get('genres', []))}")
            lines.append(f"   개봉: {movie.get('release_year', 'N/A')}")
            
            # 시놉시스 (있으면)
            if movie.get('synopsis'):
                synopsis = movie['synopsis'][:150]  # 150자로 제한
                lines.append(f"   줄거리: {synopsis}...")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _fallback_ranking(self, candidates: List[Dict], top_k: int) -> Dict:
        """LLM 실패 시 폴백 랭킹 (유사도 기반)"""
        top_candidates = candidates[:top_k]
        
        return {
            "selected_movie_ids": [m['movie_id'] for m in top_candidates],
            "explanation": "추천 영화를 선별했습니다.",
            "individual_reasons": {
                str(m['movie_id']): f"{m['title']}을(를) 추천합니다."
                for m in top_candidates
            }
        }
    
    def _validate_recommendations(
        self,
        ranked_results: Dict,
        candidate_pool: List[Dict],
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Step 4: ID Validation - 할루시네이션 방지 + 만족도 계산
        
        Args:
            ranked_results: LLM 랭킹 결과
            candidate_pool: 원본 후보 풀
            user_id: 사용자 ID (만족도 계산용, 선택사항)
            
        Returns:
            검증된 추천 결과 (만족도 포함)
        """
        # 후보 풀의 ID 집합
        valid_ids = {m['movie_id'] for m in candidate_pool}
        
        # LLM이 선택한 ID
        selected_ids = ranked_results.get('selected_movie_ids', [])
        
        # ID 검증
        validated_ids = [mid for mid in selected_ids if mid in valid_ids]
        
        if len(validated_ids) < len(selected_ids):
            print(f"⚠️ 할루시네이션 감지: {len(selected_ids) - len(validated_ids)}개 영화 제외됨")
        
        # 검증된 영화 정보 조회
        id_to_movie = {m['movie_id']: m for m in candidate_pool}
        
        # 만족도 계산 (로그인한 경우만)
        satisfaction_scores = {}
        if user_id:
            satisfaction_scores = self._calculate_satisfaction_batch(user_id, validated_ids)
        
        recommendations = []
        for movie_id in validated_ids:
            movie = id_to_movie[movie_id]
            reason = ranked_results.get('individual_reasons', {}).get(str(movie_id), "")
            
            recommendations.append({
                "movie_id": movie['movie_id'],
                "title": movie['title'],
                "genres": movie.get('genres', []),
                "release_year": movie.get('release_year'),
                "similarity_score": movie.get('final_score', movie.get('similarity_score', 0)),  # 최종 점수 사용
                "final_score": movie.get('final_score', 0),  # 최종 점수 (가중치 적용 + 보너스)
                "weighted_score": movie.get('weighted_score', 0),  # 가중치 적용 점수
                "keyword_score": movie.get('keyword_score', 0),  # 키워드 점수
                "emotion_score": movie.get('similarity_score', 0) if 'vector' in movie.get('sources', []) else 0,  # 감성 점수
                "sources": movie.get('sources', []),  # 검색 소스
                "detail_url": movie.get('detail_url'),
                "poster_url": movie.get('poster_url'),
                "rating": movie.get('rating'),
                "synopsis": movie.get('synopsis'),  # 시놉시스 추가
                "reason": reason,  # LLM이 생성한 개별 이유
                "satisfaction_probability": satisfaction_scores.get(movie_id)  # 만족도 확률
            })
        
        # 최종 점수로 정렬 (높은 순)
        recommendations.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        return {
            "recommendations": recommendations,
            "explanation": ranked_results.get('explanation', ''),
            "candidates_count": len(candidate_pool),
            "validated": True
        }
    
    def _calculate_satisfaction_batch(self, user_id: int, movie_ids: List[int]) -> Dict[int, float]:
        """
        여러 영화에 대한 만족도를 일괄 계산
        
        Args:
            user_id: 사용자 ID
            movie_ids: 영화 ID 리스트
            
        Returns:
            {movie_id: satisfaction_probability} 딕셔너리
        """
        from db import SessionLocal
        from models import UserPreference, MovieVector
        from ml.model_sample.analysis.cal_sim import calculate_satisfaction_probability_improved
        from utils.cache import cache_get, cache_set
        
        db = SessionLocal()
        satisfaction_scores = {}
        
        try:
            # 사용자 선호도 조회
            user_pref = db.query(UserPreference).filter(
                UserPreference.user_id == user_id
            ).first()
            
            if not user_pref or not user_pref.preference_vector_json:
                print(f"⚠️ [Satisfaction Batch] 사용자 선호도 없음: user_id={user_id}")
                return {}
            
            # preference_vector_json에서 global 프로필 추출
            pref_json = user_pref.preference_vector_json
            if 'global' in pref_json:
                # 신 형식: global 키가 있는 경우
                user_profile = pref_json['global']
            else:
                # 구 형식: 최상위에 직접 있는 경우
                user_profile = pref_json
            
            # 각 영화에 대해 만족도 계산
            for movie_id in movie_ids:
                # 캐시 확인
                cache_key = f"satisfaction:{user_id}:{movie_id}"
                cached_result = cache_get(cache_key)
                
                if cached_result:
                    satisfaction_scores[movie_id] = cached_result.get('satisfaction_probability')
                    continue
                
                # 영화 벡터 조회
                movie_vector = db.query(MovieVector).filter(
                    MovieVector.movie_id == movie_id
                ).first()
                
                if not movie_vector:
                    continue
                
                # 영화 프로필 구성
                movie_profile = {
                    'emotion_scores': movie_vector.emotion_scores,
                    'narrative_traits': movie_vector.narrative_traits,
                    'ending_preference': movie_vector.ending_preference or {}
                }
                
                # 만족도 계산
                result = calculate_satisfaction_probability_improved(
                    user_profile=user_profile,
                    movie_profile=movie_profile,
                    dislikes=user_pref.dislike_tags or [],
                    boost_tags=user_pref.boost_tags or [],
                    use_sigmoid=True,
                    sigmoid_k=6.0,
                    sigmoid_x0=0.5
                )
                
                satisfaction_scores[movie_id] = result['probability']
                
                # 캐시에 저장
                cache_result = {
                    "movie_id": movie_id,
                    "satisfaction_probability": result['probability'],
                    "confidence": result['confidence'],
                    "breakdown": result['breakdown'],
                    "user_id": user_id
                }
                cache_set(cache_key, cache_result, ttl=3600)
            
            print(f"✅ [Satisfaction Batch] {len(satisfaction_scores)}개 영화 만족도 계산 완료")
            
        except Exception as e:
            print(f"⚠️ [Satisfaction Batch] 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
        
        return satisfaction_scores
    
    def _format_candidates_for_display(
        self,
        candidates: List[Dict],
        selected_ids: Set[int],
        user_id: Optional[int] = None
    ) -> List[Dict]:
        """
        후보를 프론트엔드 표시용으로 포맷팅 (만족도 포함)
        
        Args:
            candidates: 후보 리스트
            selected_ids: 최종 선택된 영화 ID 집합
            user_id: 사용자 ID (만족도 계산용, 선택사항)
            
        Returns:
            포맷팅된 후보 리스트 (만족도 포함)
        """
        # 만족도 계산 (로그인한 경우만)
        satisfaction_scores = {}
        if user_id:
            candidate_ids = [m['movie_id'] for m in candidates]
            satisfaction_scores = self._calculate_satisfaction_batch(user_id, candidate_ids)
        
        formatted = []
        for movie in candidates:
            movie_id = movie['movie_id']
            is_selected = movie_id in selected_ids
            final_score = movie.get('final_score', 0)
            
            formatted.append({
                "movie_id": movie_id,
                "title": movie['title'],
                "genres": movie.get('genres', []),
                "release_year": movie.get('release_year'),
                "similarity_score": final_score,  # Pydantic required field
                "final_score": final_score,
                "keyword_score": movie.get('keyword_score', 0),
                "emotion_score": movie.get('similarity_score', 0) if 'vector' in movie.get('sources', []) else 0,
                "sources": movie.get('sources', []),
                "detail_url": movie.get('detail_url'),
                "poster_url": movie.get('poster_url'),
                "rating": movie.get('rating'),
                "is_selected": is_selected,
                "not_selected_reason": self._get_not_selected_reason(movie, is_selected),
                "satisfaction_probability": satisfaction_scores.get(movie_id)  # 만족도 확률
            })
        
        return formatted
    
    def _get_not_selected_reason(self, movie: Dict, is_selected: bool) -> Optional[str]:
        """
        선택되지 않은 이유 생성
        
        Args:
            movie: 영화 정보
            is_selected: 선택 여부
            
        Returns:
            선택되지 않은 이유 (선택된 경우 None)
        """
        if is_selected:
            return None
        
        final_score = movie.get('final_score', 0)
        sources = movie.get('sources', [])
        
        # 점수가 낮은 경우
        if final_score < 0.3:
            return "점수가 낮아 제외되었습니다"
        
        # 단일 소스인 경우
        if len(sources) == 1:
            if 'keyword' in sources:
                return "키워드 매칭만 있고 감성 유사도가 낮아 제외되었습니다"
            elif 'vector' in sources:
                return "감성 유사도만 있고 키워드 매칭이 없어 제외되었습니다"
        
        # 기타
        return "다른 영화들에 비해 종합 점수가 낮아 제외되었습니다"
    
    def close(self):
        """리소스 정리"""
        self.db_connector.close()
