import json
from pathlib import Path


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    input_path = base / "embedding" / "movie_embeddings.json"
    embeddings = json.loads(input_path.read_text(encoding="utf-8"))

    # 실제 구현에서는 OpenSearch에 인덱싱한다.
    print(f"indexing {len(embeddings)} items")


if __name__ == "__main__":
    main()
