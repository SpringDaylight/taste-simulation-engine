"""
로컬 벡터 검색 유틸리티 (1000개 영화용)
OpenSearch 대신 numpy 기반 메모리 검색
"""

import pickle
from typing import Dict, List


class LocalVectorDB:
    """
    메모리 기반 벡터 검색 (1000개 영화 정도 충분)
    OpenSearch 없이 numpy로 코사인 유사도 계산
    """
    def __init__(self):
        self.vectors = []
        self.metadata = []
        self.dimension = None
    
    def add(self, vector: List[float], meta: Dict):
        """벡터와 메타데이터 추가"""
        if self.dimension is None:
            self.dimension = len(vector)
        elif len(vector) != self.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {len(vector)}")
        
        self.vectors.append(vector)
        self.metadata.append(meta)
    
    def search(self, query_vector: List[float], k: int = 10, filters: Dict = None) -> List[Dict]:
        """
        코사인 유사도 기반 검색
        
        Args:
            query_vector: 쿼리 벡터
            k: 상위 k개 결과
            filters: 필터 조건 (예: {'genres': ['드라마'], 'year_from': 2000})
        
        Returns:
            [{'score': 0.95, 'metadata': {...}}, ...]
        """
        if not self.vectors:
            return []
        
        import numpy as np
        
        # 벡터를 numpy 배열로 변환
        db_vecs = np.array(self.vectors, dtype=float)
        q_vec = np.array(query_vector, dtype=float)
        
        # 코사인 유사도 계산
        # cosine_sim = dot(A, B) / (norm(A) * norm(B))
        norms = np.linalg.norm(db_vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # 0으로 나누기 방지
        normalized_vecs = db_vecs / norms
        
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            q_norm = 1
        normalized_q = q_vec / q_norm
        
        similarities = normalized_vecs @ normalized_q
        
        # 필터 적용
        if filters:
            mask = np.ones(len(self.metadata), dtype=bool)
            
            for i, meta in enumerate(self.metadata):
                # 장르 필터
                if 'genres' in filters and filters['genres']:
                    movie_genres = meta.get('genres', [])
                    if not any(g in movie_genres for g in filters['genres']):
                        mask[i] = False
                
                # 연도 필터
                year = meta.get('release_year')
                if year is not None:
                    if 'year_from' in filters and filters['year_from']:
                        if year < filters['year_from']:
                            mask[i] = False
                    if 'year_to' in filters and filters['year_to']:
                        if year > filters['year_to']:
                            mask[i] = False
            
            # 마스크 적용
            similarities = np.where(mask, similarities, -np.inf)
        
        # 상위 k개 선택
        top_k_idx = np.argsort(similarities)[::-1][:k]
        
        results = []
        for idx in top_k_idx:
            if similarities[idx] > -np.inf:  # 유효한 결과만
                results.append({
                    'score': float(similarities[idx]),
                    'metadata': self.metadata[idx]
                })
        
        return results
    
    def save(self, filepath: str):
        """벡터 DB를 파일로 저장"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'vectors': self.vectors,
                'metadata': self.metadata,
                'dimension': self.dimension
            }, f)
    
    def load(self, filepath: str):
        """파일에서 벡터 DB 로드"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.vectors = data['vectors']
            self.metadata = data['metadata']
            self.dimension = data['dimension']


def profile_to_vector(profile: Dict, e_keys: List[str], n_keys: List[str]) -> List[float]:
    """
    영화/사용자 프로필을 하나의 벡터로 변환
    
    Args:
        profile: 프로필 딕셔너리
        e_keys: emotion tag 키 리스트
        n_keys: narrative tag 키 리스트
    
    Returns:
        벡터 (리스트)
    """
    vec = []
    
    # Emotion scores
    for k in e_keys:
        vec.append(profile.get('emotion_scores', {}).get(k, 0.0))
    
    # Narrative traits
    for k in n_keys:
        vec.append(profile.get('narrative_traits', {}).get(k, 0.0))
    
    # Ending preference
    vec.append(profile.get('ending_preference', {}).get('happy', 0.0))
    vec.append(profile.get('ending_preference', {}).get('open', 0.0))
    vec.append(profile.get('ending_preference', {}).get('bittersweet', 0.0))
    
    return vec


def build_vector_db(movies: List[Dict], profiles: List[Dict], e_keys: List[str], n_keys: List[str]) -> LocalVectorDB:
    """
    영화 리스트를 로컬 벡터 DB로 변환
    
    Args:
        movies: 영화 데이터 리스트
        profiles: 영화 프로필 리스트 (build_profile 결과)
        e_keys: emotion tag 키 리스트
        n_keys: narrative tag 키 리스트
    
    Returns:
        LocalVectorDB 인스턴스
    """
    db = LocalVectorDB()
    
    for movie, profile in zip(movies, profiles):
        vector = profile_to_vector(profile, e_keys, n_keys)
        
        # 메타데이터 저장
        metadata = {
            'id': movie.get('id'),
            'title': movie.get('title'),
            'genres': movie.get('genres', []),
            'release_year': movie.get('release_year'),
            'runtime': movie.get('runtime'),
            'profile': profile  # 전체 프로필도 저장
        }
        
        db.add(vector, metadata)
    
    return db
