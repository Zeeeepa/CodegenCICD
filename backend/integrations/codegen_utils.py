"""
Codegen API client utility classes
"""
import time
import json
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List, Callable
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from datetime import datetime
import requests

from .codegen_api_models import (
    BulkOperationResult, 
    RequestMetrics, 
    ClientStats, 
    WebhookEvent
)
from .codegen_exceptions import (
    RateLimitError, 
    NetworkError, 
    CodegenAPIError,
    WebhookError
)

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3, backoff_factor: float = 2.0, base_delay: float = 1.0
):
    """Decorator for retrying functions with exponential backoff"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt == max_retries:
                        raise
                    logger.warning(f"Rate limited, waiting {e.retry_after} seconds")
                    time.sleep(e.retry_after)
                except (requests.RequestException, NetworkError) as e:
                    if attempt == max_retries:
                        raise CodegenAPIError(
                            f"Request failed after {max_retries} retries: {str(e)}", 0
                        )
                    sleep_time = base_delay * (backoff_factor**attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), retrying in {sleep_time}s: {str(e)}"
                    )
                    time.sleep(sleep_time)
            return None

        return wrapper

    return decorator


class RateLimiter:
    """Thread-safe rate limiter with sliding window"""

    def __init__(self, requests_per_period: int, period_seconds: int):
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.requests = []
        self.lock = Lock()

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            # Remove old requests
            self.requests = [
                req_time
                for req_time in self.requests
                if now - req_time < self.period_seconds
            ]

            if len(self.requests) >= self.requests_per_period:
                sleep_time = self.period_seconds - (now - self.requests[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)

            self.requests.append(now)

    def get_current_usage(self) -> Dict[str, Any]:
        """Get current rate limit usage"""
        with self.lock:
            now = time.time()
            recent_requests = [
                req_time
                for req_time in self.requests
                if now - req_time < self.period_seconds
            ]
            return {
                "current_requests": len(recent_requests),
                "max_requests": self.requests_per_period,
                "period_seconds": self.period_seconds,
                "usage_percentage": (len(recent_requests) / self.requests_per_period)
                * 100,
            }


class CacheManager:
    """Advanced in-memory cache with TTL support and statistics"""

    def __init__(self, max_size: int = 128, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_counts: Dict[str, int] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            # Check if expired
            if time.time() - self._timestamps[key] > self.ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                del self._access_counts[key]
                self._misses += 1
                return None

            self._hits += 1
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
            return self._cache[key]

    def set(self, key: str, value: Any):
        """Set value in cache with TTL"""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                if self._timestamps:  # Check if timestamps dict is not empty
                    oldest_key = min(self._timestamps, key=self._timestamps.get)
                    del self._cache[oldest_key]
                    del self._timestamps[oldest_key]
                    if oldest_key in self._access_counts:
                        del self._access_counts[oldest_key]

            self._cache[key] = value
            self._timestamps[key] = time.time()
            self._access_counts[key] = self._access_counts.get(key, 0)

    def clear(self):
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._access_counts.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) * 100 if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percentage": hit_rate,
                "ttl_seconds": self.ttl_seconds,
            }


class WebhookHandler:
    """Advanced webhook event handler with signature verification and event filtering"""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key
        self.handlers: Dict[str, List[Callable]] = {}
        self.middleware: List[Callable] = []

    def register_handler(
        self, event_type: str, handler: Callable[[Dict[str, Any]], None]
    ):
        """Register a handler for specific webhook events"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered webhook handler for event type: {event_type}")

    def register_middleware(
        self, middleware: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """Register middleware to process all webhook events"""
        self.middleware.append(middleware)

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.secret_key:
            logger.warning(
                "No secret key configured for webhook signature verification"
            )
            return True

        expected_signature = hmac.new(
            self.secret_key.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    def handle_webhook(self, payload: Dict[str, Any], signature: Optional[str] = None):
        """Process incoming webhook payload with middleware and handlers"""
        try:
            # Verify signature if provided
            if signature and not self.verify_signature(
                json.dumps(payload).encode(), signature
            ):
                raise WebhookError("Invalid webhook signature")

            # Apply middleware
            processed_payload = payload
            for middleware in self.middleware:
                processed_payload = middleware(processed_payload)

            event_type = processed_payload.get("event_type")
            if not event_type:
                raise WebhookError("Missing event_type in webhook payload")

            # Execute handlers
            if event_type in self.handlers:
                for handler in self.handlers[event_type]:
                    try:
                        handler(processed_payload)
                    except Exception as e:
                        logger.error(f"Handler error for {event_type}: {str(e)}")
                logger.info(f"Successfully processed webhook event: {event_type}")
            else:
                logger.warning(f"No handler registered for event type: {event_type}")

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise WebhookError(f"Webhook processing failed: {str(e)}")


class BulkOperationManager:
    """Advanced manager for bulk operations with progress tracking"""

    def __init__(self, max_workers: int = 5, batch_size: int = 100):
        self.max_workers = max_workers
        self.batch_size = batch_size

    def execute_bulk_operation(
        self,
        operation_func: Callable,
        items: List[Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        *args,
        **kwargs,
    ) -> BulkOperationResult:
        """Execute a bulk operation with error handling, metrics, and progress tracking"""
        start_time = time.time()
        results = []
        errors = []
        successful_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(operation_func, item, *args, **kwargs): (i, item)
                for i, item in enumerate(items)
            }

            # Collect results with progress tracking
            completed = 0
            for future in as_completed(future_to_item):
                i, item = future_to_item[future]
                completed += 1

                try:
                    result = future.result()
                    results.append(result)
                    successful_count += 1
                except Exception as e:
                    error_info = {
                        "index": i,
                        "item": str(item),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                    errors.append(error_info)
                    logger.error(f"Bulk operation failed for item {i}: {str(e)}")

                # Call progress callback
                if progress_callback:
                    progress_callback(completed, len(items))

        duration = time.time() - start_time
        success_rate = successful_count / len(items) if items else 0

        return BulkOperationResult(
            total_items=len(items),
            successful_items=successful_count,
            failed_items=len(errors),
            success_rate=success_rate,
            duration_seconds=duration,
            errors=errors,
            results=results,
        )


class MetricsCollector:
    """Advanced metrics collection and analysis"""

    def __init__(self):
        self.requests: List[RequestMetrics] = []
        self.start_time = datetime.now()
        self._lock = Lock()

    def record_request(
        self,
        method: str,
        endpoint: str,
        duration: float,
        status_code: int,
        request_id: str,
        cached: bool = False,
    ):
        """Record a request with comprehensive metrics"""
        with self._lock:
            metric = RequestMetrics(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration_seconds=duration,
                timestamp=datetime.now(),
                request_id=request_id,
                cached=cached,
            )
            self.requests.append(metric)

            # Keep only recent requests (last 1000)
            if len(self.requests) > 1000:
                self.requests = self.requests[-1000:]

    def get_stats(self) -> ClientStats:
        """Get comprehensive client statistics"""
        with self._lock:
            if not self.requests:
                return ClientStats(
                    uptime_seconds=0,
                    total_requests=0,
                    total_errors=0,
                    error_rate=0,
                    requests_per_minute=0,
                    average_response_time=0,
                    cache_hit_rate=0,
                    status_code_distribution={},
                    recent_requests=[],
                )

            uptime = (datetime.now() - self.start_time).total_seconds()
            total_requests = len(self.requests)
            error_requests = [r for r in self.requests if r.status_code >= 400]
            cached_requests = [r for r in self.requests if r.cached]

            avg_response_time = (
                sum(r.duration_seconds for r in self.requests) / total_requests
            )
            error_rate = (
                len(error_requests) / total_requests if total_requests > 0 else 0
            )
            cache_hit_rate = (
                len(cached_requests) / total_requests if total_requests > 0 else 0
            )
            requests_per_minute = total_requests / (uptime / 60) if uptime > 0 else 0

            # Status code distribution
            status_codes = {}
            for request in self.requests:
                status_codes[request.status_code] = (
                    status_codes.get(request.status_code, 0) + 1
                )

            return ClientStats(
                uptime_seconds=uptime,
                total_requests=total_requests,
                total_errors=len(error_requests),
                error_rate=error_rate,
                requests_per_minute=requests_per_minute,
                average_response_time=avg_response_time,
                cache_hit_rate=cache_hit_rate,
                status_code_distribution=status_codes,
                recent_requests=self.requests[-10:],
            )

    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.requests.clear()
            self.start_time = datetime.now()

