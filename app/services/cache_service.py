"""Redis cache service for S3 listing operations"""
import json
import pickle
from typing import Optional, Dict, List, Any
import redis.asyncio as redis
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis-based cache service for storage operations"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = getattr(settings, 'CACHE_TTL', 600)  # Use settings or default to 10 minutes
    
    async def connect(self):
        """Initialize Redis connection"""
        if self.redis_client is None:
            try:
                import asyncio
                
                redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
                redis_port = int(getattr(settings, 'REDIS_PORT', 6379))
                redis_db = int(getattr(settings, 'REDIS_DB', 0))
                
                # Build connection URL - always use redis:// (no TLS/SSL)
                connection_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
                
                # Create Redis client from URL (no SSL/TLS)
                self.redis_client = redis.from_url(
                    connection_url,
                    decode_responses=False,  # We'll handle encoding ourselves
                    socket_connect_timeout=10,  # Increased timeout for AWS connections
                    socket_timeout=10,  # Increased timeout for AWS operations
                )
                
                # Test connection with timeout
                logger.info(f"Attempting to connect to Redis at {redis_host}:{redis_port}...")
                await asyncio.wait_for(self.redis_client.ping(), timeout=10.0)
                logger.info(f"Redis cache connected to {redis_host}:{redis_port}/{redis_db}")
            except asyncio.TimeoutError:
                logger.warning(f"Redis connection timeout after 10 seconds. This usually means:")
                logger.warning(f"  1. Redis server is not running or not accessible")
                logger.warning(f"  2. Security group is blocking port {redis_port}")
                logger.warning(f"  3. Network connectivity issue")
                logger.warning(f"  Caching will be disabled. App will continue without cache.")
                if self.redis_client:
                    try:
                        await self.redis_client.close()
                    except:
                        pass
                self.redis_client = None
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {type(e).__name__}: {e}")
                logger.warning(f"  Host: {redis_host}, Port: {redis_port}")
                logger.warning(f"  Caching will be disabled. App will continue without cache.")
                if self.redis_client:
                    try:
                        await self.redis_client.close()
                    except:
                        pass
                self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _get_cache_key(self, bucket: str, path: Optional[str] = None) -> str:
        """Generate cache key for S3 listing"""
        if path:
            return f"s3:list:{bucket}:{path}"
        return f"s3:list:{bucket}"
    
    async def get_list_cache(self, bucket: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached S3 listing result"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(bucket, path)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # Deserialize the cached data
                data = pickle.loads(cached_data)
                # Convert lists back to sets if needed
                if 'folders_set' in data and isinstance(data['folders_set'], list):
                    data['folders_set'] = set(data['folders_set'])
                logger.debug(f"Cache hit for key: {cache_key}")
                return data
            else:
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error getting cache for {bucket}: {e}")
            return None
    
    async def set_list_cache(self, bucket: str, data: Dict[str, Any], path: Optional[str] = None, ttl: Optional[int] = None):
        """Cache S3 listing result"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(bucket, path)
            # Convert sets to lists for serialization
            cache_data = data.copy()
            if 'folders_set' in cache_data and isinstance(cache_data['folders_set'], set):
                cache_data['folders_set'] = list(cache_data['folders_set'])
            # Serialize the data
            serialized_data = pickle.dumps(cache_data)
            
            ttl = ttl or self.cache_ttl
            await self.redis_client.setex(cache_key, ttl, serialized_data)
            logger.debug(f"Cached data for key: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Error setting cache for {bucket}: {e}")
    
    async def invalidate_list_cache(self, bucket: str, path: Optional[str] = None):
        """Invalidate cache for S3 listing"""
        if not self.redis_client:
            return
        
        try:
            # Always invalidate the root cache (main bucket listing) since list_objects() caches everything
            root_cache_key = self._get_cache_key(bucket)
            await self.redis_client.delete(root_cache_key)
            
            if path:
                # Also invalidate specific path and all parent paths (for future per-path caching)
                cache_key = self._get_cache_key(bucket, path)
                await self.redis_client.delete(cache_key)
                
                # Also invalidate parent paths
                path_parts = path.split('/')
                for i in range(len(path_parts)):
                    parent_path = '/'.join(path_parts[:i+1])
                    parent_key = self._get_cache_key(bucket, parent_path)
                    await self.redis_client.delete(parent_key)
            
            logger.info(f"Invalidated cache for bucket: {bucket}, path: {path or 'all'}")
        except Exception as e:
            logger.error(f"Error invalidating cache for {bucket}: {e}")
    
    async def clear_all_cache(self, bucket: str):
        """Clear all cache entries for a bucket"""
        if not self.redis_client:
            return
        
        try:
            pattern = f"s3:list:{bucket}*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries for bucket: {bucket}")
        except Exception as e:
            logger.error(f"Error clearing cache for {bucket}: {e}")
    
    def _get_tracking_cache_key(self, bucket: str, s3_key: str) -> str:
        """Generate cache key for tracking file"""
        return f"tracking:{bucket}:{s3_key}"
    
    async def get_tracking_cache(self, bucket: str, s3_key: str) -> Optional[list]:
        """Get cached tracking data"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_tracking_cache_key(bucket, s3_key)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = pickle.loads(cached_data)
                logger.debug(f"Cache hit for tracking: {cache_key}")
                return data
            else:
                logger.debug(f"Cache miss for tracking: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error getting tracking cache: {e}")
            return None
    
    async def set_tracking_cache(self, bucket: str, s3_key: str, data: list, ttl: Optional[int] = None):
        """Cache tracking data"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_tracking_cache_key(bucket, s3_key)
            serialized_data = pickle.dumps(data)
            
            ttl = ttl or self.cache_ttl
            await self.redis_client.setex(cache_key, ttl, serialized_data)
            logger.debug(f"Cached tracking data for key: {cache_key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Error setting tracking cache: {e}")
    
    async def invalidate_tracking_cache(self, bucket: str, s3_key: str):
        """Invalidate tracking cache"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_tracking_cache_key(bucket, s3_key)
            await self.redis_client.delete(cache_key)
            logger.info(f"Invalidated tracking cache for: {cache_key}")
        except Exception as e:
            logger.error(f"Error invalidating tracking cache: {e}")


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create cache service instance (non-blocking)"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        # Try to connect, but don't block if it fails
        try:
            await _cache_service.connect()
        except Exception as e:
            logger.warning(f"Cache service initialization failed: {e}. Continuing without cache.")
    return _cache_service


async def close_cache_service():
    """Close cache service connection"""
    global _cache_service
    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None

