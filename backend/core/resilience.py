"""
Resilience patterns for CodegenCICD - Circuit breakers, retries, and error recovery
"""
import asyncio
import time
import random
from typing import Any, Callable, Optional, Dict, List, Union
from datetime import datetime, timedelta
from enum import Enum
import structlog
from functools import wraps
from contextlib import asynccontextmanager

logger = structlog.get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    JITTER = "jitter"


class CircuitBreakerError(Exception):
    """Circuit breaker is open"""
    pass


class MaxRetriesExceededError(Exception):
    """Maximum retry attempts exceeded"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[Exception, tuple] = Exception,
        success_threshold: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED
        
        logger.info("Circuit breaker initialized", 
                   name=name, 
                   failure_threshold=failure_threshold,
                   recovery_timeout=recovery_timeout)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        # Check if circuit breaker should open
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker transitioning to half-open", name=self.name)
            else:
                logger.warning("Circuit breaker is open, rejecting call", name=self.name)
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset failure count
            self._on_success()
            return result
            
        except self.expected_exception as e:
            # Expected failure - increment failure count
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery", name=self.name)
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # Failed during recovery attempt
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker opened after failed recovery attempt", name=self.name)
        elif self.failure_count >= self.failure_threshold:
            # Too many failures
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker opened due to failure threshold", 
                         name=self.name, 
                         failure_count=self.failure_count)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class RetryManager:
    """
    Retry manager with different strategies and backoff algorithms
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        backoff_multiplier: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.backoff_multiplier = backoff_multiplier
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        expected_exceptions: tuple = (Exception,),
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug("Executing function with retry", 
                           attempt=attempt, 
                           max_attempts=self.max_attempts)
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info("Function succeeded after retry", 
                              attempt=attempt, 
                              function=func.__name__)
                
                return result
                
            except expected_exceptions as e:
                last_exception = e
                
                if attempt == self.max_attempts:
                    logger.error("Max retry attempts exceeded", 
                               attempt=attempt, 
                               function=func.__name__,
                               error=str(e))
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning("Function failed, retrying", 
                             attempt=attempt, 
                             delay=delay,
                             function=func.__name__,
                             error=str(e))
                
                await asyncio.sleep(delay)
        
        raise MaxRetriesExceededError(f"Max retries ({self.max_attempts}) exceeded. Last error: {last_exception}")
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on retry strategy"""
        
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
        elif self.strategy == RetryStrategy.JITTER:
            delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
            delay += random.uniform(0, delay * 0.1)  # Add 10% jitter
        else:
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter and self.strategy != RetryStrategy.JITTER:
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount
        
        return delay


class BulkheadManager:
    """
    Bulkhead pattern implementation for resource isolation
    """
    
    def __init__(self, name: str, max_concurrent: int = 10):
        self.name = name
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0
        self.total_requests = 0
        self.rejected_requests = 0
    
    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """Acquire resource with bulkhead protection"""
        self.total_requests += 1
        
        try:
            if timeout:
                await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)
            else:
                await self.semaphore.acquire()
            
            self.active_requests += 1
            logger.debug("Bulkhead resource acquired", 
                        name=self.name, 
                        active=self.active_requests)
            
            try:
                yield
            finally:
                self.active_requests -= 1
                self.semaphore.release()
                logger.debug("Bulkhead resource released", 
                           name=self.name, 
                           active=self.active_requests)
                
        except asyncio.TimeoutError:
            self.rejected_requests += 1
            logger.warning("Bulkhead resource acquisition timeout", 
                         name=self.name,
                         timeout=timeout)
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bulkhead statistics"""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "available_slots": self.max_concurrent - self.active_requests
        }


class TimeoutManager:
    """
    Timeout management for operations
    """
    
    @staticmethod
    async def execute_with_timeout(
        func: Callable,
        timeout: float,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with timeout"""
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            else:
                # For sync functions, run in executor with timeout
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, func, *args, **kwargs),
                    timeout=timeout
                )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Operation timed out", 
                        function=func.__name__, 
                        timeout=timeout)
            raise


class ResilienceManager:
    """
    Central resilience manager combining all patterns
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.bulkheads: Dict[str, BulkheadManager] = {}
        self.retry_managers: Dict[str, RetryManager] = {}
    
    def get_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Union[Exception, tuple] = Exception
    ) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
        return self.circuit_breakers[name]
    
    def get_bulkhead(self, name: str, max_concurrent: int = 10) -> BulkheadManager:
        """Get or create bulkhead"""
        if name not in self.bulkheads:
            self.bulkheads[name] = BulkheadManager(name, max_concurrent)
        return self.bulkheads[name]
    
    def get_retry_manager(
        self,
        name: str,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    ) -> RetryManager:
        """Get or create retry manager"""
        if name not in self.retry_managers:
            self.retry_managers[name] = RetryManager(
                max_attempts=max_attempts,
                strategy=strategy
            )
        return self.retry_managers[name]
    
    async def execute_with_resilience(
        self,
        func: Callable,
        *args,
        circuit_breaker_name: Optional[str] = None,
        bulkhead_name: Optional[str] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """Execute function with full resilience patterns"""
        
        async def _execute():
            # Apply bulkhead if specified
            if bulkhead_name:
                bulkhead = self.get_bulkhead(bulkhead_name)
                async with bulkhead.acquire():
                    return await _execute_with_circuit_breaker()
            else:
                return await _execute_with_circuit_breaker()
        
        async def _execute_with_circuit_breaker():
            # Apply circuit breaker if specified
            if circuit_breaker_name:
                circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)
                return await circuit_breaker.call(func, *args, **kwargs)
            else:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
        
        # Apply retry if specified
        if retry_config:
            retry_manager = RetryManager(**retry_config)
            execution_func = _execute
        else:
            execution_func = _execute
        
        # Apply timeout if specified
        if timeout:
            if retry_config:
                return await TimeoutManager.execute_with_timeout(
                    retry_manager.execute_with_retry,
                    timeout,
                    execution_func
                )
            else:
                return await TimeoutManager.execute_with_timeout(
                    execution_func,
                    timeout
                )
        else:
            if retry_config:
                return await retry_manager.execute_with_retry(execution_func)
            else:
                return await execution_func()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all resilience components"""
        return {
            "circuit_breakers": {
                name: cb.get_state() 
                for name, cb in self.circuit_breakers.items()
            },
            "bulkheads": {
                name: bh.get_stats() 
                for name, bh in self.bulkheads.items()
            },
            "retry_managers": {
                name: {
                    "max_attempts": rm.max_attempts,
                    "strategy": rm.strategy.value,
                    "base_delay": rm.base_delay,
                    "max_delay": rm.max_delay
                }
                for name, rm in self.retry_managers.items()
            }
        }


# Global resilience manager
resilience_manager = ResilienceManager()


# Convenience decorators
def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Union[Exception, tuple] = Exception
):
    """Decorator to add circuit breaker protection"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = resilience_manager.get_circuit_breaker(
                name, failure_threshold, recovery_timeout, expected_exception
            )
            return await circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    expected_exceptions: tuple = (Exception,)
):
    """Decorator to add retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_manager = RetryManager(max_attempts=max_attempts, strategy=strategy)
            return await retry_manager.execute_with_retry(
                func, *args, expected_exceptions=expected_exceptions, **kwargs
            )
        return wrapper
    return decorator


def with_timeout(timeout: float):
    """Decorator to add timeout protection"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await TimeoutManager.execute_with_timeout(func, timeout, *args, **kwargs)
        return wrapper
    return decorator

