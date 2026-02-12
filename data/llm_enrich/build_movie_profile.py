import json
from pathlib import Path

from ai.llm_executor import run


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    input_path = base / "preprocess" / "movies_clean.json"
    output_path = Path(__file__).parent / "movie_profiles.json"

    movies = json.loads(input_path.read_text(encoding="utf-8"))
    enriched = []
    for item in movies:
        profile = run(
            prompt_path=str(base.parent / "ai" / "prompt" / "a2_movie_emotion.yaml"),
            schema_path=str(base.parent / "ai" / "schema" / "movie_profile.json"),
            input_text=item["overview"],
        )
        enriched.append(
            {
                "movie_id": item["movie_id"],
                "title": item["title"],
                "profile": profile,
            }
        )

    output_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
