def build_taste_map(payload: dict) -> dict:
    """
    A-7: 취향 지도 출력 (taste-simulation-engine 형식 맞춤)
    """
    from domain.taxonomy import load_taxonomy
    from domain.a1_preference import _stable_score

    user_text = payload.get("user_text", "")
    k = int(payload.get("k", 8))

    taxonomy = load_taxonomy()
    e_keys = taxonomy.get("emotion", {}).get("tags", [])

    scores = {k: _stable_score(user_text, k) for k in e_keys}
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    clusters = []
    for i in range(min(k, 8)):
        tag_a = top[i % len(top)][0] if top else "Cluster"
        tag_b = top[(i + 1) % len(top)][0] if top else "Cluster"
        clusters.append(
            {"cluster_id": i, "label": f"{tag_a}·{tag_b} 분위기", "count": 10 + i}
        )

    # deterministic 2D location based on text hash
    seed = sum(bytearray(user_text.encode("utf-8"))) or 1
    x = round(((seed % 100) / 100.0), 4)
    y = round((((seed // 3) % 100) / 100.0), 4)
    nearest = 0 if clusters else -1

    return {
        "clusters": clusters,
        "user_location": {
            "x": x,
            "y": y,
            "nearest_cluster": nearest,
            "cluster_label": clusters[0]["label"] if clusters else "",
        },
    }
