"""
Custom Logging Filters

This module provides custom logging filters for advanced log processing,
filtering, and enrichment with contextual information.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Pattern, Set
from datetime import datetime

from logging_config.logger import get_correlation_id


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log messages"""
    
    def __init__(self):
        super().__init__()
        
        # Patterns for sensitive data
        self.patterns = [
            # API tokens and keys
            (re.compile(r'sk-[a-zA-Z0-9]{32,}'), '[REDACTED_API_TOKEN]'),
            (re.compile(r'ghp_[a-zA-Z0-9]{36}'), '[REDACTED_GITHUB_TOKEN]'),
            (re.compile(r'github_pat_[a-zA-Z0-9_]{82}'), '[REDACTED_GITHUB_PAT]'),
            (re.compile(r'AIzaSy[a-zA-Z0-9_-]{33}'), '[REDACTED_GEMINI_KEY]'),
            
            # Generic API keys
            (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})["\']?', re.IGNORECASE), 
             r'api_key: [REDACTED_API_KEY]'),
            (re.compile(r'secret[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})["\']?', re.IGNORECASE), 
             r'secret_key: [REDACTED_SECRET_KEY]'),
            (re.compile(r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})["\']?', re.IGNORECASE), 
             r'token: [REDACTED_TOKEN]'),
            
            # Passwords
            (re.compile(r'password["\']?\s*[:=]\s*["\']?([^\s"\']{8,})["\']?', re.IGNORECASE), 
             r'password: [REDACTED_PASSWORD]'),
            (re.compile(r'passwd["\']?\s*[:=]\s*["\']?([^\s"\']{8,})["\']?', re.IGNORECASE), 
             r'passwd: [REDACTED_PASSWORD]'),
            
            # Email addresses (partial redaction)
            (re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'), 
             r'\1***@\2'),
            
            # Credit card numbers
            (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), 
             '[REDACTED_CREDIT_CARD]'),
            
            # Social Security Numbers
            (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[REDACTED_SSN]'),
            
            # IP addresses (partial redaction)
            (re.compile(r'\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b'), 
             r'\1.\2.***.\4'),
        ]
    
    def filter(self, record):
        """Filter sensitive data from log record"""
        # Redact message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._redact_sensitive_data(record.msg)
        
        # Redact args if present
        if hasattr(record, 'args') and record.args:
            redacted_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    redacted_args.append(self._redact_sensitive_data(arg))
                else:
                    redacted_args.append(arg)
            record.args = tuple(redacted_args)
        
        # Redact extra fields
        for key, value in record.__dict__.items():
            if isinstance(value, str) and key not in ['name', 'levelname', 'pathname', 'filename', 'module', 'funcName']:
                setattr(record, key, self._redact_sensitive_data(value))
        
        return True
    
    def _redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from text"""
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text


class ComponentFilter(logging.Filter):
    """Filter logs by component"""
    
    def __init__(self, allowed_components: Optional[Set[str]] = None, 
                 blocked_components: Optional[Set[str]] = None):
        super().__init__()
        self.allowed_components = allowed_components
        self.blocked_components = blocked_components or set()
    
    def filter(self, record):
        """Filter by component"""
        component = getattr(record, 'component', None)
        
        # If no component specified, allow by default
        if not component:
            return True
        
        # Check blocked components first
        if component in self.blocked_components:
            return False
        
        # Check allowed components
        if self.allowed_components:
            return component in self.allowed_components
        
        return True


class LevelRangeFilter(logging.Filter):
    """Filter logs by level range"""
    
    def __init__(self, min_level: int = logging.DEBUG, max_level: int = logging.CRITICAL):
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level
    
    def filter(self, record):
        """Filter by level range"""
        return self.min_level <= record.levelno <= self.max_level


class RateLimitFilter(logging.Filter):
    """Rate limit filter to prevent log spam"""
    
    def __init__(self, max_logs_per_minute: int = 100):
        super().__init__()
        self.max_logs_per_minute = max_logs_per_minute
        self.log_times: List[float] = []
    
    def filter(self, record):
        """Rate limit logs"""
        now = time.time()
        
        # Remove logs older than 1 minute
        cutoff = now - 60
        self.log_times = [t for t in self.log_times if t > cutoff]
        
        # Check if we're over the limit
        if len(self.log_times) >= self.max_logs_per_minute:
            return False
        
        # Add current log time
        self.log_times.append(now)
        return True


class DuplicateFilter(logging.Filter):
    """Filter to suppress duplicate log messages"""
    
    def __init__(self, max_duplicates: int = 5, time_window: int = 60):
        super().__init__()
        self.max_duplicates = max_duplicates
        self.time_window = time_window
        self.message_counts: Dict[str, List[float]] = {}
    
    def filter(self, record):
        """Filter duplicate messages"""
        message_key = f"{record.levelname}:{record.getMessage()}"
        now = time.time()
        
        # Initialize or clean up old entries
        if message_key not in self.message_counts:
            self.message_counts[message_key] = []
        
        # Remove old timestamps
        cutoff = now - self.time_window
        self.message_counts[message_key] = [
            t for t in self.message_counts[message_key] if t > cutoff
        ]
        
        # Check if we've exceeded the duplicate limit
        if len(self.message_counts[message_key]) >= self.max_duplicates:
            return False
        
        # Add current timestamp
        self.message_counts[message_key].append(now)
        return True


class PerformanceFilter(logging.Filter):
    """Filter to add performance context to logs"""
    
    def __init__(self):
        super().__init__()
        self.operation_start_times: Dict[str, float] = {}
    
    def filter(self, record):
        """Add performance context"""
        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        
        # Add performance timing if operation is specified
        operation = getattr(record, 'operation', None)
        if operation:
            if hasattr(record, 'operation_start'):
                # Calculate duration
                duration = time.time() - record.operation_start
                record.duration_ms = round(duration * 1000, 2)
            elif operation in self.operation_start_times:
                # Use stored start time
                duration = time.time() - self.operation_start_times[operation]
                record.duration_ms = round(duration * 1000, 2)
                del self.operation_start_times[operation]
        
        return True
    
    def start_operation(self, operation: str):
        """Start timing an operation"""
        self.operation_start_times[operation] = time.time()


class ContextEnrichmentFilter(logging.Filter):
    """Filter to enrich logs with contextual information"""
    
    def __init__(self):
        super().__init__()
        self.context_providers: List[callable] = []
    
    def filter(self, record):
        """Enrich log record with context"""
        # Add timestamp in ISO format
        record.iso_timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        # Add thread information
        record.thread_name = getattr(record, 'threadName', 'unknown')
        
        # Add process information
        record.process_name = getattr(record, 'processName', 'unknown')
        
        # Add correlation ID if not present
        if not hasattr(record, 'correlation_id'):
            correlation_id = get_correlation_id()
            record.correlation_id = correlation_id or 'unknown'
        
        # Run custom context providers
        for provider in self.context_providers:
            try:
                context = provider()
                if isinstance(context, dict):
                    for key, value in context.items():
                        if not hasattr(record, key):
                            setattr(record, key, value)
            except Exception:
                # Ignore errors in context providers
                pass
        
        return True
    
    def add_context_provider(self, provider: callable):
        """Add a context provider function"""
        self.context_providers.append(provider)


class ErrorOnlyFilter(logging.Filter):
    """Filter to only allow error and critical logs"""
    
    def filter(self, record):
        """Only allow ERROR and CRITICAL levels"""
        return record.levelno >= logging.ERROR


class DebugOnlyFilter(logging.Filter):
    """Filter to only allow debug logs"""
    
    def filter(self, record):
        """Only allow DEBUG level"""
        return record.levelno == logging.DEBUG


class RegexFilter(logging.Filter):
    """Filter logs based on regex patterns"""
    
    def __init__(self, include_patterns: Optional[List[str]] = None, 
                 exclude_patterns: Optional[List[str]] = None):
        super().__init__()
        
        self.include_patterns = [
            re.compile(pattern) for pattern in (include_patterns or [])
        ]
        self.exclude_patterns = [
            re.compile(pattern) for pattern in (exclude_patterns or [])
        ]
    
    def filter(self, record):
        """Filter based on regex patterns"""
        message = record.getMessage()
        
        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if pattern.search(message):
                return False
        
        # Check include patterns
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern.search(message):
                    return True
            return False
        
        return True


class SamplingFilter(logging.Filter):
    """Filter to sample logs (only keep every Nth log)"""
    
    def __init__(self, sample_rate: int = 10):
        super().__init__()
        self.sample_rate = sample_rate
        self.counter = 0
    
    def filter(self, record):
        """Sample logs"""
        self.counter += 1
        return self.counter % self.sample_rate == 0


class HealthCheckFilter(logging.Filter):
    """Filter to suppress health check logs"""
    
    def __init__(self):
        super().__init__()
        self.health_check_patterns = [
            re.compile(r'/health', re.IGNORECASE),
            re.compile(r'/ping', re.IGNORECASE),
            re.compile(r'/status', re.IGNORECASE),
            re.compile(r'health.?check', re.IGNORECASE),
        ]
    
    def filter(self, record):
        """Filter out health check logs"""
        message = record.getMessage()
        
        for pattern in self.health_check_patterns:
            if pattern.search(message):
                return False
        
        return True


class StructuredDataFilter(logging.Filter):
    """Filter to ensure structured data is properly formatted"""
    
    def filter(self, record):
        """Ensure structured data is properly formatted"""
        # Ensure extra fields are JSON serializable
        for key, value in record.__dict__.items():
            if key.startswith('_'):
                continue
                
            try:
                import json
                json.dumps(value, default=str)
            except (TypeError, ValueError):
                # Replace non-serializable values with string representation
                setattr(record, key, str(value))
        
        return True


# Factory functions for common filter combinations
def create_production_filters() -> List[logging.Filter]:
    """Create filters suitable for production"""
    return [
        SensitiveDataFilter(),
        RateLimitFilter(max_logs_per_minute=200),
        DuplicateFilter(max_duplicates=3, time_window=300),
        HealthCheckFilter(),
        ContextEnrichmentFilter(),
        StructuredDataFilter()
    ]


def create_development_filters() -> List[logging.Filter]:
    """Create filters suitable for development"""
    return [
        SensitiveDataFilter(),
        ContextEnrichmentFilter(),
        PerformanceFilter()
    ]


def create_debug_filters() -> List[logging.Filter]:
    """Create filters suitable for debugging"""
    return [
        ContextEnrichmentFilter(),
        PerformanceFilter()
    ]


def create_error_only_filters() -> List[logging.Filter]:
    """Create filters for error-only logging"""
    return [
        ErrorOnlyFilter(),
        SensitiveDataFilter(),
        ContextEnrichmentFilter(),
        StructuredDataFilter()
    ]

