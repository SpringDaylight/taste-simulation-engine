"""
LLM-based Movie Recommender
LLM은 '선택'만 하고, 영화 풀은 시스템이 통제
"""
from typing import List, Dict, Optional
import json
import re

from llm_lab.client import LLMClient
from llm_lab.movie_retriever import MovieRetriever, format_candidates_for_llm
from llm_lab.prompts import get_prompt


class LLMRecommender:
    """
    LLM 기반 영화 추천기
    
    핵심 원칙:
    1. LLM은 영화를 '생성'하지 않음
    2. 시스템이 제공한 후보 중에서만 선택
    3. 선택 이유를 자연어로 설명
    """
    
    def __init__(self, use_real_db=True):
        self.llm_client = LLMClient()
        self.retriever = MovieRetriever(use_real_db=use_real_db)
    
    def recommend(
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
        영화 추천
        
        Args:
            user_input: 사용자 입력
            top_k: 최종 추천 개수
            candidate_pool_size: 후보 풀 크기
            genres: 장르 필터
            year_from: 개봉년도 시작
            year_to: 개봉년도 끝
            conversation_history: 대화 히스토리
            
        Returns:
            {
                "recommendations": [...],
                "explanation": "...",
                "candidates_count": 20
            }
        """
        # 1단계: 후보 영화 검색 (시스템이 통제)
        candidates = self.retriever.retrieve_by_emotion(
            user_input=user_input,
            top_k=candidate_pool_size,
            genres=genres,
            year_from=year_from,
            year_to=year_to
        )
        
        if not candidates:
            return {
                "recommendations": [],
                "explanation": "조건에 맞는 영화를 찾을 수 없습니다.",
                "candidates_count": 0
            }
        
        # 2단계: LLM에게 후보 제공 및 선택 요청
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
        
        # 대화 히스토리 구성
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})
        
        # LLM 호출
        result = self.llm_client.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # 3단계: LLM 응답 파싱
        selected_ids = self._extract_movie_ids(result["response"], candidates)
        
        # 4단계: 선택된 영화 정보 조회
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
    
    def explain_recommendation(
        self,
        movie_id: int,
        user_context: str
    ) -> str:
        """
        특정 영화 추천 이유 설명
        
        Args:
            movie_id: 영화 ID
            user_context: 사용자 상황/요청
            
        Returns:
            설명 텍스트
        """
        # 영화 정보 조회
        movies = self.retriever.retrieve_by_ids([movie_id])
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
        
        explanation = self.llm_client.generate_simple(
            prompt=prompt,
            system_prompt="당신은 영화 추천 전문가입니다."
        )
        
        return explanation
    
    def _extract_movie_ids(self, llm_response: str, candidates: List[Dict]) -> List[int]:
        """
        LLM 응답에서 영화 ID 추출
        
        Args:
            llm_response: LLM 응답 텍스트
            candidates: 후보 영화 리스트
            
        Returns:
            영화 ID 리스트
        """
        # JSON 형식 추출 시도
        json_match = re.search(r'\{[^}]*"selected_ids"[^}]*\}', llm_response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                selected_ids = data.get("selected_ids", [])
                # 후보 목록에 있는 ID만 허용
                valid_ids = [cand["movie_id"] for cand in candidates]
                return [mid for mid in selected_ids if mid in valid_ids]
            except json.JSONDecodeError:
                pass
        
        # JSON 파싱 실패 시, [ID: 123] 패턴 추출
        id_pattern = r'\[ID:\s*(\d+)\]'
        matches = re.findall(id_pattern, llm_response)
        if matches:
            valid_ids = [cand["movie_id"] for cand in candidates]
            return [int(mid) for mid in matches if int(mid) in valid_ids]
        
        # 추출 실패 시 상위 후보 반환
        return [cand["movie_id"] for cand in candidates[:5]]


class ConversationalRecommender:
    """
    대화형 추천기
    여러 턴의 대화를 통해 점진적으로 취향 파악
    """
    
    def __init__(self, use_real_db=True):
        self.recommender = LLMRecommender(use_real_db=use_real_db)
        self.conversation_history = []
    
    def chat(self, user_message: str) -> Dict:
        """
        대화형 추천
        
        Args:
            user_message: 사용자 메시지
            
        Returns:
            {
                "response": "...",
                "recommendations": [...],
                "should_recommend": True/False
            }
        """
        # 대화 히스토리에 추가
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 추천 시점 판단
        should_recommend = self._should_recommend(user_message)
        
        if should_recommend:
            # 추천 실행
            result = self.recommender.recommend(
                user_input=user_message,
                conversation_history=self.conversation_history[:-1]  # 마지막 메시지 제외
            )
            
            # 응답 저장
            self.conversation_history.append({
                "role": "assistant",
                "content": result["explanation"]
            })
            
            return {
                "response": result["explanation"],
                "recommendations": result["recommendations"],
                "should_recommend": True
            }
        else:
            # 추가 질문
            system_prompt = get_prompt("conversational")
            
            llm_result = self.recommender.llm_client.generate(
                messages=self.conversation_history,
                system_prompt=system_prompt
            )
            
            # 응답 저장
            self.conversation_history.append({
                "role": "assistant",
                "content": llm_result["response"]
            })
            
            return {
                "response": llm_result["response"],
                "recommendations": [],
                "should_recommend": False
            }
    
    def _should_recommend(self, message: str) -> bool:
        """추천을 실행할 시점인지 판단"""
        # 간단한 휴리스틱
        recommend_keywords = ["추천", "영화", "보고 싶", "찾아줘", "알려줘"]
        return any(keyword in message for keyword in recommend_keywords)
    
    def reset(self):
        """대화 히스토리 초기화"""
        self.conversation_history = []
