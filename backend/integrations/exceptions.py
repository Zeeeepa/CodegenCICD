"""
Enhanced error handling and custom exceptions for Codegen API client
"""
import time
import random
from functools import wraps
from typing import Optional, Dict, Any, Callable, Type, Union, List
from datetime import datetime, timedelta


class CodegenAPIError(Exception):
    """Base exception for Codegen API errors"""
    
    def __init__(self, 
                 message: str, 
                 status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None,
                 request_id: Optional[str] = None,
                 endpoint: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        self.request_id = request_id
        self.endpoint = endpoint
        self.timestamp = datetime.utcnow()
        
        super().__init__(message)
    
    def __str__(self) -> str:
        """String representation with context"""
        parts = [self.message]
        
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        
        if self.endpoint:
            parts.append(f"Endpoint: {self.endpoint}")
        
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "response_data": self.response_data,
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "timestamp": self.timestamp.isoformat()
        }


class RateLimitError(CodegenAPIError):
    """Exception for rate limit errors"""
    
    def __init__(self, 
                 message: str = "Rate limit exceeded", 
                 retry_after: Optional[int] = None,
                 **kwargs):
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after or 60
    
    def get_retry_delay(self) -> int:
        """Get the recommended retry delay"""
        return self.retry_after


class AuthenticationError(CodegenAPIError):
    """Exception for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class ValidationError(CodegenAPIError):
    """Exception for request validation errors"""
    
    def __init__(self, 
                 message: str, 
                 field_errors: Optional[Dict[str, List[str]]] = None,
                 **kwargs):
        super().__init__(message, status_code=400, **kwargs)
        self.field_errors = field_errors or {}
    
    def get_field_errors(self) -> Dict[str, List[str]]:
        """Get field-specific validation errors"""
        return self.field_errors


class NotFoundError(CodegenAPIError):
    """Exception for resource not found errors"""
    
    def __init__(self, 
                 resource_type: str = "Resource", 
                 resource_id: Optional[str] = None,
                 **kwargs):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(message, status_code=404, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictError(CodegenAPIError):
    """Exception for resource conflict errors"""
    
    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(message, status_code=409, **kwargs)


class ServerError(CodegenAPIError):
    """Exception for server-side errors"""
    
    def __init__(self, message: str = "Internal server error", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


class TimeoutError(CodegenAPIError):
    """Exception for request timeout errors"""
    
    def __init__(self, 
                 message: str = "Request timeout", 
                 timeout_duration: Optional[float] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.timeout_duration = timeout_duration


class NetworkError(CodegenAPIError):
    """Exception for network-related errors"""
    
    def __init__(self, message: str = "Network error", **kwargs):
        super().__init__(message, **kwargs)


class WebhookError(CodegenAPIError):
    """Exception for webhook-related errors"""
    
    def __init__(self, 
                 message: str = "Webhook error", 
                 event_type: Optional[str] = None,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.event_type = event_type


class BulkOperationError(CodegenAPIError):
    """Exception for bulk operation errors"""
    
    def __init__(self, 
                 message: str = "Bulk operation error",
                 failed_items: Optional[List[Dict[str, Any]]] = None,
                 partial_success: bool = False,
                 **kwargs):
        super().__init__(message, **kwargs)
        self.failed_items = failed_items or []
        self.partial_success = partial_success
    
    def get_failed_count(self) -> int:
        """Get number of failed items"""
        return len(self.failed_items)


# Retry Logic Implementation
class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True,
                 retryable_exceptions: Optional[List[Type[Exception]]] = None,
                 retryable_status_codes: Optional[List[int]] = None):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            RateLimitError,
            ServerError,
            TimeoutError,
            NetworkError
        ]
        self.retryable_status_codes = retryable_status_codes or [429, 500, 502, 503, 504]
    
    def calculate_delay(self, attempt: int, exception: Optional[Exception] = None) -> float:
        """Calculate delay for the given attempt"""
        if isinstance(exception, RateLimitError):
            # Use the retry-after header value for rate limit errors
            base_delay = exception.get_retry_delay()
        else:
            base_delay = self.base_delay
        
        # Exponential backoff
        delay = base_delay * (self.backoff_factor ** (attempt - 1))
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if the operation should be retried"""
        if attempt >= self.max_attempts:
            return False
        
        # Check if exception type is retryable
        if any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions):
            return True
        
        # Check if status code is retryable
        if hasattr(exception, 'status_code') and exception.status_code in self.retryable_status_codes:
            return True
        
        return False


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator for adding retry logic with exponential backoff"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not config.should_retry(attempt, e):
                        raise
                    
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt, e)
                        await asyncio.sleep(delay)
            
            # If we get here, all retries failed
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not config.should_retry(attempt, e):
                        raise
                    
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt, e)
                        time.sleep(delay)
            
            # If we get here, all retries failed
            raise last_exception
        
        # Return appropriate wrapper based on function type
        import asyncio
        import inspect
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Predefined retry configurations
class RetryPresets:
    """Predefined retry configurations for common scenarios"""
    
    @staticmethod
    def default() -> RetryConfig:
        """Default retry configuration"""
        return RetryConfig()
    
    @staticmethod
    def aggressive() -> RetryConfig:
        """Aggressive retry configuration for critical operations"""
        return RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            backoff_factor=1.5
        )
    
    @staticmethod
    def conservative() -> RetryConfig:
        """Conservative retry configuration for non-critical operations"""
        return RetryConfig(
            max_attempts=2,
            base_delay=2.0,
            max_delay=10.0,
            backoff_factor=2.0
        )
    
    @staticmethod
    def rate_limit_focused() -> RetryConfig:
        """Retry configuration optimized for rate limit handling"""
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=120.0,  # Allow longer waits for rate limits
            backoff_factor=2.0,
            retryable_exceptions=[RateLimitError, ServerError]
        )
    
    @staticmethod
    def no_retry() -> RetryConfig:
        """No retry configuration for operations that should not be retried"""
        return RetryConfig(max_attempts=1)


# Error context manager for better error handling
class ErrorContext:
    """Context manager for enhanced error handling and logging"""
    
    def __init__(self, 
                 operation: str,
                 logger=None,
                 capture_context: bool = True):
        self.operation = operation
        self.logger = logger
        self.capture_context = capture_context
        self.start_time = None
        self.context_data = {}
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        
        if exc_type is not None:
            # Log the error with context
            if self.logger:
                error_data = {
                    "operation": self.operation,
                    "duration_seconds": duration,
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val)
                }
                
                if self.capture_context:
                    error_data.update(self.context_data)
                
                self.logger.error("Operation failed", **error_data)
        
        return False  # Don't suppress exceptions
    
    def add_context(self, **kwargs):
        """Add context data for error reporting"""
        self.context_data.update(kwargs)


# Utility functions for error handling
def create_error_from_response(response, endpoint: str = None) -> CodegenAPIError:
    """Create appropriate error from HTTP response"""
    status_code = getattr(response, 'status', None) or getattr(response, 'status_code', None)
    
    try:
        response_data = response.json() if hasattr(response, 'json') else {}
    except:
        response_data = {}
    
    # Extract error message
    message = response_data.get('message') or response_data.get('error') or f"HTTP {status_code} error"
    
    # Extract request ID if available
    request_id = None
    if hasattr(response, 'headers'):
        request_id = response.headers.get('x-request-id') or response.headers.get('request-id')
    
    # Create appropriate exception based on status code
    if status_code == 400:
        field_errors = response_data.get('field_errors', {})
        return ValidationError(message, field_errors=field_errors, 
                             response_data=response_data, request_id=request_id, endpoint=endpoint)
    elif status_code == 401:
        return AuthenticationError(message, response_data=response_data, 
                                 request_id=request_id, endpoint=endpoint)
    elif status_code == 404:
        return NotFoundError(message, response_data=response_data, 
                           request_id=request_id, endpoint=endpoint)
    elif status_code == 409:
        return ConflictError(message, response_data=response_data, 
                           request_id=request_id, endpoint=endpoint)
    elif status_code == 429:
        retry_after = None
        if hasattr(response, 'headers'):
            retry_after = response.headers.get('retry-after')
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = 60
        
        return RateLimitError(message, retry_after=retry_after, 
                            response_data=response_data, request_id=request_id, endpoint=endpoint)
    elif status_code >= 500:
        return ServerError(message, status_code=status_code, response_data=response_data, 
                         request_id=request_id, endpoint=endpoint)
    else:
        return CodegenAPIError(message, status_code=status_code, response_data=response_data, 
                             request_id=request_id, endpoint=endpoint)


def is_retryable_error(exception: Exception) -> bool:
    """Check if an error is retryable"""
    retryable_types = [RateLimitError, ServerError, TimeoutError, NetworkError]
    return any(isinstance(exception, exc_type) for exc_type in retryable_types)


def get_error_summary(exception: Exception) -> Dict[str, Any]:
    """Get a summary of an error for logging/monitoring"""
    summary = {
        "error_type": type(exception).__name__,
        "message": str(exception),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if isinstance(exception, CodegenAPIError):
        summary.update(exception.to_dict())
    
    return summary

