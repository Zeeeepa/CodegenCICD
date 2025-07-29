"""
Response caching system for Codegen API client
"""
import time
import hashlib
import json
from functools import wraps, lru_cache
from typing import Any, Dict, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
from threading import Lock
import asyncio


class CacheEntry:
    """Represents a cached entry with TTL support"""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        if self.ttl_seconds <= 0:
            return False  # Never expires
        return time.time() - self.created_at > self.ttl_seconds
    
    def get_value(self) -> Any:
        """Get the cached value and update access statistics"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def get_age_seconds(self) -> float:
        """Get the age of the cache entry in seconds"""
        return time.time() - self.created_at
    
    def get_remaining_ttl(self) -> float:
        """Get remaining TTL in seconds"""
        if self.ttl_seconds <= 0:
            return float('inf')
        return max(0, self.ttl_seconds - self.get_age_seconds())


class TTLCache:
    """Thread-safe TTL cache implementation"""
    
    def __init__(self, max_size: int = 128, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Create a deterministic key from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired entries from cache"""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['expired'] += 1
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        self._stats['evictions'] += 1
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
            return entry.get_value()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        ttl = ttl if ttl is not None else self.default_ttl
        
        with self._lock:
            # Clean up expired entries
            self._cleanup_expired()
            
            # Evict if at capacity and key doesn't exist
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expired': 0
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'expired': self._stats['expired']
            }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        with self._lock:
            entries_info = []
            for key, entry in self._cache.items():
                entries_info.append({
                    'key': key,
                    'age_seconds': entry.get_age_seconds(),
                    'remaining_ttl': entry.get_remaining_ttl(),
                    'access_count': entry.access_count,
                    'last_accessed': entry.last_accessed
                })
            
            return {
                'stats': self.get_stats(),
                'entries': entries_info
            }


class AsyncTTLCache:
    """Async version of TTL cache"""
    
    def __init__(self, max_size: int = 128, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _cleanup_expired(self):
        """Remove expired entries from cache"""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['expired'] += 1
    
    async def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._cache:
            return
        
        lru_key = min(self._cache.keys(), 
                     key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        self._stats['evictions'] += 1
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
            return entry.get_value()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        ttl = ttl if ttl is not None else self.default_ttl
        
        async with self._lock:
            await self._cleanup_expired()
            
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()
            
            self._cache[key] = CacheEntry(value, ttl)
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expired': 0
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'expired': self._stats['expired']
            }


def cached(ttl: int = 300, max_size: int = 128, key_func: Optional[Callable] = None):
    """Decorator for caching function results with TTL"""
    cache = TTLCache(max_size=max_size, default_ttl=ttl)
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(*args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_info = cache.get_stats
        wrapper.cache_stats = cache.get_cache_info
        
        return wrapper
    
    return decorator


def async_cached(ttl: int = 300, max_size: int = 128, key_func: Optional[Callable] = None):
    """Decorator for caching async function results with TTL"""
    cache = AsyncTTLCache(max_size=max_size, default_ttl=ttl)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(*args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        # Add cache management methods
        wrapper.cache_clear = cache.clear
        wrapper.cache_info = cache.get_stats
        
        return wrapper
    
    return decorator


class CacheManager:
    """Centralized cache management"""
    
    def __init__(self):
        self._caches: Dict[str, Union[TTLCache, AsyncTTLCache]] = {}
    
    def create_cache(self, name: str, max_size: int = 128, default_ttl: int = 300, async_cache: bool = False) -> Union[TTLCache, AsyncTTLCache]:
        """Create a named cache"""
        if async_cache:
            cache = AsyncTTLCache(max_size=max_size, default_ttl=default_ttl)
        else:
            cache = TTLCache(max_size=max_size, default_ttl=default_ttl)
        
        self._caches[name] = cache
        return cache
    
    def get_cache(self, name: str) -> Optional[Union[TTLCache, AsyncTTLCache]]:
        """Get a named cache"""
        return self._caches.get(name)
    
    def clear_all_caches(self):
        """Clear all managed caches"""
        for cache in self._caches.values():
            if isinstance(cache, AsyncTTLCache):
                asyncio.create_task(cache.clear())
            else:
                cache.clear()
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches"""
        stats = {}
        for name, cache in self._caches.items():
            if isinstance(cache, AsyncTTLCache):
                # For async caches, we can't call async methods here
                # This would need to be handled differently in practice
                stats[name] = {"type": "async", "available": False}
            else:
                stats[name] = cache.get_stats()
        return stats


# Global cache manager instance
cache_manager = CacheManager()


# Predefined cache configurations
class CachePresets:
    """Predefined cache configurations"""
    
    @staticmethod
    def user_cache() -> Dict[str, Any]:
        """Cache configuration for user data"""
        return {
            'ttl': 600,  # 10 minutes
            'max_size': 100
        }
    
    @staticmethod
    def organization_cache() -> Dict[str, Any]:
        """Cache configuration for organization data"""
        return {
            'ttl': 1800,  # 30 minutes
            'max_size': 50
        }
    
    @staticmethod
    def agent_run_cache() -> Dict[str, Any]:
        """Cache configuration for agent run data"""
        return {
            'ttl': 60,  # 1 minute (frequently changing)
            'max_size': 200
        }
    
    @staticmethod
    def repository_cache() -> Dict[str, Any]:
        """Cache configuration for repository data"""
        return {
            'ttl': 3600,  # 1 hour
            'max_size': 50
        }

