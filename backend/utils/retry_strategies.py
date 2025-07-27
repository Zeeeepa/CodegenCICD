"""
Advanced retry strategies with exponential backoff and jitter
"""
import asyncio
import random
import time
from typing import Callable, Any, Optional, List, Type
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True  # Add randomness to prevent thundering herd
    backoff_multiplier: float = 2.0
    retryable_exceptions: Optional[List[Type[Exception]]] = None


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted"""
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_exception}")


class RetryHandler:
    """Advanced retry handler with multiple strategies"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logger.bind(component="retry_handler")
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                self.logger.debug("Executing function attempt",
                                attempt=attempt,
                                max_attempts=self.config.max_attempts)
                
                result = await func(*args, **kwargs)
                
                if attempt > 1:
                    self.logger.info("Function succeeded after retry",
                                   attempt=attempt,
                                   total_attempts=self.config.max_attempts)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if this exception is retryable
                if not self._is_retryable_exception(e):
                    self.logger.warning("Non-retryable exception encountered",
                                      exception=str(e),
                                      exception_type=type(e).__name__)
                    raise
                
                # Don't sleep after the last attempt
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    
                    self.logger.warning("Function failed, retrying",
                                      attempt=attempt,
                                      max_attempts=self.config.max_attempts,
                                      delay=delay,
                                      exception=str(e))
                    
                    await asyncio.sleep(delay)
                else:
                    self.logger.error("All retry attempts exhausted",
                                    attempts=attempt,
                                    exception=str(e))
        
        # All attempts exhausted
        raise RetryExhaustedError(self.config.max_attempts, last_exception)
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        if self.config.retryable_exceptions is None:
            # Default retryable exceptions
            retryable_types = (
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
                OSError,
            )
            return isinstance(exception, retryable_types)
        
        return any(isinstance(exception, exc_type) 
                  for exc_type in self.config.retryable_exceptions)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on retry strategy"""
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self.config.base_delay * self._fibonacci(attempt)
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number for fibonacci backoff"""
        if n <= 1:
            return 1
        elif n == 2:
            return 1
        else:
            a, b = 1, 1
            for _ in range(3, n + 1):
                a, b = b, a + b
            return b


def retry_with_config(config: RetryConfig):
    """Decorator for applying retry logic with configuration"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(config)
            return await retry_handler.execute(func, *args, **kwargs)
        return wrapper
    return decorator


def retry(max_attempts: int = 3,
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
          jitter: bool = True,
          backoff_multiplier: float = 2.0,
          retryable_exceptions: Optional[List[Type[Exception]]] = None):
    """Simple retry decorator with common parameters"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        jitter=jitter,
        backoff_multiplier=backoff_multiplier,
        retryable_exceptions=retryable_exceptions
    )
    return retry_with_config(config)


class AdaptiveRetryHandler:
    """Adaptive retry handler that adjusts strategy based on success rates"""
    
    def __init__(self, base_config: RetryConfig):
        self.base_config = base_config
        self.success_history: List[bool] = []
        self.max_history = 100
        self.logger = logger.bind(component="adaptive_retry_handler")
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with adaptive retry strategy"""
        # Adjust config based on recent success rate
        config = self._adapt_config()
        
        retry_handler = RetryHandler(config)
        
        try:
            result = await retry_handler.execute(func, *args, **kwargs)
            self._record_success(True)
            return result
        except Exception as e:
            self._record_success(False)
            raise
    
    def _adapt_config(self) -> RetryConfig:
        """Adapt retry configuration based on success history"""
        if len(self.success_history) < 10:
            return self.base_config
        
        recent_success_rate = sum(self.success_history[-20:]) / min(20, len(self.success_history))
        
        # Adjust retry attempts based on success rate
        if recent_success_rate > 0.8:
            # High success rate, reduce retries
            max_attempts = max(1, self.base_config.max_attempts - 1)
        elif recent_success_rate < 0.5:
            # Low success rate, increase retries
            max_attempts = min(10, self.base_config.max_attempts + 2)
        else:
            max_attempts = self.base_config.max_attempts
        
        # Adjust base delay based on success rate
        if recent_success_rate < 0.3:
            # Very low success rate, increase delay
            base_delay = self.base_config.base_delay * 1.5
        else:
            base_delay = self.base_config.base_delay
        
        adapted_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=self.base_config.max_delay,
            strategy=self.base_config.strategy,
            jitter=self.base_config.jitter,
            backoff_multiplier=self.base_config.backoff_multiplier,
            retryable_exceptions=self.base_config.retryable_exceptions
        )
        
        self.logger.debug("Adapted retry configuration",
                         success_rate=recent_success_rate,
                         max_attempts=max_attempts,
                         base_delay=base_delay)
        
        return adapted_config
    
    def _record_success(self, success: bool):
        """Record success/failure for adaptive behavior"""
        self.success_history.append(success)
        if len(self.success_history) > self.max_history:
            self.success_history.pop(0)
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        if not self.success_history:
            return {"success_rate": 0.0, "total_attempts": 0}
        
        return {
            "success_rate": sum(self.success_history) / len(self.success_history),
            "total_attempts": len(self.success_history),
            "recent_success_rate": sum(self.success_history[-20:]) / min(20, len(self.success_history))
        }
