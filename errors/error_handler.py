"""
Global Error Handler

This module provides comprehensive error handling with automatic error
reporting, recovery strategies, and integration with logging and monitoring.
"""

import asyncio
import logging
import sys
import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta

from errors.exceptions import (
    BaseApplicationError, ErrorCode, ErrorSeverity,
    create_error_response, wrap_exception
)
from logging_config.logger import get_logger, set_correlation_id, LogContext


class ErrorHandler:
    """Global error handler with recovery strategies"""
    
    def __init__(self):
        self.logger = get_logger('error_handler')
        self.error_counts: Dict[str, int] = {}
        self.error_timestamps: Dict[str, List[datetime]] = {}
        self.recovery_strategies: Dict[ErrorCode, Callable] = {}
        self.error_callbacks: List[Callable[[BaseApplicationError], None]] = []
        
        # Setup default recovery strategies
        self._setup_default_recovery_strategies()
    
    def _setup_default_recovery_strategies(self):
        """Setup default error recovery strategies"""
        
        # Database connection recovery
        def recover_database_connection(error: BaseApplicationError):
            """Attempt to recover database connection"""
            try:
                from database.connection_manager import get_database_manager
                db_manager = get_database_manager()
                
                # Close existing connections
                db_manager.close()
                
                # Reinitialize database manager
                from database.connection_manager import _db_manager
                _db_manager = None
                
                # Test new connection
                new_db_manager = get_database_manager()
                health = new_db_manager.health_check()
                
                if health.get('healthy'):
                    self.logger.info("Database connection recovered successfully")
                    return True
                else:
                    self.logger.error("Database connection recovery failed")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Error during database recovery: {e}")
                return False
        
        # API rate limit recovery
        def recover_rate_limit(error: BaseApplicationError):
            """Handle rate limit recovery"""
            retry_after = error.context.get('retry_after', 60)
            self.logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
            
            # In a real implementation, you might want to:
            # 1. Queue the request for later
            # 2. Use exponential backoff
            # 3. Switch to alternative endpoints
            
            return True  # Indicate recovery strategy exists
        
        # Network error recovery
        def recover_network_error(error: BaseApplicationError):
            """Handle network error recovery"""
            self.logger.warning("Network error detected, implementing retry strategy")
            
            # In a real implementation:
            # 1. Check network connectivity
            # 2. Implement exponential backoff
            # 3. Switch to backup endpoints
            
            return True
        
        # Register recovery strategies
        self.recovery_strategies[ErrorCode.DATABASE_CONNECTION_ERROR] = recover_database_connection
        self.recovery_strategies[ErrorCode.API_RATE_LIMIT_ERROR] = recover_rate_limit
        self.recovery_strategies[ErrorCode.NETWORK_ERROR] = recover_network_error
    
    def handle_error(
        self,
        error: Union[Exception, BaseApplicationError],
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        attempt_recovery: bool = True
    ) -> BaseApplicationError:
        """Handle an error with logging, recovery, and reporting"""
        
        # Ensure we have a BaseApplicationError
        if not isinstance(error, BaseApplicationError):
            app_error = wrap_exception(error, context=context)
        else:
            app_error = error
        
        # Set correlation ID if provided
        if correlation_id:
            app_error.correlation_id = correlation_id
        elif not app_error.correlation_id:
            app_error.correlation_id = set_correlation_id()
        
        # Update error statistics
        self._update_error_stats(app_error)
        
        # Log the error
        self._log_error(app_error)
        
        # Attempt recovery if enabled
        if attempt_recovery:
            recovery_success = self._attempt_recovery(app_error)
            if recovery_success:
                self.logger.info(f"Error recovery successful for {app_error.error_code.value}")
        
        # Notify error callbacks
        self._notify_error_callbacks(app_error)
        
        # Check for error patterns that might indicate system issues
        self._check_error_patterns(app_error)
        
        return app_error
    
    def _update_error_stats(self, error: BaseApplicationError):
        """Update error statistics"""
        error_key = error.error_code.value
        
        # Update count
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Update timestamps
        if error_key not in self.error_timestamps:
            self.error_timestamps[error_key] = []
        
        self.error_timestamps[error_key].append(error.timestamp)
        
        # Keep only recent timestamps (last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.error_timestamps[error_key] = [
            ts for ts in self.error_timestamps[error_key] if ts > cutoff
        ]
    
    def _log_error(self, error: BaseApplicationError):
        """Log the error with appropriate level and context"""
        log_context = LogContext(
            correlation_id=error.correlation_id,
            component='error_handler',
            operation='handle_error',
            metadata={
                'error_code': error.error_code.value,
                'severity': error.severity.value,
                'context': error.context
            }
        )
        
        # Determine log level based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            log_level = 'critical'
        elif error.severity == ErrorSeverity.HIGH:
            log_level = 'error'
        elif error.severity == ErrorSeverity.MEDIUM:
            log_level = 'warning'
        else:
            log_level = 'info'
        
        # Log the error
        log_message = f"[{error.error_code.value}] {error.message}"
        
        # Add exception traceback if available
        if error.cause:
            log_message += f"\nCaused by: {error.cause}"
            if hasattr(error.cause, '__traceback__'):
                tb_lines = traceback.format_exception(
                    type(error.cause),
                    error.cause,
                    error.cause.__traceback__
                )
                log_message += f"\nTraceback:\n{''.join(tb_lines)}"
        
        getattr(self.logger, log_level)(log_message, extra=log_context.__dict__)
    
    def _attempt_recovery(self, error: BaseApplicationError) -> bool:
        """Attempt to recover from the error"""
        recovery_strategy = self.recovery_strategies.get(error.error_code)
        
        if recovery_strategy:
            try:
                self.logger.info(f"Attempting recovery for error: {error.error_code.value}")
                return recovery_strategy(error)
                
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed: {recovery_error}")
                return False
        
        return False
    
    def _notify_error_callbacks(self, error: BaseApplicationError):
        """Notify registered error callbacks"""
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as callback_error:
                self.logger.error(f"Error callback failed: {callback_error}")
    
    def _check_error_patterns(self, error: BaseApplicationError):
        """Check for error patterns that might indicate system issues"""
        error_key = error.error_code.value
        recent_errors = len(self.error_timestamps.get(error_key, []))
        
        # Check for error spikes
        if recent_errors > 10:  # More than 10 errors of same type in last hour
            self.logger.critical(
                f"Error spike detected: {recent_errors} occurrences of {error_key} in the last hour"
            )
            
            # In a real implementation, you might:
            # 1. Send alerts to monitoring systems
            # 2. Trigger circuit breakers
            # 3. Scale up resources
            # 4. Switch to degraded mode
    
    def register_recovery_strategy(
        self,
        error_code: ErrorCode,
        strategy: Callable[[BaseApplicationError], bool]
    ):
        """Register a custom recovery strategy"""
        self.recovery_strategies[error_code] = strategy
        self.logger.info(f"Registered recovery strategy for {error_code.value}")
    
    def register_error_callback(self, callback: Callable[[BaseApplicationError], None]):
        """Register an error callback"""
        self.error_callbacks.append(callback)
        self.logger.info("Registered error callback")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = sum(self.error_counts.values())
        
        # Calculate error rates
        error_rates = {}
        for error_code, timestamps in self.error_timestamps.items():
            recent_count = len(timestamps)
            error_rates[error_code] = {
                'total_count': self.error_counts.get(error_code, 0),
                'recent_count': recent_count,
                'rate_per_hour': recent_count  # Already filtered to last hour
            }
        
        return {
            'total_errors': total_errors,
            'error_types': len(self.error_counts),
            'error_rates': error_rates,
            'recovery_strategies': len(self.recovery_strategies),
            'error_callbacks': len(self.error_callbacks)
        }
    
    def reset_stats(self):
        """Reset error statistics"""
        self.error_counts.clear()
        self.error_timestamps.clear()
        self.logger.info("Error statistics reset")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get or create the global error handler instance"""
    global _error_handler
    
    if _error_handler is None:
        _error_handler = ErrorHandler()
    
    return _error_handler


def handle_error(
    error: Union[Exception, BaseApplicationError],
    context: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    attempt_recovery: bool = True
) -> BaseApplicationError:
    """Handle an error using the global error handler"""
    return get_error_handler().handle_error(error, context, correlation_id, attempt_recovery)


# Decorators for error handling
def handle_exceptions(
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = False,
    return_value: Any = None
):
    """Decorator to handle exceptions in functions"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseApplicationError:
                # Re-raise application errors as-is
                raise
            except Exception as e:
                # Wrap and handle other exceptions
                app_error = wrap_exception(
                    e,
                    error_code=error_code,
                    severity=severity,
                    context={
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }
                )
                
                handle_error(app_error)
                
                if reraise:
                    raise app_error
                else:
                    return return_value
        
        return wrapper
    
    return decorator


def handle_async_exceptions(
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = False,
    return_value: Any = None
):
    """Decorator to handle exceptions in async functions"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseApplicationError:
                # Re-raise application errors as-is
                raise
            except Exception as e:
                # Wrap and handle other exceptions
                app_error = wrap_exception(
                    e,
                    error_code=error_code,
                    severity=severity,
                    context={
                        'function': func.__name__,
                        'args': str(args),
                        'kwargs': str(kwargs)
                    }
                )
                
                handle_error(app_error)
                
                if reraise:
                    raise app_error
                else:
                    return return_value
        
        return wrapper
    
    return decorator


# Context manager for error handling
class error_context:
    """Context manager for error handling"""
    
    def __init__(
        self,
        operation: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        reraise: bool = True,
        context: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.error_code = error_code
        self.severity = severity
        self.reraise = reraise
        self.context = context or {}
        self.correlation_id = None
    
    def __enter__(self):
        self.correlation_id = set_correlation_id()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if not isinstance(exc_val, BaseApplicationError):
                app_error = wrap_exception(
                    exc_val,
                    error_code=self.error_code,
                    severity=self.severity,
                    context={
                        **self.context,
                        'operation': self.operation
                    }
                )
            else:
                app_error = exc_val
            
            handle_error(app_error, correlation_id=self.correlation_id)
            
            if not self.reraise:
                return True  # Suppress the exception
        
        return False


# Global exception handler for uncaught exceptions
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Global handler for uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow KeyboardInterrupt to propagate normally
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Handle other uncaught exceptions
    error = wrap_exception(
        exc_value,
        message=f"Uncaught exception: {exc_type.__name__}",
        error_code=ErrorCode.UNKNOWN_ERROR,
        severity=ErrorSeverity.CRITICAL,
        context={
            'exception_type': exc_type.__name__,
            'traceback': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        }
    )
    
    handle_error(error)


# Install global exception handler
sys.excepthook = global_exception_handler


# Async exception handler
def handle_async_exception(loop, context):
    """Handle exceptions in async code"""
    exception = context.get('exception')
    
    if exception:
        error = wrap_exception(
            exception,
            message=f"Async exception: {context.get('message', 'Unknown')}",
            error_code=ErrorCode.UNKNOWN_ERROR,
            severity=ErrorSeverity.HIGH,
            context=context
        )
        
        handle_error(error)


# Set async exception handler
def setup_async_exception_handling():
    """Setup async exception handling"""
    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_async_exception)
    except RuntimeError:
        # No event loop running
        pass


# Initialize async exception handling
setup_async_exception_handling()

