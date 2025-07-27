"""
Circuit Breaker implementation for enhanced error handling
"""
import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Request timeout in seconds


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.lock = asyncio.Lock()
        
        self.logger = logger.bind(circuit_breaker=name)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.logger.info("Circuit breaker transitioning to half-open")
                else:
                    self.logger.warning("Circuit breaker is open, failing fast")
                    raise CircuitBreakerError(f"Circuit breaker {self.name} is open")
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            await self._on_success()
            return result
            
        except Exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful execution"""
        async with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.logger.info("Circuit breaker closed after successful recovery")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0  # Reset failure count on success
    
    async def _on_failure(self, exception: Exception):
        """Handle failed execution"""
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
                self.logger.warning("Circuit breaker opened after failure in half-open state",
                                  exception=str(exception))
            elif (self.state == CircuitState.CLOSED and 
                  self.failure_count >= self.config.failure_threshold):
                self.state = CircuitState.OPEN
                self.logger.warning("Circuit breaker opened due to failure threshold",
                                  failure_count=self.failure_count,
                                  exception=str(exception))
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }


class CircuitBreakerManager:
    """Manager for multiple circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logger.bind(component="circuit_breaker_manager")
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.breakers:
            if config is None:
                config = CircuitBreakerConfig()
            self.breakers[name] = CircuitBreaker(name, config)
            self.logger.info("Created new circuit breaker", name=name)
        
        return self.breakers[name]
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers"""
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}
    
    async def reset_breaker(self, name: str):
        """Manually reset a circuit breaker"""
        if name in self.breakers:
            breaker = self.breakers[name]
            async with breaker.lock:
                breaker.state = CircuitState.CLOSED
                breaker.failure_count = 0
                breaker.success_count = 0
                self.logger.info("Circuit breaker manually reset", name=name)


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()
