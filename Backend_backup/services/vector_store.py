# 벡터 DB 인터페이스 → OpenSearch/pgvector(예상)
class VectorStore:
    def search(self, vector: list[float], top_k: int = 5) -> list[dict]:
        pass
