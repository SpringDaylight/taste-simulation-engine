import json
from pathlib import Path


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    raw_path = base / "raw" / "tmdb_movies.json"
    out_path = Path(__file__).parent / "movies_normalized.json"

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    normalized = []
    for item in raw:
        normalized.append(
            {
                "movie_id": item["movie_id"],
                "title": item["title"].strip(),
                "overview": item["overview"].strip(),
                "genres": sorted(set(item["genres"])),
                "rating": float(item["rating"]),
            }
        )

    out_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
