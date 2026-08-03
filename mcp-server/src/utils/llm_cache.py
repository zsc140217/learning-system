"""
LLM Response Cache

Caches LLM API responses to avoid redundant calls and reduce costs.
"""
import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger


class LLMCache:
    """
    In-memory LLM response cache

    Caches responses based on (messages, model, temperature) to avoid duplicate API calls.

    Example:
        cache = LLMCache(ttl_seconds=3600)

        # Try to get from cache
        response = cache.get(messages, "deepseek-chat", 0.7)
        if response:
            return response

        # Cache miss - call API
        response = await provider.chat(messages)
        cache.set(messages, "deepseek-chat", 0.7, response)

    Note: Only cache deterministic requests (temperature=0 or low).
          High temperature requests should not be cached as they're non-deterministic.
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize cache

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default 1 hour)
            max_size: Maximum number of cache entries (default 1000)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        self._hits = 0
        self._misses = 0

        logger.info(f"LLMCache initialized: ttl={ttl_seconds}s, max_size={max_size}")

    def _make_key(self, messages: list, model: str, temperature: float) -> str:
        """
        Generate cache key from request parameters

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature parameter

        Returns:
            SHA256 hash of normalized request
        """
        # Normalize to ensure consistent hashing
        normalized = {
            "messages": messages,
            "model": model,
            "temperature": round(temperature, 2)  # Round to avoid float precision issues
        }

        content = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        key = hashlib.sha256(content.encode('utf-8')).hexdigest()

        return key

    def get(self, messages: list, model: str, temperature: float) -> Optional[str]:
        """
        Get cached response

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature parameter

        Returns:
            Cached response or None if not found/expired
        """
        key = self._make_key(messages, model, temperature)

        if key in self._cache:
            response, expire_time = self._cache[key]

            if datetime.now() < expire_time:
                self._hits += 1
                logger.info(f"Cache HIT: {key[:16]}... (hit_rate={self.get_hit_rate():.1%})")
                return response
            else:
                # Expired - remove
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key[:16]}...")

        self._misses += 1
        logger.debug(f"Cache MISS: {key[:16]}... (hit_rate={self.get_hit_rate():.1%})")
        return None

    def set(self, messages: list, model: str, temperature: float, response: str) -> None:
        """
        Cache a response

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature parameter
            response: Response to cache
        """
        # Don't cache high-temperature non-deterministic responses
        if temperature > 0.8:
            logger.debug(f"Skipping cache for high temperature ({temperature})")
            return

        key = self._make_key(messages, model, temperature)
        expire_time = datetime.now() + timedelta(seconds=self.ttl_seconds)

        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        self._cache[key] = (response, expire_time)
        logger.debug(f"Cache SET: {key[:16]}... (size={len(self._cache)}/{self.max_size})")

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry"""
        if not self._cache:
            return

        # Find entry with earliest expiration
        oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
        del self._cache[oldest_key]
        logger.debug(f"Cache EVICT: {oldest_key[:16]}...")

    def clear_expired(self) -> int:
        """
        Remove all expired cache entries

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [
            key for key, (_, expire_time) in self._cache.items()
            if now >= expire_time
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def clear(self) -> None:
        """Clear all cache entries"""
        size = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info(f"Cache cleared: {size} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0

        # Calculate memory usage estimate
        memory_bytes = sum(
            len(key) + len(response)
            for key, (response, _) in self._cache.items()
        )

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "memory_bytes": memory_bytes,
            "memory_mb": memory_bytes / 1024 / 1024
        }

    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0


class TieredLLMCache:
    """
    Two-tier cache: hot (recent) + cold (persistent)

    Hot tier: In-memory, fast access
    Cold tier: File-based, larger capacity
    """

    def __init__(
        self,
        hot_ttl: int = 600,      # 10 minutes
        cold_ttl: int = 86400,   # 24 hours
        hot_max_size: int = 100,
        cold_max_size: int = 10000
    ):
        """
        Initialize tiered cache

        Args:
            hot_ttl: Hot tier TTL in seconds
            cold_ttl: Cold tier TTL in seconds
            hot_max_size: Hot tier max entries
            cold_max_size: Cold tier max entries
        """
        self.hot_cache = LLMCache(ttl_seconds=hot_ttl, max_size=hot_max_size)
        self.cold_cache = LLMCache(ttl_seconds=cold_ttl, max_size=cold_max_size)

        logger.info(
            f"TieredLLMCache initialized: "
            f"hot({hot_ttl}s, {hot_max_size}), cold({cold_ttl}s, {cold_max_size})"
        )

    def get(self, messages: list, model: str, temperature: float) -> Optional[str]:
        """Try hot tier first, then cold tier"""
        # Try hot tier
        response = self.hot_cache.get(messages, model, temperature)
        if response:
            return response

        # Try cold tier
        response = self.cold_cache.get(messages, model, temperature)
        if response:
            # Promote to hot tier
            self.hot_cache.set(messages, model, temperature, response)
            logger.debug("Cache promotion: cold -> hot")
            return response

        return None

    def set(self, messages: list, model: str, temperature: float, response: str) -> None:
        """Set in both tiers"""
        self.hot_cache.set(messages, model, temperature, response)
        self.cold_cache.set(messages, model, temperature, response)

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics"""
        hot_stats = self.hot_cache.get_stats()
        cold_stats = self.cold_cache.get_stats()

        return {
            "hot": hot_stats,
            "cold": cold_stats,
            "total_hit_rate": (hot_stats["hits"] + cold_stats["hits"]) /
                             (hot_stats["hits"] + hot_stats["misses"] + cold_stats["misses"])
                             if (hot_stats["hits"] + hot_stats["misses"] + cold_stats["misses"]) > 0 else 0
        }
