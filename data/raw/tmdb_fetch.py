import json
from pathlib import Path


def fetch_tmdb_movies() -> list[dict]:
    # 실제 구현에서는 TMDB API를 호출한다.
    return [
        {
            "movie_id": 101,
            "title": "Silent Echo",
            "overview": "조용한 일상 속 작은 사건이 남긴 여운.",
            "genres": ["Drama"],
            "rating": 7.8,
        },
        {
            "movie_id": 202,
            "title": "Edge of Night",
            "overview": "긴장감 넘치는 추적과 시원한 결말.",
            "genres": ["Thriller", "Action"],
            "rating": 8.2,
        },
    ]


def main() -> None:
    out_dir = Path(__file__).parent
    out_path = out_dir / "tmdb_movies.json"
    out_path.write_text(
        json.dumps(fetch_tmdb_movies(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
