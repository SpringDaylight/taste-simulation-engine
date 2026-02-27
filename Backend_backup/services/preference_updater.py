"""
User Preference Updater Service
리뷰 기반으로 사용자 취향을 업데이트하는 서비스
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from repositories.user_preference import UserPreferenceRepository
from repositories.movie_vector import MovieVectorRepository
from ml.model_sample.analysis import embedding


class PreferenceUpdater:
    """리뷰 기반 취향 업데이트 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_pref_repo = UserPreferenceRepository(db)
        self.movie_vector_repo = MovieVectorRepository(db)
        
        # Taxonomy 로드
        try:
            self.taxonomy = embedding.load_taxonomy("ml/data/emotion_tag.json")
        except:
            try:
                self.taxonomy = embedding.load_taxonomy("emotion_tag.json")
            except:
                self.taxonomy = None
    
    def update_from_review(
        self,
        user_id: str,
        movie_id: int,
        rating: float,
        review_text: Optional[str] = None,
        learning_rate: float = 0.15
    ) -> Dict[str, Any]:
        """
        리뷰 기반으로 사용자 취향 및 영화 벡터 업데이트
        
        Args:
            user_id: 사용자 ID
            movie_id: 영화 ID
            rating: 평점 (0.5~5.0)
            review_text: 리뷰 텍스트 (선택)
            learning_rate: 학습률 (기본 0.15)
        
        Returns:
            업데이트 결과
        """
        # 1. 기존 사용자 취향 가져오기
        user_pref = self.user_pref_repo.get_by_user_id(user_id)
        if not user_pref:
            return {
                "success": False,
                "message": "User preference not found. Please complete taste survey first."
            }
        
        # 2. 영화 벡터 가져오기
        movie_vector = self.movie_vector_repo.get_by_movie_id(movie_id)
        if not movie_vector:
            return {
                "success": False,
                "message": "Movie vector not found. Cannot update preference."
            }
        
        # 3. 리뷰 텍스트 분석 (있는 경우)
        review_vector = None
        if review_text and self.taxonomy:
            try:
                review_vector = self._analyze_review_text(review_text)
            except Exception as e:
                print(f"Failed to analyze review text: {e}")
        
        # 4. 평점을 가중치로 변환
        rating_weight = self._calculate_rating_weight(rating)
        
        # 5. 사용자 취향 업데이트
        updated_user_pref = self._update_user_preference(
            user_pref=user_pref,
            movie_vector=movie_vector,
            review_vector=review_vector,
            rating=rating,
            rating_weight=rating_weight,
            learning_rate=learning_rate
        )
        
        # 6. 영화 벡터 업데이트 (리뷰 텍스트가 있는 경우)
        movie_updated = False
        if review_vector:
            movie_updated = self._update_movie_vector(
                movie_vector=movie_vector,
                review_vector=review_vector,
                rating=rating,
                learning_rate=0.05  # 영화 벡터는 더 천천히 변화
            )
        
        return {
            "success": True,
            "message": "User preference and movie vector updated based on review",
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": rating,
            "rating_weight": rating_weight,
            "review_analyzed": review_vector is not None,
            "movie_vector_updated": movie_updated,
            "updated_at": updated_user_pref.updated_at.isoformat() if updated_user_pref.updated_at else None
        }
    
    def _analyze_review_text(self, review_text: str) -> Dict[str, Any]:
        """
        리뷰 텍스트를 분석하여 감정/서사 벡터 추출
        """
        if not self.taxonomy:
            return {}
        
        return {
            "emotion_scores": embedding.score_tags(
                review_text,
                self.taxonomy['emotion']['tags']
            ),
            "narrative_traits": embedding.score_tags(
                review_text,
                self.taxonomy['story_flow']['tags']
            ),
            "ending_preference": {
                'happy': embedding.stable_score(review_text, 'ending_happy'),
                'open': embedding.stable_score(review_text, 'ending_open'),
                'bittersweet': embedding.stable_score(review_text, 'ending_bittersweet'),
            }
        }
    
    def _calculate_rating_weight(self, rating: float) -> float:
        """
        평점을 가중치로 변환
        5.0 → 1.0 (강한 선호)
        3.0 → 0.0 (중립)
        0.5 → -1.0 (강한 비선호)
        """
        return (rating - 3.0) / 2.0
    
    def _update_user_preference(
        self,
        user_pref,
        movie_vector,
        review_vector: Optional[Dict],
        rating: float,
        rating_weight: float,
        learning_rate: float
    ):
        """사용자 취향 벡터 업데이트"""
        current_pref = user_pref.preference_vector_json
        
        # preference_vector_json에서 global 프로필 추출
        if 'global' in current_pref:
            # 신 형식: global 키가 있는 경우
            current_global = current_pref['global']
            has_new_format = True
        else:
            # 구 형식: 최상위에 직접 있는 경우
            current_global = current_pref
            has_new_format = False
        
        # 리뷰 텍스트 분석이 있으면 우선 사용, 없으면 영화 벡터 사용
        source_vector = review_vector if review_vector else {
            "emotion_scores": movie_vector.emotion_scores,
            "narrative_traits": movie_vector.narrative_traits,
            "ending_preference": movie_vector.ending_preference
        }
        
        updated_global = {
            "emotion_scores": self._update_vector(
                current_global.get("emotion_scores", {}),
                source_vector.get("emotion_scores", {}),
                rating_weight,
                learning_rate
            ),
            "narrative_traits": self._update_vector(
                current_global.get("narrative_traits", {}),
                source_vector.get("narrative_traits", {}),
                rating_weight,
                learning_rate
            ),
            "direction_mood": self._update_vector(
                current_global.get("direction_mood", {}),
                movie_vector.direction_mood,
                rating_weight,
                learning_rate * 0.7  # 연출/분위기는 덜 반영
            ),
            "character_relationship": self._update_vector(
                current_global.get("character_relationship", {}),
                movie_vector.character_relationship,
                rating_weight,
                learning_rate * 0.7
            ),
            "ending_preference": self._update_vector(
                current_global.get("ending_preference", {}),
                source_vector.get("ending_preference", {}),
                rating_weight,
                learning_rate
            )
        }
        
        # 신 형식인 경우 구조 유지, 구 형식인 경우 그대로 저장
        if has_new_format:
            updated_pref = current_pref.copy()
            updated_pref['global'] = updated_global
        else:
            updated_pref = updated_global
        
        # boost_tags와 dislike_tags 업데이트
        boost_tags = list(user_pref.boost_tags) if user_pref.boost_tags else []
        dislike_tags = list(user_pref.dislike_tags) if user_pref.dislike_tags else []
        
        if rating >= 4.0:
            top_tags = self._get_top_tags(movie_vector, limit=3)
            for tag in top_tags:
                if tag not in boost_tags and tag not in dislike_tags:
                    boost_tags.append(tag)
            boost_tags = boost_tags[-20:]
        elif rating <= 2.0:
            top_tags = self._get_top_tags(movie_vector, limit=2)
            for tag in top_tags:
                if tag not in dislike_tags and tag not in boost_tags:
                    dislike_tags.append(tag)
            dislike_tags = dislike_tags[-15:]
        
        # DB에 저장
        return self.user_pref_repo.upsert(
            user_id=user_pref.user_id,
            preference_vector_json=updated_pref,
            persona_code=user_pref.persona_code,
            boost_tags=boost_tags,
            dislike_tags=dislike_tags,
            penalty_tags=list(user_pref.penalty_tags) if user_pref.penalty_tags else []
        )
    
    def _update_movie_vector(
        self,
        movie_vector,
        review_vector: Dict,
        rating: float,
        learning_rate: float
    ) -> bool:
        """
        영화 벡터 업데이트 (실제 사용자 반응 반영)
        """
        try:
            current_emotion = movie_vector.emotion_scores
            current_narrative = movie_vector.narrative_traits
            current_ending = movie_vector.ending_preference
            
            # 평점에 따라 업데이트 강도 조절
            if rating >= 4.0:
                # 긍정적 리뷰: 리뷰 벡터 방향으로 이동
                weight = 1.0
            elif rating <= 2.0:
                # 부정적 리뷰: 약간만 반영 (영화 자체 특성은 유지)
                weight = 0.3
            else:
                # 중립적 리뷰: 중간 정도 반영
                weight = 0.6
            
            updated_emotion = self._update_vector(
                current_emotion,
                review_vector.get("emotion_scores", {}),
                weight,
                learning_rate
            )
            
            updated_narrative = self._update_vector(
                current_narrative,
                review_vector.get("narrative_traits", {}),
                weight,
                learning_rate
            )
            
            updated_ending = self._update_vector(
                current_ending,
                review_vector.get("ending_preference", {}),
                weight,
                learning_rate
            )
            
            # 업데이트된 벡터 저장
            self.movie_vector_repo.upsert(
                movie_id=movie_vector.movie_id,
                emotion_scores=updated_emotion,
                narrative_traits=updated_narrative,
                direction_mood=movie_vector.direction_mood,
                character_relationship=movie_vector.character_relationship,
                ending_preference=updated_ending,
                embedding_text=movie_vector.embedding_text,
                embedding_vector=movie_vector.embedding_vector
            )
            
            return True
        except Exception as e:
            print(f"Failed to update movie vector: {e}")
            return False
    
    def _update_vector(
        self,
        current: Dict[str, float],
        target: Dict[str, float],
        weight: float,
        learning_rate: float
    ) -> Dict[str, float]:
        """
        벡터 업데이트 (가중 평균)
        new_value = current_value + learning_rate * weight * (target_value - current_value)
        """
        updated = {}
        all_keys = set(current.keys()) | set(target.keys())
        
        for key in all_keys:
            current_val = current.get(key, 0.0)
            target_val = target.get(key, 0.0)
            
            if weight > 0:
                # 긍정적: 타겟 방향으로 이동
                delta = learning_rate * weight * (target_val - current_val)
            else:
                # 부정적: 타겟 반대 방향으로 이동
                delta = learning_rate * weight * target_val
            
            new_val = current_val + delta
            new_val = max(0.0, min(1.0, new_val))
            
            updated[key] = round(new_val, 3)
        
        return updated
    
    def _get_top_tags(self, movie_vector, limit: int = 3) -> list:
        """영화의 주요 태그 추출"""
        all_scores = {}
        
        for category in ['emotion_scores', 'narrative_traits', 'direction_mood', 'character_relationship']:
            scores = getattr(movie_vector, category, {})
            if isinstance(scores, dict):
                all_scores.update(scores)
        
        sorted_tags = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, score in sorted_tags[:limit] if score > 0.3]
