"""
Async wrapper for LLMRecommender to enable non-blocking recommendation operations
"""
import asyncio
from typing import List, Dict, Optional

from llm_lab.recommender import LLMRecommender
from llm_lab.async_client import AsyncLLMClient
from llm_lab.movie_retriever import format_candidates_for_llm


class AsyncLLMRecommender:
    """Async wrapper for LLMRecommender"""
    
    def __init__(self, use_real_db=True):
        self._sync_recommender = LLMRecommender(use_real_db)
        self._async_llm_client = AsyncLLMClient()
    
    async def recommend(
        self,
        user_input: str,
        top_k: int = 5,
        candidate_pool_size: int = 20,
        genres: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Async movie recommendation
        
        Wraps retrieval and LLM operations in thread pool to avoid blocking the event loop.
        
        Args:
            user_input: User input text
            top_k: Number of final recommendations
            candidate_pool_size: Size of candidate pool
            genres: Genre filters
            year_from: Release year start
            year_to: Release year end
            conversation_history: Conversation history
            
        Returns:
            Dict with 'recommendations', 'explanation', 'candidates_count', and 'usage' keys
        """
        # 1. Wrap retrieval (includes DB queries) in thread pool
        candidates = await asyncio.to_thread(
            self._sync_recommender.retriever.retrieve_by_emotion,
            user_input,
            candidate_pool_size,
            genres,
            year_from,
            year_to
        )
        
        if not candidates:
            return {
                "recommendations": [],
                "explanation": "조건에 맞는 영화를 찾을 수 없습니다.",
                "candidates_count": 0
            }
        
        # 2. Format candidates and build prompt
        candidates_text = format_candidates_for_llm(candidates)
        
        system_prompt = f"""당신은 영화 추천 전문가입니다.

{candidates_text}

사용자의 요청을 분석하고, 위 후보 중에서 가장 적합한 영화 {top_k}개를 선택하세요.

응답 형식:
1. 선택한 영화 ID 목록 (JSON 배열)
2. 각 영화를 추천하는 이유
3. 전체적인 추천 설명

예시:
```json
{{"selected_ids": [1, 3, 5]}}
```

**추천 이유:**
1. [ID: 1] 리틀 포레스트 - 잔잔하고 힐링되는 분위기가 현재 기분에 딱 맞습니다.
2. [ID: 3] 인사이드 아웃 - 감정을 다루는 따뜻한 이야기입니다.
...
"""
        
        # 3. Build messages
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})
        
        # 4. Async LLM call
        result = await self._async_llm_client.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # 5. Parse and return results
        selected_ids = self._sync_recommender._extract_movie_ids(
            result["response"],
            candidates
        )
        
        recommendations = []
        for movie_id in selected_ids[:top_k]:
            movie = next((c for c in candidates if c["movie_id"] == movie_id), None)
            if movie:
                recommendations.append(movie)
        
        return {
            "recommendations": recommendations,
            "explanation": result["response"],
            "candidates_count": len(candidates),
            "usage": result["usage"]
        }
    
    async def explain_recommendation(
        self,
        movie_id: int,
        user_context: str
    ) -> str:
        """
        Async wrapper for explaining recommendation
        
        Args:
            movie_id: Movie ID
            user_context: User context/request
            
        Returns:
            Explanation text
        """
        # Retrieve movie info in thread pool
        movies = await asyncio.to_thread(
            self._sync_recommender.retriever.retrieve_by_ids,
            [movie_id]
        )
        
        if not movies:
            return "영화 정보를 찾을 수 없습니다."
        
        movie = movies[0]
        
        prompt = f"""사용자 상황: {user_context}

추천 영화:
- 제목: {movie['title']}
- 장르: {', '.join(movie.get('genres', []))}
- 개봉: {movie.get('release_year', 'N/A')}

이 영화가 사용자의 현재 상황에 왜 적합한지 설명해주세요.
감정적 측면, 서사 구조, 분위기 등을 고려하여 설명하세요."""
        
        explanation = await self._async_llm_client.generate_simple(
            prompt=prompt,
            system_prompt="당신은 영화 추천 전문가입니다."
        )
        
        return explanation
