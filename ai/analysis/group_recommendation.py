import argparse
import json
from typing import Any, Dict, List, Optional

from . import embedding
from .similarity import calculate_satisfaction_probability


def build_user_profile(user_text: str, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
    emotion_tags = taxonomy["emotion"]["tags"]
    story_tags = taxonomy["story_flow"]["tags"]
    return {
        "emotion_scores": embedding.score_tags(user_text, emotion_tags),
        "narrative_traits": embedding.score_tags(user_text, story_tags),
        "ending_preference": {
            "happy": embedding.stable_score(user_text, "ending_happy"),
            "open": embedding.stable_score(user_text, "ending_open"),
            "bittersweet": embedding.stable_score(user_text, "ending_bittersweet"),
        },
    }


def parse_users(users_text: Optional[str], users_json: Optional[str]) -> List[Dict[str, Any]]:
    users: List[Dict[str, Any]] = []

    if users_json:
        raw_users = json.loads(users_json)
        if not isinstance(raw_users, list):
            raise ValueError("--users-json 값은 사용자 객체 리스트여야 합니다.")

        for idx, item in enumerate(raw_users):
            if not isinstance(item, dict):
                raise ValueError("--users-json의 각 항목은 객체여야 합니다.")
            users.append(
                {
                    "name": str(item.get("name") or f"U{idx + 1}"),
                    "text": str(item.get("text", "")),
                    "likes": [str(x).strip() for x in item.get("likes", []) if str(x).strip()],
                    "dislikes": [str(x).strip() for x in item.get("dislikes", []) if str(x).strip()],
                }
            )
    elif users_text:
        chunks = [x.strip() for x in users_text.split(";") if x.strip()]
        for idx, chunk in enumerate(chunks):
            if ":" in chunk:
                name, text = chunk.split(":", 1)
                users.append({"name": name.strip() or f"U{idx + 1}", "text": text.strip(), "likes": [], "dislikes": []})
            else:
                users.append({"name": f"U{idx + 1}", "text": chunk, "likes": [], "dislikes": []})

    if not users:
        raise ValueError("사용자 입력이 없습니다. --users 또는 --users-json을 전달하세요.")
    return users


def find_movie(movies: List[Dict[str, Any]], movie_id: Optional[str], movie_title: Optional[str]) -> Dict[str, Any]:
    if movie_id is not None:
        for movie in movies:
            if str(movie.get("id")) == str(movie_id):
                return movie

    if movie_title:
        target_title = movie_title.lower()
        for movie in movies:
            if str(movie.get("title", "")).lower() == target_title:
                return movie

    raise ValueError("해당 영화를 찾을 수 없습니다. --movie-id 또는 --movie-title을 확인하세요.")


def top_tags(score_map: Dict[str, Any], n: int = 2) -> List[str]:
    pairs: List[tuple[str, float]] = []
    for key, value in score_map.items():
        try:
            pairs.append((str(key), float(value)))
        except (TypeError, ValueError):
            continue
    pairs.sort(key=lambda x: x[1], reverse=True)
    return [k for k, _ in pairs[:n]]


def build_movie_style_text(movie_profile: Dict[str, Any]) -> str:
    emotion_tags = top_tags(movie_profile.get("emotion_scores", {}), 2)
    narrative_tags = top_tags(movie_profile.get("narrative_traits", {}), 2)

    if emotion_tags and narrative_tags:
        return (
            f"이 영화는 {', '.join(emotion_tags)} 정서 톤과 "
            f"{', '.join(narrative_tags)} 서사 초점을 가지고 있어요"
        )
    if emotion_tags:
        return f"이 영화는 {', '.join(emotion_tags)} 정서 톤을 가지고 있어요"
    if narrative_tags:
        return f"이 영화는 {', '.join(narrative_tags)} 서사 초점을 가지고 있어요"
    return "이 영화는 특별한 정서 톤과 서사 초점을 가지고 있어요"


def to_satisfaction_level(probability: float) -> str:
    if probability >= 0.85:
        return "매우 만족"
    if probability >= 0.70:
        return "만족"
    if probability >= 0.50:
        return "보통"
    if probability >= 0.30:
        return "불만"
    return "매우 불만"


def main() -> None:
    parser = argparse.ArgumentParser(description="A-6 Group Movie Satisfaction (그룹 영화 만족도)")
    parser.add_argument("--movies", default="movies_dataset_final.json")
    parser.add_argument("--taxonomy", default="emotion_tag.json")
    parser.add_argument("--movie-id", default=None)
    parser.add_argument("--movie-title", default=None)
    parser.add_argument("--users", default=None, help="예: A:감동적인 영화 선호;B:반전 있는 영화 선호")
    parser.add_argument("--users-json", default=None)
    parser.add_argument("--penalty-weight", type=float, default=0.7)
    parser.add_argument("--boost-weight", type=float, default=0.5)
    args = parser.parse_args()

    taxonomy = embedding.load_taxonomy(args.taxonomy)
    movies = embedding.load_json(args.movies)
    users = parse_users(args.users, args.users_json)

    target_movie = find_movie(movies, args.movie_id, args.movie_title)
    movie_profile = embedding.build_profile(target_movie, taxonomy, bedrock_client=None)

    user_probabilities: List[float] = []
    user_levels: List[str] = []

    for user in users:
        user_profile = build_user_profile(user["text"], taxonomy)
        result = calculate_satisfaction_probability(
            user_profile=user_profile,
            movie_profile=movie_profile,
            dislikes=user["dislikes"],
            boost_tags=user["likes"],
            penalty_weight=args.penalty_weight,
            boost_weight=args.boost_weight,
        )

        prob = float(result["probability"])
        user_probabilities.append(prob)
        user_levels.append(f"{user['name']} 사용자: {to_satisfaction_level(prob)}")

    group_prob = sum(user_probabilities) / len(user_probabilities)

    print(f"그룹 만족 확률: {group_prob * 100:.0f}%")
    print(build_movie_style_text(movie_profile))
    for line in user_levels:
        print(line)


if __name__ == "__main__":
    main()
