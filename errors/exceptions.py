"""
Custom Exception Classes

This module defines all custom exceptions used throughout the application
with proper error codes, context information, and error handling.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes"""
    
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_TRANSACTION_ERROR = "DATABASE_TRANSACTION_ERROR"
    DATABASE_MIGRATION_ERROR = "DATABASE_MIGRATION_ERROR"
    DATABASE_INTEGRITY_ERROR = "DATABASE_INTEGRITY_ERROR"
    
    # API errors
    API_REQUEST_ERROR = "API_REQUEST_ERROR"
    API_RESPONSE_ERROR = "API_RESPONSE_ERROR"
    API_AUTHENTICATION_ERROR = "API_AUTHENTICATION_ERROR"
    API_RATE_LIMIT_ERROR = "API_RATE_LIMIT_ERROR"
    API_TIMEOUT_ERROR = "API_TIMEOUT_ERROR"
    
    # Service-specific errors
    CODEGEN_API_ERROR = "CODEGEN_API_ERROR"
    GITHUB_API_ERROR = "GITHUB_API_ERROR"
    CLOUDFLARE_API_ERROR = "CLOUDFLARE_API_ERROR"
    GEMINI_API_ERROR = "GEMINI_API_ERROR"
    
    # Agent and pipeline errors
    AGENT_RUN_ERROR = "AGENT_RUN_ERROR"
    PIPELINE_ERROR = "PIPELINE_ERROR"
    WEBHOOK_ERROR = "WEBHOOK_ERROR"
    GRAINCHAIN_ERROR = "GRAINCHAIN_ERROR"
    WEB_EVAL_AGENT_ERROR = "WEB_EVAL_AGENT_ERROR"
    
    # File and I/O errors
    FILE_NOT_FOUND_ERROR = "FILE_NOT_FOUND_ERROR"
    FILE_PERMISSION_ERROR = "FILE_PERMISSION_ERROR"
    FILE_FORMAT_ERROR = "FILE_FORMAT_ERROR"
    
    # Security errors
    ENCRYPTION_ERROR = "ENCRYPTION_ERROR"
    DECRYPTION_ERROR = "DECRYPTION_ERROR"
    TOKEN_INVALID_ERROR = "TOKEN_INVALID_ERROR"
    TOKEN_EXPIRED_ERROR = "TOKEN_EXPIRED_ERROR"
    SIGNATURE_INVALID_ERROR = "SIGNATURE_INVALID_ERROR"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaseApplicationError(Exception):
    """Base exception class for all application errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        self.user_message = user_message or message
        self.correlation_id = correlation_id
        self.timestamp = datetime.now()
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "context": self.context,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"
    
    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}("
                f"error_code={self.error_code.value}, "
                f"message='{self.message}', "
                f"severity={self.severity.value})")


# Configuration and Validation Errors
class ConfigurationError(BaseApplicationError):
    """Configuration-related error"""
    
    def __init__(
        self,
        message: str,
        config_field: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if config_field:
            context['config_field'] = config_field
        if config_value is not None:
            context['config_value'] = str(config_value)
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.CONFIGURATION_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        
        super().__init__(message, **kwargs)


class ValidationError(BaseApplicationError):
    """Data validation error"""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)
        if validation_errors:
            context['validation_errors'] = validation_errors
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.VALIDATION_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        
        super().__init__(message, **kwargs)


# Database Errors
class DatabaseError(BaseApplicationError):
    """Base database error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_code', ErrorCode.DATABASE_CONNECTION_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Database connection error"""
    
    def __init__(
        self,
        message: str,
        database_path: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if database_path:
            context['database_path'] = database_path
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.DATABASE_CONNECTION_ERROR)
        
        super().__init__(message, **kwargs)


class DatabaseQueryError(DatabaseError):
    """Database query error"""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        parameters: Optional[tuple] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if query:
            context['query'] = query
        if parameters:
            context['parameters'] = str(parameters)
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.DATABASE_QUERY_ERROR)
        
        super().__init__(message, **kwargs)


class DatabaseTransactionError(DatabaseError):
    """Database transaction error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_code', ErrorCode.DATABASE_TRANSACTION_ERROR)
        super().__init__(message, **kwargs)


class DatabaseMigrationError(DatabaseError):
    """Database migration error"""
    
    def __init__(
        self,
        message: str,
        migration_version: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if migration_version:
            context['migration_version'] = migration_version
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.DATABASE_MIGRATION_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        
        super().__init__(message, **kwargs)


# API Errors
class APIError(BaseApplicationError):
    """Base API error"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_url: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if status_code:
            context['status_code'] = status_code
        if response_data:
            context['response_data'] = response_data
        if request_url:
            context['request_url'] = request_url
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.API_REQUEST_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        
        super().__init__(message, **kwargs)


class APIAuthenticationError(APIError):
    """API authentication error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_code', ErrorCode.API_AUTHENTICATION_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class APIRateLimitError(APIError):
    """API rate limit error"""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if retry_after:
            context['retry_after'] = retry_after
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.API_RATE_LIMIT_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        
        super().__init__(message, **kwargs)


class APITimeoutError(APIError):
    """API timeout error"""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if timeout_seconds:
            context['timeout_seconds'] = timeout_seconds
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.API_TIMEOUT_ERROR)
        
        super().__init__(message, **kwargs)


# Service-Specific Errors
class CodegenAPIError(APIError):
    """Codegen API error"""
    
    def __init__(
        self,
        message: str,
        agent_run_id: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if agent_run_id:
            context['agent_run_id'] = agent_run_id
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.CODEGEN_API_ERROR)
        
        super().__init__(message, **kwargs)


class GitHubAPIError(APIError):
    """GitHub API error"""
    
    def __init__(
        self,
        message: str,
        repository: Optional[str] = None,
        pr_number: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if repository:
            context['repository'] = repository
        if pr_number:
            context['pr_number'] = pr_number
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.GITHUB_API_ERROR)
        
        super().__init__(message, **kwargs)


class CloudflareAPIError(APIError):
    """Cloudflare API error"""
    
    def __init__(
        self,
        message: str,
        worker_name: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if worker_name:
            context['worker_name'] = worker_name
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.CLOUDFLARE_API_ERROR)
        
        super().__init__(message, **kwargs)


class GeminiAPIError(APIError):
    """Gemini API error"""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if model:
            context['model'] = model
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.GEMINI_API_ERROR)
        
        super().__init__(message, **kwargs)


# Agent and Pipeline Errors
class AgentRunError(BaseApplicationError):
    """Agent run error"""
    
    def __init__(
        self,
        message: str,
        agent_run_id: Optional[int] = None,
        project_id: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if agent_run_id:
            context['agent_run_id'] = agent_run_id
        if project_id:
            context['project_id'] = project_id
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.AGENT_RUN_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        
        super().__init__(message, **kwargs)


class PipelineError(BaseApplicationError):
    """Pipeline execution error"""
    
    def __init__(
        self,
        message: str,
        pipeline_state: Optional[str] = None,
        agent_run_id: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if pipeline_state:
            context['pipeline_state'] = pipeline_state
        if agent_run_id:
            context['agent_run_id'] = agent_run_id
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.PIPELINE_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        
        super().__init__(message, **kwargs)


class WebhookError(BaseApplicationError):
    """Webhook processing error"""
    
    def __init__(
        self,
        message: str,
        webhook_type: Optional[str] = None,
        project_id: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if webhook_type:
            context['webhook_type'] = webhook_type
        if project_id:
            context['project_id'] = project_id
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.WEBHOOK_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        
        super().__init__(message, **kwargs)


class GrainchainError(BaseApplicationError):
    """Grainchain operation error"""
    
    def __init__(
        self,
        message: str,
        snapshot_id: Optional[str] = None,
        container_id: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if snapshot_id:
            context['snapshot_id'] = snapshot_id
        if container_id:
            context['container_id'] = container_id
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.GRAINCHAIN_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        
        super().__init__(message, **kwargs)


class WebEvalAgentError(BaseApplicationError):
    """Web-Eval-Agent error"""
    
    def __init__(
        self,
        message: str,
        test_name: Optional[str] = None,
        browser: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if test_name:
            context['test_name'] = test_name
        if browser:
            context['browser'] = browser
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.WEB_EVAL_AGENT_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        
        super().__init__(message, **kwargs)


# Security Errors
class SecurityError(BaseApplicationError):
    """Base security error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        super().__init__(message, **kwargs)


class AuthenticationError(SecurityError):
    """Authentication error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_code', ErrorCode.AUTHENTICATION_ERROR)
        super().__init__(message, **kwargs)


class AuthorizationError(SecurityError):
    """Authorization error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_code', ErrorCode.AUTHORIZATION_ERROR)
        super().__init__(message, **kwargs)


class TokenError(SecurityError):
    """Token-related error"""
    
    def __init__(
        self,
        message: str,
        token_type: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if token_type:
            context['token_type'] = token_type
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.TOKEN_INVALID_ERROR)
        
        super().__init__(message, **kwargs)


class EncryptionError(SecurityError):
    """Encryption/decryption error"""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_code', ErrorCode.ENCRYPTION_ERROR)
        super().__init__(message, **kwargs)


# File and I/O Errors
class FileError(BaseApplicationError):
    """File operation error"""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if file_path:
            context['file_path'] = file_path
        
        kwargs['context'] = context
        kwargs.setdefault('error_code', ErrorCode.FILE_NOT_FOUND_ERROR)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        
        super().__init__(message, **kwargs)


# Utility functions for error handling
def create_error_response(error: BaseApplicationError) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": True,
        "error_code": error.error_code.value,
        "message": error.user_message,
        "severity": error.severity.value,
        "timestamp": error.timestamp.isoformat(),
        "correlation_id": error.correlation_id,
        "context": error.context
    }


def wrap_exception(
    exc: Exception,
    message: Optional[str] = None,
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    **kwargs
) -> BaseApplicationError:
    """Wrap a generic exception in a BaseApplicationError"""
    if isinstance(exc, BaseApplicationError):
        return exc
    
    error_message = message or str(exc)
    
    return BaseApplicationError(
        message=error_message,
        error_code=error_code,
        cause=exc,
        **kwargs
    )


def get_error_severity(error_code: ErrorCode) -> ErrorSeverity:
    """Get default severity for an error code"""
    critical_errors = {
        ErrorCode.DATABASE_MIGRATION_ERROR,
        ErrorCode.AUTHENTICATION_ERROR,
        ErrorCode.AUTHORIZATION_ERROR,
        ErrorCode.ENCRYPTION_ERROR,
        ErrorCode.DECRYPTION_ERROR
    }
    
    high_errors = {
        ErrorCode.DATABASE_CONNECTION_ERROR,
        ErrorCode.DATABASE_TRANSACTION_ERROR,
        ErrorCode.AGENT_RUN_ERROR,
        ErrorCode.PIPELINE_ERROR,
        ErrorCode.GRAINCHAIN_ERROR
    }
    
    if error_code in critical_errors:
        return ErrorSeverity.CRITICAL
    elif error_code in high_errors:
        return ErrorSeverity.HIGH
    else:
        return ErrorSeverity.MEDIUM

