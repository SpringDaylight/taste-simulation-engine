# 캐시 인터페이스 → ElastiCache(또는 DynamoDB TTL)(예상)
class Cache:
    def get(self, key: str):
        pass

    def set(self, key: str, value, ttl: int = 0):
        pass
