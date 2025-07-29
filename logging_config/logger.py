"""
Advanced Logging Configuration

This module provides comprehensive logging setup with structured logging,
correlation IDs, performance monitoring, and multiple output formats.
"""

import json
import logging
import logging.handlers
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextvars import ContextVar
from dataclasses import dataclass, asdict

from config.settings import LoggingSettings, get_settings


# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


@dataclass
class LogContext:
    """Log context information"""
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records"""
    
    def filter(self, record):
        record.correlation_id = correlation_id.get() or 'unknown'
        return True


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process,
            'correlation_id': getattr(record, 'correlation_id', 'unknown')
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info', 'correlation_id'
                ]:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Format the message
        formatted = super().format(record)
        
        # Add correlation ID if available
        correlation = getattr(record, 'correlation_id', 'unknown')
        
        # Create colored output
        return f"{level_color}[{record.levelname}]{reset_color} {formatted} (correlation_id: {correlation})"


class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to log records"""
    
    def __init__(self):
        super().__init__()
        self.start_times = {}
    
    def filter(self, record):
        # Add performance timing if available
        if hasattr(record, 'operation_start'):
            duration = time.time() - record.operation_start
            record.duration_ms = round(duration * 1000, 2)
        
        return True


class LogMetrics:
    """Log metrics collector"""
    
    def __init__(self):
        self.metrics = {
            'total_logs': 0,
            'logs_by_level': {},
            'logs_by_component': {},
            'errors_count': 0,
            'warnings_count': 0,
            'start_time': time.time()
        }
        self.lock = threading.Lock()
    
    def record_log(self, level: str, component: Optional[str] = None):
        """Record a log entry"""
        with self.lock:
            self.metrics['total_logs'] += 1
            
            # Count by level
            self.metrics['logs_by_level'][level] = (
                self.metrics['logs_by_level'].get(level, 0) + 1
            )
            
            # Count by component
            if component:
                self.metrics['logs_by_component'][component] = (
                    self.metrics['logs_by_component'].get(component, 0) + 1
                )
            
            # Count errors and warnings
            if level == 'ERROR':
                self.metrics['errors_count'] += 1
            elif level == 'WARNING':
                self.metrics['warnings_count'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self.lock:
            uptime = time.time() - self.metrics['start_time']
            
            return {
                **self.metrics,
                'uptime_seconds': uptime,
                'logs_per_minute': (self.metrics['total_logs'] / uptime) * 60 if uptime > 0 else 0,
                'error_rate': (self.metrics['errors_count'] / self.metrics['total_logs']) * 100 
                             if self.metrics['total_logs'] > 0 else 0
            }
    
    def reset(self):
        """Reset metrics"""
        with self.lock:
            self.metrics = {
                'total_logs': 0,
                'logs_by_level': {},
                'logs_by_component': {},
                'errors_count': 0,
                'warnings_count': 0,
                'start_time': time.time()
            }


class MetricsHandler(logging.Handler):
    """Handler to collect log metrics"""
    
    def __init__(self, metrics: LogMetrics):
        super().__init__()
        self.metrics = metrics
    
    def emit(self, record):
        component = getattr(record, 'component', None)
        self.metrics.record_log(record.levelname, component)


class LoggerManager:
    """Advanced logger manager with configuration and monitoring"""
    
    def __init__(self, settings: Optional[LoggingSettings] = None):
        self.settings = settings or get_settings().logging
        self.metrics = LogMetrics()
        self.loggers: Dict[str, logging.Logger] = {}
        self.handlers: List[logging.Handler] = []
        self.configured = False
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        if self.configured:
            return
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set root level
        root_logger.setLevel(getattr(logging, self.settings.level.value))
        
        # Setup console handler
        if self.settings.log_to_console:
            console_handler = self._create_console_handler()
            root_logger.addHandler(console_handler)
            self.handlers.append(console_handler)
        
        # Setup file handler
        if self.settings.log_to_file and self.settings.log_file:
            file_handler = self._create_file_handler()
            root_logger.addHandler(file_handler)
            self.handlers.append(file_handler)
        
        # Setup metrics handler
        metrics_handler = MetricsHandler(self.metrics)
        root_logger.addHandler(metrics_handler)
        self.handlers.append(metrics_handler)
        
        # Add correlation ID filter to all handlers
        correlation_filter = CorrelationIdFilter()
        for handler in self.handlers:
            handler.addFilter(correlation_filter)
        
        # Add performance filter
        performance_filter = PerformanceFilter()
        for handler in self.handlers:
            handler.addFilter(performance_filter)
        
        self.configured = True
        
        # Log configuration
        logger = self.get_logger('logging_config')
        logger.info(f"Logging configured - Level: {self.settings.level.value}, "
                   f"Console: {self.settings.log_to_console}, "
                   f"File: {self.settings.log_to_file}")
    
    def _create_console_handler(self) -> logging.Handler:
        """Create console handler"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, self.settings.console_level.value))
        
        if self.settings.structured_logging:
            formatter = StructuredFormatter()
        else:
            formatter = ColoredFormatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(self) -> logging.Handler:
        """Create file handler with rotation"""
        # Ensure log directory exists
        log_file = Path(self.settings.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            filename=self.settings.log_file,
            maxBytes=self.settings.max_file_size,
            backupCount=self.settings.backup_count,
            encoding='utf-8'
        )
        
        handler.setLevel(getattr(logging, self.settings.level.value))
        
        # Always use structured logging for files
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        
        return handler
    
    def get_logger(self, name: str, component: Optional[str] = None) -> logging.Logger:
        """Get or create a logger with optional component context"""
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        
        # Add component context if provided
        if component:
            logger = logging.LoggerAdapter(logger, {'component': component})
        
        self.loggers[name] = logger
        return logger
    
    def set_correlation_id(self, corr_id: Optional[str] = None) -> str:
        """Set correlation ID for current context"""
        if corr_id is None:
            corr_id = str(uuid.uuid4())
        
        correlation_id.set(corr_id)
        return corr_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID"""
        return correlation_id.get()
    
    def clear_correlation_id(self):
        """Clear correlation ID"""
        correlation_id.set(None)
    
    def log_with_context(
        self,
        logger: logging.Logger,
        level: str,
        message: str,
        context: Optional[LogContext] = None,
        **kwargs
    ):
        """Log with additional context"""
        # Set correlation ID if provided in context
        if context and context.correlation_id:
            correlation_id.set(context.correlation_id)
        
        # Add context to extra fields
        extra = kwargs.copy()
        if context:
            context_dict = asdict(context)
            for key, value in context_dict.items():
                if value is not None:
                    extra[key] = value
        
        # Log the message
        getattr(logger, level.lower())(message, extra=extra)
    
    def log_performance(
        self,
        logger: logging.Logger,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **kwargs
    ):
        """Log performance metrics"""
        extra = {
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success,
            **kwargs
        }
        
        level = 'info' if success else 'warning'
        message = f"Operation '{operation}' completed in {duration_ms:.2f}ms"
        
        getattr(logger, level)(message, extra=extra)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics"""
        return self.metrics.get_metrics()
    
    def reset_metrics(self):
        """Reset logging metrics"""
        self.metrics.reset()
    
    def reconfigure(self, settings: LoggingSettings):
        """Reconfigure logging with new settings"""
        self.settings = settings
        
        # Remove existing handlers
        root_logger = logging.getLogger()
        for handler in self.handlers:
            root_logger.removeHandler(handler)
            handler.close()
        
        self.handlers.clear()
        self.configured = False
        
        # Setup with new configuration
        self.setup_logging()
    
    def close(self):
        """Close all handlers and cleanup"""
        for handler in self.handlers:
            handler.close()
        
        self.handlers.clear()
        self.loggers.clear()


# Global logger manager instance
_logger_manager: Optional[LoggerManager] = None


def get_logger_manager(settings: Optional[LoggingSettings] = None) -> LoggerManager:
    """Get or create the global logger manager instance"""
    global _logger_manager
    
    if _logger_manager is None:
        _logger_manager = LoggerManager(settings)
    
    return _logger_manager


def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """Get a logger instance"""
    return get_logger_manager().get_logger(name, component)


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """Set correlation ID for current context"""
    return get_logger_manager().set_correlation_id(corr_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return get_logger_manager().get_correlation_id()


def clear_correlation_id():
    """Clear correlation ID"""
    get_logger_manager().clear_correlation_id()


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    context: Optional[LogContext] = None,
    **kwargs
):
    """Log with additional context"""
    get_logger_manager().log_with_context(logger, level, message, context, **kwargs)


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **kwargs
):
    """Log performance metrics"""
    get_logger_manager().log_performance(logger, operation, duration_ms, success, **kwargs)


def get_logging_metrics() -> Dict[str, Any]:
    """Get logging metrics"""
    return get_logger_manager().get_metrics()


def close_logger_manager():
    """Close the global logger manager"""
    global _logger_manager
    
    if _logger_manager:
        _logger_manager.close()
        _logger_manager = None


# Context manager for correlation ID
class correlation_context:
    """Context manager for correlation ID"""
    
    def __init__(self, corr_id: Optional[str] = None):
        self.corr_id = corr_id
        self.previous_id = None
    
    def __enter__(self) -> str:
        self.previous_id = get_correlation_id()
        return set_correlation_id(self.corr_id)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_id:
            correlation_id.set(self.previous_id)
        else:
            clear_correlation_id()


# Context manager for performance logging
class performance_context:
    """Context manager for performance logging"""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.kwargs = kwargs
        self.start_time = None
        self.success = True
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None
            
            log_performance(
                self.logger,
                self.operation,
                duration_ms,
                self.success,
                **self.kwargs
            )
    
    def set_success(self, success: bool):
        """Manually set success status"""
        self.success = success

