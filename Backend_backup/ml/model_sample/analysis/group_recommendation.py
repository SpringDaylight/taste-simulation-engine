import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import embedding
from . import preference as pref_mod
from . import sentiment as sent_mod
from .similarity import calculate_satisfaction_probability
from .vector_db import LocalVectorDB, build_vector_db, profile_to_vector


def parse_users(users_text: Optional[str], users_json: Optional[str]) -> List[Dict[str, Any]]:
    """
    Parse group users from plain text or JSON string/file.

    users_json example:
    [
      {"user_id":"u1","name":"A","text":"감동적인 영화 좋아해", "likes":[], "dislikes":[]},
      {"user_id":"u2","name":"B","text":"반전 있는 영화 좋아해", "likes":[], "dislikes":[]}
    ]
    """
    users: List[Dict[str, Any]] = []

    if users_json:
        if os.path.exists(users_json):
            raw_users = embedding.load_json(users_json)
        else:
            raw_users = json.loads(users_json)

        if not isinstance(raw_users, list):
            raise ValueError("--users-json 값은 사용자 객체 리스트여야 합니다.")

        for idx, item in enumerate(raw_users):
            if not isinstance(item, dict):
                raise ValueError("--users-json의 각 항목은 객체여야 합니다.")

            name = str(item.get("name") or f"U{idx + 1}")
            user_id = str(item.get("user_id") or name)

            users.append(
                {
                    "user_id": user_id,
                    "name": name,
                    "text": str(item.get("text", "")),
                    "likes": [str(x).strip() for x in item.get("likes", []) if str(x).strip()],
                    "dislikes": [str(x).strip() for x in item.get("dislikes", []) if str(x).strip()],
                    "profile": item.get("profile"),
                }
            )

    elif users_text:
        chunks = [x.strip() for x in users_text.split(";") if x.strip()]
        for idx, chunk in enumerate(chunks):
            if ":" in chunk:
                name, text = chunk.split(":", 1)
                name = name.strip() or f"U{idx + 1}"
                users.append(
                    {
                        "user_id": name,
                        "name": name,
                        "text": text.strip(),
                        "likes": [],
                        "dislikes": [],
                        "profile": None,
                    }
                )
            else:
                name = f"U{idx + 1}"
                users.append(
                    {
                        "user_id": name,
                        "name": name,
                        "text": chunk,
                        "likes": [],
                        "dislikes": [],
                        "profile": None,
                    }
                )

    if not users:
        raise ValueError("사용자 입력이 없습니다. --users 또는 --users-json을 전달하세요.")
    return users


def parse_users_from_profiles(user_profiles_file: str) -> List[Dict[str, Any]]:
    """
    Build users from an existing user profile file.
    """
    raw = embedding.load_json(user_profiles_file)
    users: List[Dict[str, Any]] = []

    if isinstance(raw, list):
        iterable = raw
    elif isinstance(raw, dict):
        iterable = []
        for key, value in raw.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("user_id", key)
                iterable.append(item)
    else:
        raise ValueError("--user-profiles 는 사용자 프로필 객체 리스트/맵 JSON이어야 합니다.")

    for idx, item in enumerate(iterable):
        if not isinstance(item, dict):
            continue
        user_id = str(item.get("user_id") or item.get("name") or f"U{idx + 1}")
        name = str(item.get("name") or user_id)
        profile = item.get("profile") if isinstance(item.get("profile"), dict) else item
        users.append(
            {
                "user_id": user_id,
                "name": name,
                "text": str(item.get("text", "")),
                "likes": [str(x).strip() for x in item.get("likes", []) if str(x).strip()],
                "dislikes": [str(x).strip() for x in item.get("dislikes", []) if str(x).strip()],
                "profile": profile,
            }
        )

    if not users:
        raise ValueError("--user-profiles 에서 사용자 프로필을 찾지 못했습니다.")
    return users


def merge_a1_preference(users: List[Dict[str, Any]], user_pref_file: Optional[str]) -> None:
    """
    Merge saved A-1 preference boost/penalty tags into each user.
    """
    if not user_pref_file:
        return

    for u in users:
        a1 = pref_mod.load_user_preference(u["user_id"], input_file=user_pref_file)
        boost = a1.get("boost_tags", []) or []
        penalty = a1.get("penalty_tags", []) or []

        u["likes"] = list(dict.fromkeys((u.get("likes", []) or []) + boost))
        u["dislikes"] = list(dict.fromkeys((u.get("dislikes", []) or []) + penalty))


def apply_tag_nudges_to_group_profile(
    group_profile: Dict[str, Any],
    e_keys: List[str],
    n_keys: List[str],
    boost_tags: List[str],
    penalty_tags: List[str],
    boost_nudge: float = 0.08,
    penalty_nudge: float = 0.08,
) -> Dict[str, Any]:
    """
    Apply light boost/penalty nudges to group profile for candidate pre-filtering.
    """
    e = dict(group_profile.get("emotion_scores", {}))
    n = dict(group_profile.get("narrative_traits", {}))
    ending = dict(group_profile.get("ending_preference", {}))

    boost_set = set(boost_tags or [])
    penalty_set = set(penalty_tags or [])

    for k in e_keys:
        val = float(e.get(k, 0.0))
        if k in boost_set:
            val += boost_nudge
        if k in penalty_set:
            val -= penalty_nudge
        e[k] = max(0.0, min(1.0, val))

    for k in n_keys:
        val = float(n.get(k, 0.0))
        if k in boost_set:
            val += boost_nudge
        if k in penalty_set:
            val -= penalty_nudge
        n[k] = max(0.0, min(1.0, val))

    return {"emotion_scores": e, "narrative_traits": n, "ending_preference": ending}


def normalize_profile(profile: Dict[str, Any], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize profile schema to the vector scoring format.
    """
    e_keys = taxonomy.get("emotion", {}).get("tags", [])
    n_keys = taxonomy.get("story_flow", {}).get("tags", [])
    ending_keys = ("happy", "open", "bittersweet")

    emotion_scores = {k: float((profile.get("emotion_scores", {}) or {}).get(k, 0.0)) for k in e_keys}
    narrative_traits = {k: float((profile.get("narrative_traits", {}) or {}).get(k, 0.0)) for k in n_keys}
    ending_preference = {k: float((profile.get("ending_preference", {}) or {}).get(k, 0.0)) for k in ending_keys}

    # Debug: Check if profile has the expected keys (only warn once per issue)
    profile_emotion_keys = set((profile.get("emotion_scores", {}) or {}).keys())
    profile_narrative_keys = set((profile.get("narrative_traits", {}) or {}).keys())
    taxonomy_emotion_keys = set(e_keys)
    taxonomy_narrative_keys = set(n_keys)
    
    # Check for non-zero values
    emotion_nonzero = sum(1 for v in emotion_scores.values() if v != 0)
    narrative_nonzero = sum(1 for v in narrative_traits.values() if v != 0)
    
    # Only warn if there's a key mismatch (not just zero values)
    if emotion_nonzero == 0 or narrative_nonzero == 0:
        matching_emotion = len(taxonomy_emotion_keys & profile_emotion_keys)
        if matching_emotion < len(taxonomy_emotion_keys) * 0.5:  # Less than 50% match
            print(f"[WARN] normalize_profile: Key mismatch detected")
            print(f"  Taxonomy keys: {len(taxonomy_emotion_keys)} emotion, {len(taxonomy_narrative_keys)} narrative")
            print(f"  Profile keys: {len(profile_emotion_keys)} emotion, {len(profile_narrative_keys)} narrative")
            print(f"  Matching: {matching_emotion} emotion keys")
            print(f"  Sample taxonomy: {list(taxonomy_emotion_keys)[:3]}")
            print(f"  Sample profile: {list(profile_emotion_keys)[:3]}")

    return {
        "emotion_scores": emotion_scores,
        "narrative_traits": narrative_traits,
        "ending_preference": ending_preference,
    }


def build_user_profile(user: Dict[str, Any], taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build per-user profile.
    Priority:
    1) user["profile"] if provided
    2) derive from user["text"] via sentiment module
    """
    raw_profile = user.get("profile")
    if isinstance(raw_profile, dict):
        return normalize_profile(raw_profile, taxonomy)

    derived = sent_mod.build_user_profile(user.get("text", ""), taxonomy)
    return normalize_profile(derived, taxonomy)


def _top_matching_tags(
    user_scores: Dict[str, Any],
    movie_scores: Dict[str, Any],
    top_n: int = 3,
    label_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, float]]:
    """
    Extract top tag-level matches using user*movie score product.
    """
    rows: List[Dict[str, float]] = []
    keys = set(user_scores.keys()) | set(movie_scores.keys())

    for key in keys:
        u = float(user_scores.get(key, 0.0))
        m = float(movie_scores.get(key, 0.0))
        match = u * m
        if match <= 0:
            continue
        tag = label_map.get(key, key) if label_map else key
        rows.append(
            {
                "tag": tag,
                "match_score": round(match, 3),
                "user_score": round(u, 3),
                "movie_score": round(m, 3),
            }
        )

    rows.sort(key=lambda x: x["match_score"], reverse=True)
    return rows[:top_n]


def extract_factor_tag_details(
    user_profile: Dict[str, Any],
    movie_profile: Dict[str, Any],
    top_factors: List[str],
    top_n: int = 3,
) -> Dict[str, List[Dict[str, float]]]:
    """
    From top_factors, derive per-factor top tags.
    """
    factor_set = set(top_factors or [])
    ending_label_map = {"happy": "해피엔딩", "open": "열린결말", "bittersweet": "비터스윗"}

    details = {"emotion_tags": [], "narrative_tags": [], "ending_tags": []}

    if "정서 톤" in factor_set:
        details["emotion_tags"] = _top_matching_tags(
            user_profile.get("emotion_scores", {}) or {},
            movie_profile.get("emotion_scores", {}) or {},
            top_n=top_n,
        )
    if "서사 초점" in factor_set:
        details["narrative_tags"] = _top_matching_tags(
            user_profile.get("narrative_traits", {}) or {},
            movie_profile.get("narrative_traits", {}) or {},
            top_n=top_n,
        )
    if "결말 취향" in factor_set:
        details["ending_tags"] = _top_matching_tags(
            user_profile.get("ending_preference", {}) or {},
            movie_profile.get("ending_preference", {}) or {},
            top_n=top_n,
            label_map=ending_label_map,
        )

    return details


def summarize_tag_details(
    tag_rows: List[Dict[str, float]],
    include_scores: bool = True,
    top_only: bool = False,
) -> str:
    if not tag_rows:
        return "없음"
    rows = tag_rows[:1] if top_only else tag_rows
    if include_scores:
        return ", ".join(f"{x['tag']}({x['match_score']:.3f})" for x in rows)
    return ", ".join(f"{x['tag']}" for x in rows)


def build_movie_explanation_with_llm(
    user: Dict[str, Any],
    movie_meta: Dict[str, Any],
    probability: float,
    breakdown: Dict[str, Any],
    factor_tag_details: Dict[str, List[Dict[str, float]]],
    bedrock_client,
) -> str:
    """
    Generate short satisfaction/dissatisfaction explanation via Bedrock.
    """
    if bedrock_client is None:
        return build_user_explanation(breakdown, factor_tag_details=factor_tag_details)

    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    top_factors = ", ".join(breakdown.get("top_factors", []) or [])
    user_name = str(user.get("name", user.get("user_id", "User")))
    emotion_tags = summarize_tag_details(
        (factor_tag_details or {}).get("emotion_tags", []),
        include_scores=False,
        top_only=True,
    )
    narrative_tags = summarize_tag_details(
        (factor_tag_details or {}).get("narrative_tags", []),
        include_scores=False,
        top_only=True,
    )
    ending_tags = summarize_tag_details(
        (factor_tag_details or {}).get("ending_tags", []),
        include_scores=False,
        top_only=True,
    )
    prompt = (
        "당신은 영화 추천 설명 생성기입니다.\n"
        "아래 정보를 바탕으로 매우 간단한 한 줄 설명을 생성하세요.\n"
        "출력은 반드시 한 문장이고 형식은 정확히 '이름: 설명' 이어야 합니다.\n"
        "숫자, 퍼센트, 영어 technical 용어를 쓰지 마세요.\n"
        "만족 이유 중심으로 쓰되, 불만족 요소가 있으면 짧게 한 번만 덧붙이세요.\n\n"
        "[사실성/환각 방지 규칙]\n"
        "1) 아래 입력에 없는 영화 줄거리, 장면, 인물, 사건을 절대 만들어내지 마세요.\n"
        "2) 영화 고유 정보는 제공된 제목/장르/태그 범위 안에서만 언급하세요.\n"
        "3) 설명 근거는 핵심 요인과 태그 매칭만 사용하세요.\n"
        "4) 확실하지 않은 내용은 단정하지 말고, 취향 적합성 중심으로만 표현하세요.\n\n"
        f"이름: {user_name}\n"
        f"사용자 취향 텍스트: {user.get('text', '')}\n"
        f"선호 태그: {', '.join(user.get('likes', []) or [])}\n"
        f"비선호 태그: {', '.join(user.get('dislikes', []) or [])}\n"
        f"영화 제목: {movie_meta.get('title', '')}\n"
        f"영화 장르: {', '.join(movie_meta.get('genres', []) or [])}\n"
        f"핵심 요인: {top_factors}\n"
        f"정서 핵심 태그: {emotion_tags}\n"
        f"서사 핵심 태그: {narrative_tags}\n"
        f"결말 핵심 태그: {ending_tags}\n"
        f"참고 만족도: {probability * 100:.1f}\n"
        f"참고 페널티: {float(breakdown.get('dislike_penalty', 0.0)):.3f}\n"
        "예시 형식:\n"
        "A: 감동과 따뜻한 여운이 남는 톤에 서사가 깔끔하게 정리돼서 편하게 만족할 가능성이 높아요.\n"
        "B: 속도감 있는 전개와 반전 요소 덕분에 몰입감이 강하고 긴장감을 좋아하는 취향에 잘 맞아요.\n"
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": int(os.getenv("BEDROCK_MAX_TOKENS", "256")),
        "temperature": float(os.getenv("BEDROCK_TEMPERATURE", "0.2")),
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = bedrock_client.invoke_model(modelId=model_id, body=json.dumps(body))
        response_body = json.loads(response["body"].read())
        text = (response_body.get("content") or [{}])[0].get("text", "").strip()
        text = " ".join(text.split())
        if not text:
            return build_user_explanation(breakdown, factor_tag_details=factor_tag_details)
        if ":" in text:
            text = f"{user_name}: {text.split(':', 1)[1].strip()}"
        else:
            text = f"{user_name}: {text}"
        return text
    except Exception as exc:
        print(f"[WARN] Explanation LLM failed, fallback to rule explanation: {exc}")
        return build_user_explanation(breakdown, factor_tag_details=factor_tag_details)


def average_profiles(user_profiles: List[Dict[str, Any]], e_keys: List[str], n_keys: List[str]) -> Dict[str, Any]:
    if not user_profiles:
        raise ValueError("user_profiles is empty")

    group_emotion = {k: 0.0 for k in e_keys}
    group_story = {k: 0.0 for k in n_keys}
    group_ending = {"happy": 0.0, "open": 0.0, "bittersweet": 0.0}

    for p in user_profiles:
        es = p.get("emotion_scores", {})
        ns = p.get("narrative_traits", {})
        ep = p.get("ending_preference", {})

        for k in e_keys:
            group_emotion[k] += float(es.get(k, 0.0))
        for k in n_keys:
            group_story[k] += float(ns.get(k, 0.0))

        group_ending["happy"] += float(ep.get("happy", 0.0))
        group_ending["open"] += float(ep.get("open", 0.0))
        group_ending["bittersweet"] += float(ep.get("bittersweet", 0.0))

    denom = float(len(user_profiles))
    for k in e_keys:
        group_emotion[k] /= denom
    for k in n_keys:
        group_story[k] /= denom
    for k in group_ending:
        group_ending[k] /= denom

    return {
        "emotion_scores": group_emotion,
        "narrative_traits": group_story,
        "ending_preference": group_ending,
    }


def aggregate_group_score(per_user_probs: List[float], strategy: str) -> float:
    if not per_user_probs:
        return 0.0

    strategy = strategy.lower().strip()
    probs = sorted(per_user_probs)

    if strategy in ("mean", "avg", "average"):
        return sum(probs) / len(probs)
    if strategy in ("least_misery", "min"):
        return min(probs)
    if strategy == "median":
        mid = len(probs) // 2
        if len(probs) % 2 == 1:
            return probs[mid]
        return (probs[mid - 1] + probs[mid]) / 2.0
    if strategy == "trimmed_mean":
        if len(probs) <= 2:
            return sum(probs) / len(probs)
        trimmed = probs[1:-1]
        return sum(trimmed) / len(trimmed)

    raise ValueError(f"Unknown strategy: {strategy} (use mean|min|median|trimmed_mean)")


def build_user_explanation(
    breakdown: Dict[str, Any],
    factor_tag_details: Optional[Dict[str, List[Dict[str, float]]]] = None,
) -> str:
    """
    Build a short natural-language explanation for per-user recommendation fit.
    """
    top_factors = breakdown.get("top_factors", []) or []
    parts: List[str] = []
    if top_factors:
        parts.append(f"주요 일치 요인: {', '.join(top_factors)}")
    if factor_tag_details:
        emotion_tags = summarize_tag_details(
            (factor_tag_details or {}).get("emotion_tags", []),
            include_scores=False,
            top_only=True,
        )
        narrative_tags = summarize_tag_details(
            (factor_tag_details or {}).get("narrative_tags", []),
            include_scores=False,
            top_only=True,
        )
        ending_tags = summarize_tag_details(
            (factor_tag_details or {}).get("ending_tags", []),
            include_scores=False,
            top_only=True,
        )
        if emotion_tags != "없음":
            parts.append(f"정서 태그: {emotion_tags}")
        if narrative_tags != "없음":
            parts.append(f"서사 태그: {narrative_tags}")
        if ending_tags != "없음":
            parts.append(f"결말 태그: {ending_tags}")

    if not parts:
        return "세부 요인 정보가 충분하지 않습니다."
    return " | ".join(parts)


def load_or_build_db(
    db_cache_path: Optional[str],
    movies: List[Dict[str, Any]],
    taxonomy: Dict[str, Any],
    movie_profiles_file: Optional[str] = None,
) -> Tuple[LocalVectorDB, List[str], List[str]]:
    e_keys = taxonomy["emotion"]["tags"]
    n_keys = taxonomy["story_flow"]["tags"]

    if db_cache_path and os.path.exists(db_cache_path):
        db = LocalVectorDB()
        db.load(db_cache_path)
        return db, e_keys, n_keys

    db = LocalVectorDB()
    movie_map = {m.get("id"): m for m in movies}

    if movie_profiles_file:
        raw_profiles = embedding.load_json(movie_profiles_file)
        if not isinstance(raw_profiles, list):
            raise ValueError("--movie-profiles 는 영화 프로필 객체 리스트(JSON array)여야 합니다.")

        for item in raw_profiles:
            if not isinstance(item, dict):
                continue
            movie_profile = dict(item)
            movie_profile.update(normalize_profile(movie_profile, taxonomy))

            movie_id = movie_profile.get("movie_id", movie_profile.get("id"))
            source_movie = movie_map.get(movie_id, {})
            title = movie_profile.get("title") or source_movie.get("title")
            if not title:
                continue

            db.add(
                profile_to_vector(movie_profile, e_keys, n_keys),
                {
                    "id": movie_id,
                    "title": title,
                    "genres": source_movie.get("genres", []),
                    "release_year": source_movie.get("release_year"),
                    "runtime": source_movie.get("runtime"),
                    "profile": movie_profile,
                },
            )
    else:
        profiles: List[Dict[str, Any]] = []
        for movie in movies:
            profiles.append(embedding.build_profile(movie, taxonomy, bedrock_client=None))
        db = build_vector_db(movies, profiles, e_keys, n_keys)

    if db_cache_path:
        os.makedirs(os.path.dirname(db_cache_path) or ".", exist_ok=True)
        db.save(db_cache_path)

    return db, e_keys, n_keys


def main() -> None:
    parser = argparse.ArgumentParser(description="A-6 Group Movie Recommendation Top-K")

    parser.add_argument("--movies", default="movies_dataset_final.json")
    parser.add_argument("--taxonomy", default="emotion_tag.json")

    parser.add_argument("--users", default=None, help="예: A:감동적인 영화 선호;B:반전 있는 영화 선호")
    parser.add_argument("--users-json", default=None)
    parser.add_argument(
        "--user-profiles",
        default=None,
        help="이미 생성된 사용자 프로필 JSON 경로 (user_id 기준 병합)",
    )
    parser.add_argument(
        "--movie-profiles",
        default=None,
        help="이미 생성된 영화 프로필 JSON 경로 (예: profiles_sample.json)",
    )

    parser.add_argument(
        "--user-pref-file",
        default=None,
        help="A-1 user_preferences.json 경로 (boost/penalty 병합용)",
    )

    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=200)
    parser.add_argument("--strategy", default="mean", help="mean|min|median|trimmed_mean")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json-out", action="store_true")

    parser.add_argument("--penalty-weight", type=float, default=0.7)
    parser.add_argument("--boost-weight", type=float, default=0.5)
    parser.add_argument("--boost-nudge", type=float, default=0.08)
    parser.add_argument("--penalty-nudge", type=float, default=0.08)

    parser.add_argument("--genres", default=None, help="예: 드라마,로맨스")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)

    parser.add_argument("--db-cache", default=None, help="예: cache/movie_vecdb.pkl")
    parser.add_argument(
        "--use-bedrock",
        action="store_true",
        help="AWS Bedrock을 사용자별 만족/불만족 설명 생성에만 사용",
    )

    args = parser.parse_args()

    taxonomy = embedding.load_taxonomy(args.taxonomy)
    movies = embedding.load_json(args.movies)
    if args.users or args.users_json:
        users = parse_users(args.users, args.users_json)
    elif args.user_profiles:
        users = parse_users_from_profiles(args.user_profiles)
    else:
        raise ValueError("사용자 입력이 없습니다. --users/--users-json 또는 --user-profiles를 전달하세요.")

    merge_a1_preference(users, args.user_pref_file)

    if args.user_profiles:
        raw_user_profiles = embedding.load_json(args.user_profiles)
        user_profile_map: Dict[str, Dict[str, Any]] = {}

        if isinstance(raw_user_profiles, list):
            for item in raw_user_profiles:
                if not isinstance(item, dict):
                    continue
                key = item.get("user_id") or item.get("name")
                if key:
                    user_profile_map[str(key)] = item.get("profile") if isinstance(item.get("profile"), dict) else item
        elif isinstance(raw_user_profiles, dict):
            for key, item in raw_user_profiles.items():
                if isinstance(item, dict):
                    user_profile_map[str(key)] = item.get("profile") if isinstance(item.get("profile"), dict) else item

        for u in users:
            key = str(u.get("user_id") or u.get("name"))
            if key in user_profile_map:
                u["profile"] = user_profile_map[key]

    user_profiles: List[Dict[str, Any]] = [build_user_profile(u, taxonomy) for u in users]

    explainer_client = None
    if args.use_bedrock:
        explainer_client = embedding.get_bedrock_client()
        if explainer_client is None:
            print("[WARN] Bedrock client initialization failed. Fallback to rule explanation.")
        else:
            print("[INFO] Bedrock explainer enabled for per-user explanation text.")

    db, e_keys, n_keys = load_or_build_db(
        args.db_cache,
        movies,
        taxonomy,
        movie_profiles_file=args.movie_profiles,
    )

    group_profile = average_profiles(user_profiles, e_keys, n_keys)

    group_boost: List[str] = []
    group_penalty: List[str] = []
    for u in users:
        group_boost.extend(u.get("likes", []) or [])
        group_penalty.extend(u.get("dislikes", []) or [])

    group_profile = apply_tag_nudges_to_group_profile(
        group_profile,
        e_keys,
        n_keys,
        boost_tags=group_boost,
        penalty_tags=group_penalty,
        boost_nudge=args.boost_nudge,
        penalty_nudge=args.penalty_nudge,
    )
    query_vec = profile_to_vector(group_profile, e_keys, n_keys)

    filters: Dict[str, Any] = {}
    if args.genres:
        filters["genres"] = [g.strip() for g in args.genres.split(",") if g.strip()]
    if args.year_from is not None:
        filters["year_from"] = args.year_from
    if args.year_to is not None:
        filters["year_to"] = args.year_to
    if not filters:
        filters = None

    candidates = db.search(query_vec, k=args.candidate_k, filters=filters)

    ranked: List[Dict[str, Any]] = []
    for item in candidates:
        meta = item["metadata"]
        movie_profile = meta.get("profile") or {}
        movie_title = meta.get("title", "")
        movie_id = meta.get("id")

        per_user_probs: List[float] = []
        per_user_detail: List[Dict[str, Any]] = []

        for u, up in zip(users, user_profiles):
            res = calculate_satisfaction_probability(
                user_profile=up,
                movie_profile=movie_profile,
                dislikes=u.get("dislikes", []),
                boost_tags=u.get("likes", []),
                penalty_weight=args.penalty_weight,
                boost_weight=args.boost_weight,
            )
            prob = float(res.get("probability", 0.0))
            per_user_probs.append(prob)

            if args.verbose:
                breakdown = res.get("breakdown", {}) or {}
                top_factors = breakdown.get("top_factors", []) or []
                factor_tag_details = extract_factor_tag_details(
                    user_profile=up,
                    movie_profile=movie_profile,
                    top_factors=top_factors,
                    top_n=1,
                )
                explanation = build_user_explanation(breakdown, factor_tag_details=factor_tag_details)
                if explainer_client is not None:
                    explanation = build_movie_explanation_with_llm(
                        user=u,
                        movie_meta=meta,
                        probability=prob,
                        breakdown=breakdown,
                        factor_tag_details=factor_tag_details,
                        bedrock_client=explainer_client,
                    )
                per_user_detail.append(
                    {
                        "user_id": u["user_id"],
                        "name": u["name"],
                        "probability": prob,
                        "top_factors": top_factors,
                        "emotion_tags": factor_tag_details.get("emotion_tags", []),
                        "narrative_tags": factor_tag_details.get("narrative_tags", []),
                        "ending_tags": factor_tag_details.get("ending_tags", []),
                        "dislike_penalty": breakdown.get("dislike_penalty", 0.0),
                        "boost_score": breakdown.get("boost_score", 0.0),
                        "explanation": explanation,
                    }
                )

        group_score = aggregate_group_score(per_user_probs, args.strategy)

        ranked.append(
            {
                "movie_id": movie_id,
                "title": movie_title,
                "genres": meta.get("genres", []),
                "release_year": meta.get("release_year"),
                "group_score": group_score,
                "prefilter_score": float(item.get("score", 0.0)),
                "per_user_detail": per_user_detail if args.verbose else None,
            }
        )

    ranked.sort(key=lambda x: x["group_score"], reverse=True)
    topk = ranked[: max(1, args.top_k)]

    if args.json_out:
        print(json.dumps({"strategy": args.strategy, "topk": topk}, ensure_ascii=False, indent=2))
        return

    print(f"그룹 추천 Top-{len(topk)} (strategy={args.strategy}, candidates={len(candidates)})")
    if filters:
        print(f"filters={filters}")
    if args.db_cache:
        print(f"db_cache={args.db_cache}")
    if args.user_pref_file:
        print(f"user_pref_file={args.user_pref_file} (A-1 boost/penalty 사용)")

    for i, r in enumerate(topk, start=1):
        year = r.get("release_year")
        genres = ", ".join(r.get("genres") or [])
        print(f"\n[{i}] {r['title']} ({year})")
        if genres:
            print(f"  genres: {genres}")
        print(f"  group_score: {r['group_score']*100:.1f}% | prefilter: {r['prefilter_score']:.3f}")

        if args.verbose and r.get("per_user_detail"):
            for ud in r["per_user_detail"]:
                p = ud["probability"] * 100
                tf = ", ".join(ud.get("top_factors", []) or [])
                print(f"    - {ud['name']}({ud['user_id']}): {p:.1f}% | top_factors: {tf}")
                if explainer_client is None:
                    e_tags = summarize_tag_details(
                        ud.get("emotion_tags", []) or [],
                        include_scores=False,
                        top_only=True,
                    )
                    n_tags = summarize_tag_details(
                        ud.get("narrative_tags", []) or [],
                        include_scores=False,
                        top_only=True,
                    )
                    d_tags = summarize_tag_details(
                        ud.get("ending_tags", []) or [],
                        include_scores=False,
                        top_only=True,
                    )
                    if e_tags != "없음":
                        print(f"      emotion_tags: {e_tags}")
                    if n_tags != "없음":
                        print(f"      narrative_tags: {n_tags}")
                    if d_tags != "없음":
                        print(f"      ending_tags: {d_tags}")
                print(f"      {ud.get('explanation', '')}")


if __name__ == "__main__":
    main()
