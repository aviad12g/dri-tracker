"""
Caching layer for scraped data.

Implements 24-hour caching to avoid excessive requests to third-party sites.
Supports both file-based and Redis backends.
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ScraperCache:
    """
    24-hour cache for scraped metrics.
    
    Uses file-based storage by default, with optional Redis support.
    """
    
    def __init__(
        self,
        cache_dir: str = ".scraper_cache",
        ttl_hours: int = 24,
        redis_url: Optional[str] = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl = timedelta(hours=ttl_hours)
        self.redis_url = redis_url
        self._redis_client = None
        
        # Create cache directory if using file backend
        if not redis_url:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, platform: str, handle: str) -> str:
        """Generate a unique cache key for platform/handle combo."""
        raw_key = f"{platform}:{handle}".lower()
        return hashlib.md5(raw_key.encode()).hexdigest()
    
    def _get_file_path(self, cache_key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{cache_key}.json"
    
    async def _get_redis(self):
        """Get Redis client if configured."""
        if self.redis_url and self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.redis_url)
            except ImportError:
                logger.warning("redis package not installed, falling back to file cache")
                self.redis_url = None
        return self._redis_client
    
    async def get(self, platform: str, handle: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data if valid (within TTL).
        
        Args:
            platform: Platform name (youtube, telegram, etc.)
            handle: Platform handle/username
            
        Returns:
            Cached data dict or None if expired/missing
        """
        cache_key = self._get_cache_key(platform, handle)
        
        # Try Redis first
        if self.redis_url:
            redis_client = await self._get_redis()
            if redis_client:
                try:
                    data = await redis_client.get(f"dri:scraper:{cache_key}")
                    if data:
                        return json.loads(data)
                except Exception as e:
                    logger.error(f"Redis get error: {e}")
        
        # Fall back to file cache
        file_path = self._get_file_path(cache_key)
        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    cached = json.load(f)
                
                # Check TTL
                cached_at = datetime.fromisoformat(cached.get("_cached_at", "2000-01-01"))
                if datetime.utcnow() - cached_at < self.ttl:
                    logger.debug(f"Cache hit for {platform}:{handle}")
                    return cached.get("data")
                else:
                    logger.debug(f"Cache expired for {platform}:{handle}")
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid cache file {file_path}: {e}")
        
        return None
    
    async def set(self, platform: str, handle: str, data: Dict[str, Any]) -> bool:
        """
        Store data in cache.
        
        Args:
            platform: Platform name
            handle: Platform handle
            data: Data to cache
            
        Returns:
            True if successfully cached
        """
        cache_key = self._get_cache_key(platform, handle)
        cache_entry = {
            "_cached_at": datetime.utcnow().isoformat(),
            "_platform": platform,
            "_handle": handle,
            "data": data,
        }
        
        # Try Redis first
        if self.redis_url:
            redis_client = await self._get_redis()
            if redis_client:
                try:
                    await redis_client.setex(
                        f"dri:scraper:{cache_key}",
                        int(self.ttl.total_seconds()),
                        json.dumps(cache_entry),
                    )
                    return True
                except Exception as e:
                    logger.error(f"Redis set error: {e}")
        
        # Fall back to file cache
        file_path = self._get_file_path(cache_key)
        try:
            with open(file_path, "w") as f:
                json.dump(cache_entry, f)
            logger.debug(f"Cached data for {platform}:{handle}")
            return True
        except Exception as e:
            logger.error(f"Failed to write cache file: {e}")
            return False
    
    async def invalidate(self, platform: str, handle: str) -> bool:
        """
        Remove cached data for a specific platform/handle.
        
        Args:
            platform: Platform name
            handle: Platform handle
            
        Returns:
            True if successfully invalidated
        """
        cache_key = self._get_cache_key(platform, handle)
        
        # Redis
        if self.redis_url:
            redis_client = await self._get_redis()
            if redis_client:
                try:
                    await redis_client.delete(f"dri:scraper:{cache_key}")
                except Exception as e:
                    logger.error(f"Redis delete error: {e}")
        
        # File
        file_path = self._get_file_path(cache_key)
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache file: {e}")
            return False
    
    async def clear_all(self) -> int:
        """
        Clear all cached data.
        
        Returns:
            Number of entries cleared
        """
        count = 0
        
        # Redis
        if self.redis_url:
            redis_client = await self._get_redis()
            if redis_client:
                try:
                    keys = await redis_client.keys("dri:scraper:*")
                    if keys:
                        count += await redis_client.delete(*keys)
                except Exception as e:
                    logger.error(f"Redis clear error: {e}")
        
        # File
        try:
            for file_path in self.cache_dir.glob("*.json"):
                file_path.unlink()
                count += 1
        except Exception as e:
            logger.error(f"Failed to clear cache directory: {e}")
        
        return count
