# A-7 영화 취향 지도 (계층적 클러스터링)

import argparse
import json
import math
from typing import List, Dict, Tuple
from collections import defaultdict

import movie_a_2

try:
    import numpy as np
except Exception:
    np = None


# ===== 기본 유틸리티 =====

def to_vector(profile: Dict, e_keys: List[str], n_keys: List[str], d_keys: List[str]) -> List[float]:
    """영화 프로필을 벡터로 변환"""
    return (
        [profile['emotion_scores'].get(k, 0.0) for k in e_keys]
        + [profile['narrative_traits'].get(k, 0.0) for k in n_keys]
        + [profile['ending_preference'].get(k, 0.0) for k in d_keys]
    )


def to_emotion_narrative_vector(profile: Dict, e_keys: List[str], n_keys: List[str]) -> List[float]:
    """감정+서사 벡터만 추출 (장르 무관)"""
    return (
        [profile['emotion_scores'].get(k, 0.0) for k in e_keys]
        + [profile['narrative_traits'].get(k, 0.0) for k in n_keys]
    )


# ===== 차원 축소 =====

def project_2d(X: List[List[float]]):
    """고차원 벡터를 2D로 축소"""
    if np is None:
        raise RuntimeError('numpy is required for projection')

    Xn = np.array(X, dtype=float)
    n_samples = Xn.shape[0]

    # Try UMAP, then random projection
    try:
        if n_samples < 3:
            raise ValueError('UMAP needs at least 3 samples')
        import umap
        n_neighbors = min(15, n_samples - 1)
        reducer = umap.UMAP(n_components=2, n_neighbors=n_neighbors, random_state=42)
        coords = reducer.fit_transform(Xn)
        return coords, reducer
    except Exception:
        pass

    # Fallback: random projection
    rng = np.random.RandomState(42)
    W = rng.normal(size=(Xn.shape[1], 2))
    coords = Xn @ W

    class DummyReducer:
        def transform(self, Xnew):
            return np.array(Xnew) @ W

    return coords, DummyReducer()


# ===== K-Means 클러스터링 =====

def kmeans(X: List[List[float]], k: int = 8, iters: int = 30):
    """K-Means 클러스터링"""
    if np is None:
        raise RuntimeError('numpy is required for clustering')

    Xn = np.array(X, dtype=float)
    rng = np.random.RandomState(42)
    
    if k <= 0:
        raise ValueError('k must be positive')
    if k > len(Xn):
        raise ValueError(f'k ({k}) must be <= number of samples ({len(Xn)})')
    
    centroids = Xn[rng.choice(len(Xn), k, replace=False)]

    for _ in range(iters):
        dists = ((Xn[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        new_centroids = np.vstack([
            Xn[labels == i].mean(axis=0) if (labels == i).any() else centroids[i]
            for i in range(k)
        ])
        if np.allclose(new_centroids, centroids):
            break
        centroids = new_centroids

    return labels.tolist(), centroids.tolist()


# ===== 계층적 클러스터링 (NEW) =====

def group_by_genre(movies: List[Dict], profiles: List[Dict]) -> Dict[str, List[Tuple[Dict, Dict]]]:
    """
    영화를 장르별로 그룹핑
    
    Returns:
        {
            '코미디': [(movie1, profile1), ...],
            '드라마': [(movie2, profile2), ...],
        }
    """
    genre_groups = defaultdict(list)
    
    for movie, profile in zip(movies, profiles):
        genres = movie.get('genres', [])
        if not genres:
            genres = ['기타']
        
        # 각 장르에 추가 (한 영화가 여러 장르에 속할 수 있음)
        for genre in genres:
            genre_groups[genre].append((movie, profile))
    
    return dict(genre_groups)


def hierarchical_clustering(
    movies: List[Dict],
    profiles: List[Dict],
    taxonomy: Dict,
    min_cluster_size: int = 3
) -> Dict:
    """
    계층적 클러스터링
    
    1차: 장르별 분류
    2차: 각 장르 내에서 감정/서사 클러스터링
    
    Returns:
        {
            '코미디': {
                'subclusters': {
                    '슬프고 여운있는': {
                        'movies': [...],
                        'coords': [...],
                        'center': [x, y]
                    },
                    ...
                },
                'all_coords': [...],
                'count': 10
            },
            ...
        }
    """
    if np is None:
        raise RuntimeError('numpy is required for hierarchical clustering')
    
    e_keys = taxonomy['emotion']['tags']
    n_keys = taxonomy['story_flow']['tags']
    
    # 1. 장르별 그룹핑
    genre_groups = group_by_genre(movies, profiles)
    
    hierarchical_result = {}
    
    for genre, items in genre_groups.items():
        if len(items) < min_cluster_size:
            # 영화가 너무 적으면 하나의 서브클러스터로
            emotion_narrative_vecs = [
                to_emotion_narrative_vector(profile, e_keys, n_keys)
                for movie, profile in items
            ]
            coords_2d, _ = project_2d(emotion_narrative_vecs)
            
            hierarchical_result[genre] = {
                'subclusters': {
                    f'{genre} 전체': {
                        'movies': [m for m, p in items],
                        'profiles': [p for m, p in items],
                        'coords': coords_2d.tolist(),
                        'center': coords_2d.mean(axis=0).tolist() if len(coords_2d) > 0 else [0, 0]
                    }
                },
                'all_coords': coords_2d.tolist(),
                'count': len(items)
            }
            continue
        
        # 2. 감정/서사 벡터 추출 (장르 정보 제외)
        emotion_narrative_vecs = [
            to_emotion_narrative_vector(profile, e_keys, n_keys)
            for movie, profile in items
        ]
        
        # 3. 2D 투영
        coords_2d, _ = project_2d(emotion_narrative_vecs)
        
        # 4. K-Means 서브클러스터링
        k = max(2, min(4, len(items) // 10))  # 장르당 2~4개 서브클러스터
        labels, centroids_2d = kmeans(coords_2d.tolist(), k=k)
        
        # 5. 서브클러스터 생성
        subclusters = {}
        for cluster_id in range(k):
            cluster_movies = [items[i][0] for i, l in enumerate(labels) if l == cluster_id]
            cluster_profiles = [items[i][1] for i, l in enumerate(labels) if l == cluster_id]
            cluster_coords = [coords_2d[i].tolist() for i, l in enumerate(labels) if l == cluster_id]
            
            if not cluster_movies:
                continue
            
            # 라벨 생성
            label = generate_subcluster_label(cluster_profiles, e_keys)
            
            subclusters[label] = {
                'movies': cluster_movies,
                'profiles': cluster_profiles,
                'coords': cluster_coords,
                'center': centroids_2d[cluster_id]
            }
        
        hierarchical_result[genre] = {
            'subclusters': subclusters,
            'all_coords': coords_2d.tolist(),
            'count': len(items)
        }
    
    return hierarchical_result


def generate_subcluster_label(profiles: List[Dict], e_keys: List[str]) -> str:
    """서브클러스터 라벨 생성 (감정 태그 기반)"""
    # 평균 감정 점수 계산
    mean_scores = {k: 0.0 for k in e_keys}
    for profile in profiles:
        for k in e_keys:
            mean_scores[k] += profile.get('emotion_scores', {}).get(k, 0.0)
    
    for k in mean_scores:
        mean_scores[k] /= len(profiles)
    
    # 상위 2개 태그 추출
    sorted_tags = sorted(mean_scores.items(), key=lambda x: x[1], reverse=True)
    top_tags = [sorted_tags[0][0], sorted_tags[1][0]] if len(sorted_tags) >= 2 else [sorted_tags[0][0]]
    
    return f"{top_tags[0]}·{top_tags[1]}" if len(top_tags) >= 2 else top_tags[0]


# ===== 장르 간 추천 알고리즘 (NEW) =====

def extract_user_genres(liked_movie_ids: List[str], all_movies: List[Dict]) -> List[str]:
    """
    사용자가 좋아하는 영화들로부터 선호 장르 추출
    
    Args:
        liked_movie_ids: 좋아하는 영화 ID 리스트
        all_movies: 전체 영화 데이터
    
    Returns:
        선호 장르 리스트 (빈도 순)
    """
    genre_count = defaultdict(int)
    
    # 좋아하는 영화들의 장르 카운트
    for movie in all_movies:
        if str(movie.get('id')) in liked_movie_ids or movie.get('id') in liked_movie_ids:
            for genre in movie.get('genres', []):
                genre_count[genre] += 1
    
    # 빈도 순 정렬
    sorted_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)
    
    return [genre for genre, count in sorted_genres]


def cross_genre_recommendation(
    scored_movies: List[Dict],
    preferred_genres: List[str],
    limit: int = 10
) -> List[Dict]:
    """
    장르 간 추천 알고리즘 (중복 방지)
    
    각 선호 장르에서 최고 점수 영화를 1개씩 추천하되, 중복 방지
    
    Args:
        scored_movies: 만족 확률이 계산된 영화 리스트
            [{'movie': {...}, 'score': 0.8, 'genres': ['액션', '드라마'], 'movie_id': '123'}, ...]
        preferred_genres: 사용자 선호 장르 리스트 (순서대로)
        limit: 최종 추천 영화 개수
    
    Returns:
        추천 영화 리스트 (중복 없음)
    """
    if not preferred_genres:
        # 선호 장르가 없으면 점수순으로 반환
        sorted_movies = sorted(scored_movies, key=lambda x: x['score'], reverse=True)
        return sorted_movies[:limit]
    
    # 장르별로 영화 분류
    genre_to_movies = defaultdict(list)
    for item in scored_movies:
        movie_genres = item.get('genres', [])
        for genre in movie_genres:
            genre_to_movies[genre].append(item)
    
    # 각 장르별로 점수순 정렬
    for genre in genre_to_movies:
        genre_to_movies[genre].sort(key=lambda x: x['score'], reverse=True)
    
    # 추천 영화 선택 (중복 방지)
    recommendations = []
    recommended_ids = set()  # 이미 추천한 영화 ID 추적
    
    # 선호 장르를 순회하면서 각 장르에서 최고 점수 영화 선택
    genre_index = 0
    while len(recommendations) < limit and genre_index < len(preferred_genres) * 10:  # 최대 10회 순회
        genre = preferred_genres[genre_index % len(preferred_genres)]
        
        if genre in genre_to_movies:
            # 해당 장르에서 아직 추천하지 않은 최고 점수 영화 찾기
            for movie in genre_to_movies[genre]:
                movie_id = movie.get('movie_id') or movie.get('movie', {}).get('id')
                
                if movie_id not in recommended_ids:
                    recommendations.append(movie)
                    recommended_ids.add(movie_id)
                    break
        
        genre_index += 1
    
    # 아직 limit에 도달하지 못했다면, 남은 영화 중 점수 높은 순으로 추가
    if len(recommendations) < limit:
        remaining_movies = [
            m for m in scored_movies 
            if (m.get('movie_id') or m.get('movie', {}).get('id')) not in recommended_ids
        ]
        remaining_movies.sort(key=lambda x: x['score'], reverse=True)
        
        for movie in remaining_movies:
            if len(recommendations) >= limit:
                break
            movie_id = movie.get('movie_id') or movie.get('movie', {}).get('id')
            recommendations.append(movie)
            recommended_ids.add(movie_id)
    
    return recommendations[:limit]


# ===== 메인 함수 =====

def main():
    parser = argparse.ArgumentParser(description='A-7 계층적 클러스터링')
    parser.add_argument('--movies', default='movies_small.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-text', default='저는 감동적이고 따뜻한 영화를 좋아해요')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--output', default='hierarchical_clusters.json')
    parser.add_argument('--hierarchical', action='store_true', help='계층적 클러스터링 사용')
    args = parser.parse_args()

    print("\n" + "="*60)
    print("🎬 영화 취향 지도 생성")
    print("="*60)

    # 데이터 로드
    taxonomy = movie_a_2.load_taxonomy(args.taxonomy)
    movies = movie_a_2.load_json(args.movies)[:args.limit]
    print(f"📂 영화 {len(movies)}개 로드")

    e_keys = taxonomy['emotion']['tags']
    n_keys = taxonomy['story_flow']['tags']
    d_keys = ['happy', 'open', 'bittersweet']

    # 프로필 생성
    print("🔨 영화 프로필 생성 중...")
    profiles = [movie_a_2.build_profile(m, taxonomy) for m in movies]

    if args.hierarchical:
        # 계층적 클러스터링
        print("📊 계층적 클러스터링 수행 중...")
        result = hierarchical_clustering(movies, profiles, taxonomy)
        
        print("\n" + "="*60)
        print("📊 클러스터링 결과")
        print("="*60)
        
        for genre, data in result.items():
            print(f"\n🎭 {genre} ({data['count']}개 영화)")
            for label, subcluster in data['subclusters'].items():
                print(f"  ├─ {label}: {len(subcluster['movies'])}개")
        
        # JSON 저장
        output_data = {}
        for genre, data in result.items():
            output_data[genre] = {
                'count': data['count'],
                'subclusters': {
                    label: {
                        'count': len(sc['movies']),
                        'movies': [m['title'] for m in sc['movies']],
                        'center': sc['center']
                    }
                    for label, sc in data['subclusters'].items()
                }
            }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 결과 저장: {args.output}")
        
    else:
        # 기존 방식 (평평한 클러스터링)
        print("📐 벡터화 및 2D 투영 중...")
        X = [to_vector(p, e_keys, n_keys, d_keys) for p in profiles]
        coords, reducer = project_2d(X)
        
        print("🎯 K-Means 클러스터링...")
        k = min(8, len(movies) // 10)
        labels, centroids_2d = kmeans(coords.tolist(), k=k)
        
        # 클러스터 라벨링
        from collections import defaultdict
        cluster_data = defaultdict(list)
        for i, label in enumerate(labels):
            cluster_data[label].append((movies[i], profiles[i]))
        
        cluster_labels = {}
        for cid, items in cluster_data.items():
            cluster_profiles = [p for m, p in items]
            cluster_labels[cid] = generate_subcluster_label(cluster_profiles, e_keys)
        
        # 사용자 위치
        user_profile = {
            'emotion_scores': movie_a_2.score_tags(args.user_text, e_keys),
            'narrative_traits': movie_a_2.score_tags(args.user_text, n_keys),
            'ending_preference': {
                'happy': movie_a_2.stable_score(args.user_text, 'ending_happy'),
                'open': movie_a_2.stable_score(args.user_text, 'ending_open'),
                'bittersweet': movie_a_2.stable_score(args.user_text, 'ending_bittersweet'),
            },
        }
        user_vec = to_vector(user_profile, e_keys, n_keys, d_keys)
        user_xy = reducer.transform([user_vec])[0].tolist()
        
        # 가장 가까운 클러스터
        cent = np.array(centroids_2d, dtype=float)
        uv = np.array(user_xy, dtype=float)
        dists = ((cent - uv) ** 2).sum(axis=1)
        nearest = int(dists.argmin())
        
        output = {
            'clusters': [
                {
                    'cluster_id': i,
                    'label': cluster_labels.get(i, f"Cluster {i}"),
                    'count': labels.count(i)
                } for i in range(k)
            ],
            'user_location': {
                'x': round(user_xy[0], 4),
                'y': round(user_xy[1], 4),
                'nearest_cluster': nearest,
                'cluster_label': cluster_labels.get(nearest, f"Cluster {nearest}")
            }
        }

        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()