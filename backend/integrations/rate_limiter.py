"""
Advanced rate limiting system for Codegen API client
"""
import time
import asyncio
from collections import deque
from threading import Lock
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Thread-safe rate limiter with sliding window algorithm"""
    
    def __init__(self, 
                 requests_per_period: int = 60,
                 period_seconds: int = 60,
                 burst_limit: Optional[int] = None,
                 queue_size: int = 100):
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.burst_limit = burst_limit or requests_per_period
        self.queue_size = queue_size
        
        self._requests: deque = deque()
        self._lock = Lock()
        self._stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'queue_full_rejections': 0,
            'average_wait_time': 0.0
        }
        self._wait_times: deque = deque(maxlen=100)  # Keep last 100 wait times
    
    def _cleanup_old_requests(self, current_time: float):
        """Remove requests older than the period"""
        cutoff_time = current_time - self.period_seconds
        while self._requests and self._requests[0] <= cutoff_time:
            self._requests.popleft()
    
    def _calculate_wait_time(self, current_time: float) -> float:
        """Calculate how long to wait before making a request"""
        if len(self._requests) < self.requests_per_period:
            return 0.0
        
        # Find the oldest request that should be considered
        oldest_relevant_time = current_time - self.period_seconds
        
        # If we have too many requests in the current period,
        # wait until the oldest one expires
        if len(self._requests) >= self.requests_per_period:
            wait_until = self._requests[0] + self.period_seconds
            return max(0.0, wait_until - current_time)
        
        return 0.0
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without waiting"""
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            return len(self._requests) < self.requests_per_period
    
    def wait_if_needed(self) -> float:
        """Wait if necessary to respect rate limits. Returns actual wait time."""
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            
            wait_time = self._calculate_wait_time(current_time)
            
            if wait_time > 0:
                self._stats['blocked_requests'] += 1
                self._wait_times.append(wait_time)
                
                # Update average wait time
                if self._wait_times:
                    self._stats['average_wait_time'] = sum(self._wait_times) / len(self._wait_times)
        
        # Wait outside the lock to avoid blocking other threads
        if wait_time > 0:
            logger.debug("Rate limit wait", wait_time=wait_time)
            time.sleep(wait_time)
        
        # Record the request
        with self._lock:
            self._requests.append(time.time())
            self._stats['total_requests'] += 1
        
        return wait_time
    
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current rate limit usage"""
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            
            return {
                'requests_in_period': len(self._requests),
                'requests_per_period': self.requests_per_period,
                'period_seconds': self.period_seconds,
                'usage_percentage': (len(self._requests) / self.requests_per_period) * 100,
                'remaining_requests': max(0, self.requests_per_period - len(self._requests)),
                'reset_time': self._requests[0] + self.period_seconds if self._requests else None
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        with self._lock:
            current_usage = self.get_current_usage()
            
            return {
                'current_usage': current_usage,
                'total_requests': self._stats['total_requests'],
                'blocked_requests': self._stats['blocked_requests'],
                'queue_full_rejections': self._stats['queue_full_rejections'],
                'average_wait_time': self._stats['average_wait_time'],
                'block_rate': (self._stats['blocked_requests'] / max(1, self._stats['total_requests'])) * 100
            }
    
    def reset(self):
        """Reset the rate limiter state"""
        with self._lock:
            self._requests.clear()
            self._stats = {
                'total_requests': 0,
                'blocked_requests': 0,
                'queue_full_rejections': 0,
                'average_wait_time': 0.0
            }
            self._wait_times.clear()


class AsyncRateLimiter:
    """Async version of rate limiter"""
    
    def __init__(self, 
                 requests_per_period: int = 60,
                 period_seconds: int = 60,
                 burst_limit: Optional[int] = None,
                 queue_size: int = 100):
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.burst_limit = burst_limit or requests_per_period
        self.queue_size = queue_size
        
        self._requests: deque = deque()
        self._lock = asyncio.Lock()
        self._stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'queue_full_rejections': 0,
            'average_wait_time': 0.0
        }
        self._wait_times: deque = deque(maxlen=100)
    
    def _cleanup_old_requests(self, current_time: float):
        """Remove requests older than the period"""
        cutoff_time = current_time - self.period_seconds
        while self._requests and self._requests[0] <= cutoff_time:
            self._requests.popleft()
    
    def _calculate_wait_time(self, current_time: float) -> float:
        """Calculate how long to wait before making a request"""
        if len(self._requests) < self.requests_per_period:
            return 0.0
        
        if len(self._requests) >= self.requests_per_period:
            wait_until = self._requests[0] + self.period_seconds
            return max(0.0, wait_until - current_time)
        
        return 0.0
    
    async def can_make_request(self) -> bool:
        """Check if a request can be made without waiting"""
        async with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            return len(self._requests) < self.requests_per_period
    
    async def wait_if_needed(self) -> float:
        """Wait if necessary to respect rate limits. Returns actual wait time."""
        async with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            
            wait_time = self._calculate_wait_time(current_time)
            
            if wait_time > 0:
                self._stats['blocked_requests'] += 1
                self._wait_times.append(wait_time)
                
                if self._wait_times:
                    self._stats['average_wait_time'] = sum(self._wait_times) / len(self._wait_times)
        
        # Wait outside the lock
        if wait_time > 0:
            logger.debug("Rate limit wait", wait_time=wait_time)
            await asyncio.sleep(wait_time)
        
        # Record the request
        async with self._lock:
            self._requests.append(time.time())
            self._stats['total_requests'] += 1
        
        return wait_time
    
    async def get_current_usage(self) -> Dict[str, Any]:
        """Get current rate limit usage"""
        async with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            
            return {
                'requests_in_period': len(self._requests),
                'requests_per_period': self.requests_per_period,
                'period_seconds': self.period_seconds,
                'usage_percentage': (len(self._requests) / self.requests_per_period) * 100,
                'remaining_requests': max(0, self.requests_per_period - len(self._requests)),
                'reset_time': self._requests[0] + self.period_seconds if self._requests else None
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        async with self._lock:
            current_usage = await self.get_current_usage()
            
            return {
                'current_usage': current_usage,
                'total_requests': self._stats['total_requests'],
                'blocked_requests': self._stats['blocked_requests'],
                'queue_full_rejections': self._stats['queue_full_rejections'],
                'average_wait_time': self._stats['average_wait_time'],
                'block_rate': (self._stats['blocked_requests'] / max(1, self._stats['total_requests'])) * 100
            }
    
    async def reset(self):
        """Reset the rate limiter state"""
        async with self._lock:
            self._requests.clear()
            self._stats = {
                'total_requests': 0,
                'blocked_requests': 0,
                'queue_full_rejections': 0,
                'average_wait_time': 0.0
            }
            self._wait_times.clear()


class AdaptiveRateLimiter:
    """Rate limiter that adapts based on server responses"""
    
    def __init__(self, 
                 initial_requests_per_period: int = 60,
                 period_seconds: int = 60,
                 min_requests_per_period: int = 10,
                 max_requests_per_period: int = 200):
        self.period_seconds = period_seconds
        self.min_requests_per_period = min_requests_per_period
        self.max_requests_per_period = max_requests_per_period
        
        self._current_limit = initial_requests_per_period
        self._base_limiter = AsyncRateLimiter(
            requests_per_period=self._current_limit,
            period_seconds=period_seconds
        )
        
        self._consecutive_successes = 0
        self._consecutive_rate_limits = 0
        self._lock = asyncio.Lock()
        
        # Adaptation parameters
        self._increase_threshold = 10  # Successes before increasing limit
        self._decrease_factor = 0.5    # Factor to decrease limit on rate limit
        self._increase_factor = 1.1    # Factor to increase limit on success
    
    async def wait_if_needed(self) -> float:
        """Wait if necessary, adapting the rate limit based on responses"""
        return await self._base_limiter.wait_if_needed()
    
    async def record_success(self):
        """Record a successful request"""
        async with self._lock:
            self._consecutive_successes += 1
            self._consecutive_rate_limits = 0
            
            # Increase limit if we've had enough consecutive successes
            if self._consecutive_successes >= self._increase_threshold:
                new_limit = min(
                    self.max_requests_per_period,
                    int(self._current_limit * self._increase_factor)
                )
                
                if new_limit > self._current_limit:
                    self._current_limit = new_limit
                    self._base_limiter = AsyncRateLimiter(
                        requests_per_period=self._current_limit,
                        period_seconds=self.period_seconds
                    )
                    logger.info("Increased rate limit", new_limit=self._current_limit)
                
                self._consecutive_successes = 0
    
    async def record_rate_limit(self, retry_after: Optional[int] = None):
        """Record a rate limit response"""
        async with self._lock:
            self._consecutive_rate_limits += 1
            self._consecutive_successes = 0
            
            # Decrease limit immediately on rate limit
            new_limit = max(
                self.min_requests_per_period,
                int(self._current_limit * self._decrease_factor)
            )
            
            if new_limit < self._current_limit:
                self._current_limit = new_limit
                self._base_limiter = AsyncRateLimiter(
                    requests_per_period=self._current_limit,
                    period_seconds=self.period_seconds
                )
                logger.warning("Decreased rate limit due to rate limiting", 
                             new_limit=self._current_limit)
    
    async def get_current_limit(self) -> int:
        """Get the current rate limit"""
        async with self._lock:
            return self._current_limit
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        base_stats = await self._base_limiter.get_stats()
        
        async with self._lock:
            adaptive_stats = {
                'current_limit': self._current_limit,
                'min_limit': self.min_requests_per_period,
                'max_limit': self.max_requests_per_period,
                'consecutive_successes': self._consecutive_successes,
                'consecutive_rate_limits': self._consecutive_rate_limits
            }
        
        return {
            'adaptive': adaptive_stats,
            'base': base_stats
        }


class RateLimitManager:
    """Manages multiple rate limiters for different endpoints/operations"""
    
    def __init__(self):
        self._limiters: Dict[str, AsyncRateLimiter] = {}
        self._lock = asyncio.Lock()
    
    async def get_limiter(self, 
                         name: str, 
                         requests_per_period: int = 60,
                         period_seconds: int = 60) -> AsyncRateLimiter:
        """Get or create a rate limiter for a specific operation"""
        async with self._lock:
            if name not in self._limiters:
                self._limiters[name] = AsyncRateLimiter(
                    requests_per_period=requests_per_period,
                    period_seconds=period_seconds
                )
            return self._limiters[name]
    
    async def wait_for_operation(self, operation_name: str) -> float:
        """Wait for a specific operation if needed"""
        limiter = await self.get_limiter(operation_name)
        return await limiter.wait_if_needed()
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all rate limiters"""
        async with self._lock:
            stats = {}
            for name, limiter in self._limiters.items():
                stats[name] = await limiter.get_stats()
            return stats
    
    async def reset_all(self):
        """Reset all rate limiters"""
        async with self._lock:
            for limiter in self._limiters.values():
                await limiter.reset()


# Global rate limit manager
rate_limit_manager = RateLimitManager()


# Predefined rate limit configurations
class RateLimitPresets:
    """Predefined rate limit configurations"""
    
    @staticmethod
    def default() -> Dict[str, Any]:
        """Default rate limiting configuration"""
        return {
            'requests_per_period': 60,
            'period_seconds': 60
        }
    
    @staticmethod
    def conservative() -> Dict[str, Any]:
        """Conservative rate limiting for sensitive operations"""
        return {
            'requests_per_period': 30,
            'period_seconds': 60
        }
    
    @staticmethod
    def aggressive() -> Dict[str, Any]:
        """Aggressive rate limiting for high-throughput scenarios"""
        return {
            'requests_per_period': 120,
            'period_seconds': 60
        }
    
    @staticmethod
    def bulk_operations() -> Dict[str, Any]:
        """Rate limiting optimized for bulk operations"""
        return {
            'requests_per_period': 100,
            'period_seconds': 60,
            'burst_limit': 150
        }


def rate_limited(requests_per_period: int = 60, 
                period_seconds: int = 60,
                operation_name: Optional[str] = None):
    """Decorator for applying rate limiting to functions"""
    def decorator(func):
        limiter_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                limiter = await rate_limit_manager.get_limiter(
                    limiter_name, requests_per_period, period_seconds
                )
                await limiter.wait_if_needed()
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, use a simple rate limiter
                if not hasattr(sync_wrapper, '_limiter'):
                    sync_wrapper._limiter = RateLimiter(
                        requests_per_period, period_seconds
                    )
                sync_wrapper._limiter.wait_if_needed()
                return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator

