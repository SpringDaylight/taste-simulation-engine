"""
Redis 캐시 유틸리티
"""
import json
import redis
from typing import Optional, Any
from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_SSL,
    REDIS_ENABLED
)

# Redis 클라이언트 (전역)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Redis 클라이언트 가져오기 (싱글톤)
    """
    global _redis_client
    
    if not REDIS_ENABLED:
        # Redis가 비활성화된 경우 연결 시도하지 않음
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                ssl=REDIS_SSL,
                decode_responses=True,  # 자동으로 bytes를 str로 변환
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 연결 테스트
            _redis_client.ping()
            print(f"✅ Redis connected: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            _redis_client = None
    
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """
    캐시에서 값 가져오기
    
    Args:
        key: 캐시 키
        
    Returns:
        캐시된 값 (JSON 파싱됨) 또는 None
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        print(f"❌ Cache get error: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    캐시에 값 저장
    
    Args:
        key: 캐시 키
        value: 저장할 값 (JSON 직렬화 가능해야 함)
        ttl: TTL (초), 기본 1시간
        
    Returns:
        성공 여부
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        serialized = json.dumps(value)
        client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        print(f"❌ Cache set error: {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    캐시에서 값 삭제
    
    Args:
        key: 캐시 키
        
    Returns:
        성공 여부
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.delete(key)
        return True
    except Exception as e:
        print(f"❌ Cache delete error: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    패턴에 맞는 모든 키 삭제
    
    Args:
        pattern: 키 패턴 (예: "satisfaction:user_123:*")
        
    Returns:
        삭제된 키 개수
    """
    client = get_redis_client()
    if not client:
        return 0
    
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        print(f"❌ Cache delete pattern error: {e}")
        return 0


def cache_clear_all() -> bool:
    """
    모든 캐시 삭제 (주의: 개발 환경에서만 사용)
    
    Returns:
        성공 여부
    """
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.flushdb()
        print("⚠️ All cache cleared")
        return True
    except Exception as e:
        print(f"❌ Cache clear error: {e}")
        return False
