# A-7 영화 취향 지도

import argparse
import json
import math
from typing import List, Dict, Tuple

import moviea2

try:
    import numpy as np
except Exception:
    np = None



# 영화 프로필을 하나의 벡터(숫자 리스트)로 변환
def to_vector(profile: Dict, e_keys: List[str], n_keys: List[str], d_keys: List[str]) -> List[float]:
    return (
        [profile['emotion_scores'].get(k, 0.0) for k in e_keys]
        + [profile['narrative_traits'].get(k, 0.0) for k in n_keys]
        + [profile['ending_preference'].get(k, 0.0) for k in d_keys]
    )



# 고차원 벡터를 2D 좌표로 축소 (차원 축소)
def project_2d(X: List[List[float]]):
    if np is None:
        raise RuntimeError('numpy is required for projection')

    Xn = np.array(X, dtype=float)
    # UMAP (최우선) - 비선형 차원 축소, 가장 정확
    # PCA (대안) - 선형 차원 축소
    # Random Projection (최후) - 랜덤 투영
    try:
        import umap
        reducer = umap.UMAP(n_components=2, random_state=42)
        coords = reducer.fit_transform(Xn)
        return coords, reducer
    except Exception:
        pass

    try:
        from sklearn.decomposition import PCA
        reducer = PCA(n_components=2, random_state=42)
        coords = reducer.fit_transform(Xn)
        return coords, reducer
    except Exception:
        pass

    rng = np.random.RandomState(42)
    W = rng.normal(size=(Xn.shape[1], 2))
    coords = Xn @ W

    class DummyReducer:
        def transform(self, Xnew):
            return np.array(Xnew) @ W

    return coords, DummyReducer()



# K-Means 클러스터링
def kmeans(X: List[List[float]], k: int = 8, iters: int = 30):
    if np is None:
        raise RuntimeError('numpy is required for clustering')

    Xn = np.array(X, dtype=float)
    rng = np.random.RandomState(42)
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



# 클러스터에 이름 붙이기
# 클러스터 중심점에서 가장 높은 점수를 가진 감정 태그 2개 추출
def label_cluster(centroid_vec: List[float], e_keys: List[str]):
    # Use top emotion tags as cluster label (dummy LLM)
    e_len = len(e_keys)
    e_scores = centroid_vec[:e_len]
    pairs = list(zip(e_keys, e_scores))
    pairs.sort(key=lambda x: x[1], reverse=True)
    top = [p[0] for p in pairs[:2]]
    return f"{top[0]}·{top[1]} 분위기"



# 1. 영화 데이터 로드 및 벡터화
# 2. 2D 좌표로 투영
# 3. K-Means 클러스터링 (k=8개 그룹)
# 4. 각 클러스터에 라벨 부여
# 5. 사용자 취향 벡터도 생성하여 같은 2D 공간에 배치
# 6. 사용자와 가장 가까운 클러스터 찾기
def main():
    parser = argparse.ArgumentParser(description='A-7 Dynamic Clustering Map (UMAP/PCA fallback)')
    parser.add_argument('--movies', default='movies_dataset_final.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--user-text', required=True)
    parser.add_argument('--k', type=int, default=8)
    parser.add_argument('--limit', type=int, default=200)
    args = parser.parse_args()

    taxonomy = moviea2.load_taxonomy(args.taxonomy)
    movies = moviea2.load_json(args.movies)[: args.limit]

    e_keys = taxonomy['emotion']['tags']
    n_keys = taxonomy['story_flow']['tags']
    d_keys = ['happy', 'open', 'bittersweet']

    profiles = [moviea2.build_profile(m, taxonomy) for m in movies]
    X = [to_vector(p, e_keys, n_keys, d_keys) for p in profiles]

    coords, reducer = project_2d(X)

    labels, centroids = kmeans(X, k=args.k)
    cluster_labels = {
        i: label_cluster(centroids[i], e_keys) for i in range(args.k)
    }

    user_profile = {
        'emotion_scores': moviea2.score_tags(args.user_text, e_keys),
        'narrative_traits': moviea2.score_tags(args.user_text, n_keys),
        'ending_preference': {
            'happy': moviea2.stable_score(args.user_text, 'ending_happy'),
            'open': moviea2.stable_score(args.user_text, 'ending_open'),
            'bittersweet': moviea2.stable_score(args.user_text, 'ending_bittersweet'),
        },
    }
    user_vec = to_vector(user_profile, e_keys, n_keys, d_keys)
    user_xy = reducer.transform([user_vec])[0].tolist()

    # Find nearest cluster
    if np is None:
        raise RuntimeError('numpy is required for nearest cluster calculation')
    cent = np.array(centroids)
    uv = np.array(user_vec)
    dists = ((cent - uv) ** 2).sum(axis=1)
    nearest = int(dists.argmin())

    output = {
        'clusters': [
            {
                'cluster_id': i,
                'label': cluster_labels[i],
                'count': labels.count(i)
            } for i in range(args.k)
        ],
        'user_location': {
            'x': round(user_xy[0], 4),
            'y': round(user_xy[1], 4),
            'nearest_cluster': nearest,
            'cluster_label': cluster_labels[nearest]
        },
        'note': 'UMAP이 없으면 PCA/랜덤 투영으로 대체합니다.'
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
