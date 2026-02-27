"""
Redis 기반 Refresh Token 저장소
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime
from utils.cache import get_redis_client


class RefreshTokenStore:
    """Redis를 사용한 Refresh Token 저장소"""
    
    KEY_PREFIX = "refresh_token:"
    
    @staticmethod
    def _get_key(token_hash: str) -> str:
        """Redis 키 생성"""
        return f"{RefreshTokenStore.KEY_PREFIX}{token_hash}"
    
    @staticmethod
    def save(
        token_hash: str,
        user_id: str,
        jti: str,
        expires_at: datetime,
        ttl_seconds: int
    ) -> bool:
        """
        Refresh token을 Redis에 저장
        
        Args:
            token_hash: 토큰 해시
            user_id: 사용자 ID
            jti: JWT ID
            expires_at: 만료 시간
            ttl_seconds: TTL (초)
            
        Returns:
            성공 여부
        """
        client = get_redis_client()
        if not client:
            # Redis 비활성화 시 조용히 실패
            return False
        
        try:
            key = RefreshTokenStore._get_key(token_hash)
            data = {
                "user_id": user_id,
                "jti": jti,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Redis에 저장 (TTL 설정)
            client.setex(key, ttl_seconds, json.dumps(data))
            print(f"✅ [RefreshToken] Saved to Redis: {token_hash[:16]}... (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            print(f"❌ [RefreshToken] Save error: {e}")
            return False
    
    @staticmethod
    def get(token_hash: str) -> Optional[Dict[str, Any]]:
        """
        Refresh token 조회
        
        Args:
            token_hash: 토큰 해시
            
        Returns:
            토큰 데이터 또는 None (만료/revoke된 경우)
        """
        client = get_redis_client()
        if not client:
            # Redis 비활성화 시 조용히 None 반환
            return None
        
        try:
            key = RefreshTokenStore._get_key(token_hash)
            data = client.get(key)
            
            if not data:
                return None
            
            token_data = json.loads(data)
            print(f"✅ [RefreshToken] Found in Redis: {token_hash[:16]}...")
            return token_data
        except Exception as e:
            print(f"❌ [RefreshToken] Get error: {e}")
            return None
    
    @staticmethod
    def revoke(token_hash: str) -> bool:
        """
        Refresh token 무효화 (Redis에서 삭제)
        
        Args:
            token_hash: 토큰 해시
            
        Returns:
            성공 여부
        """
        client = get_redis_client()
        if not client:
            # Redis 비활성화 시 조용히 실패
            return False
        
        try:
            key = RefreshTokenStore._get_key(token_hash)
            deleted = client.delete(key)
            
            if deleted:
                print(f"✅ [RefreshToken] Revoked: {token_hash[:16]}...")
            
            return bool(deleted)
        except Exception as e:
            print(f"❌ [RefreshToken] Revoke error: {e}")
            return False
    
    @staticmethod
    def revoke_all_for_user(user_id: str) -> int:
        """
        특정 사용자의 모든 refresh token 무효화
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            삭제된 토큰 개수
        """
        client = get_redis_client()
        if not client:
            # Redis 비활성화 시 조용히 0 반환
            return 0
        
        try:
            # 모든 refresh token 키 조회
            pattern = f"{RefreshTokenStore.KEY_PREFIX}*"
            keys = client.keys(pattern)
            
            deleted_count = 0
            for key in keys:
                data = client.get(key)
                if data:
                    token_data = json.loads(data)
                    if token_data.get("user_id") == user_id:
                        client.delete(key)
                        deleted_count += 1
            
            if deleted_count > 0:
                print(f"✅ [RefreshToken] Revoked {deleted_count} tokens for user {user_id}")
            
            return deleted_count
        except Exception as e:
            print(f"❌ [RefreshToken] Revoke all error: {e}")
            return 0
    
    @staticmethod
    def exists(token_hash: str) -> bool:
        """
        Refresh token 존재 여부 확인
        
        Args:
            token_hash: 토큰 해시
            
        Returns:
            존재 여부
        """
        client = get_redis_client()
        if not client:
            # Redis 비활성화 시 조용히 False 반환
            return False
        
        try:
            key = RefreshTokenStore._get_key(token_hash)
            return bool(client.exists(key))
        except Exception as e:
            print(f"❌ [RefreshToken] Exists check error: {e}")
            return False
