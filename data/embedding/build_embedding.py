import json
from pathlib import Path


def fake_embed(text: str) -> list[float]:
    # 실제 구현에서는 Bedrock Embeddings 등을 호출한다.
    return [float(len(text) % 7), float(len(text) % 11), float(len(text) % 13)]


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    input_path = base / "llm_enrich" / "movie_profiles.json"
    output_path = Path(__file__).parent / "movie_embeddings.json"

    items = json.loads(input_path.read_text(encoding="utf-8"))
    embedded = []
    for item in items:
        profile = item["profile"]
        text = " ".join(
            profile.get("emotion_tone", [])
            + profile.get("narrative_focus", [])
            + [profile.get("pacing", "")]
        )
        embedded.append(
            {
                "movie_id": item["movie_id"],
                "embedding": fake_embed(text),
            }
        )

    output_path.write_text(
        json.dumps(embedded, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
