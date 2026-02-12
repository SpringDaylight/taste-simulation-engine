import json
from pathlib import Path


def clean_overview(text: str, max_len: int = 300) -> str:
    text = " ".join(text.split())
    return text[:max_len]


def normalize_genres(genres: list[str]) -> list[str]:
    mapping = {
        "Sci-Fi": "Science Fiction",
    }
    return [mapping.get(g, g) for g in genres]


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    raw_path = base / "raw" / "tmdb_movies.json"
    out_path = Path(__file__).parent / "movies_clean.json"

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    cleaned = []
    for item in raw:
        cleaned.append(
            {
                "movie_id": item["movie_id"],
                "title": item["title"],
                "overview": clean_overview(item["overview"]),
                "genres": normalize_genres(item["genres"]),
                "rating": item["rating"],
            }
        )

    out_path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
