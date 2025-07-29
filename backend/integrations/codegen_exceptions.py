"""
Codegen API client exceptions
"""
from typing import Optional, Dict, List


class ValidationError(Exception):
    """Validation error for request parameters"""

    def __init__(
        self, message: str, field_errors: Optional[Dict[str, List[str]]] = None
    ):
        self.message = message
        self.field_errors = field_errors or {}
        super().__init__(message)


class CodegenAPIError(Exception):
    """Base exception for Codegen API errors"""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response_data: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.request_id = request_id
        super().__init__(message)


class RateLimitError(CodegenAPIError):
    """Rate limiting error with retry information"""

    def __init__(self, retry_after: int = 60, request_id: Optional[str] = None):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited. Retry after {retry_after} seconds",
            429,
            request_id=request_id,
        )


class AuthenticationError(CodegenAPIError):
    """Authentication/authorization error"""

    def __init__(
        self, message: str = "Authentication failed", request_id: Optional[str] = None
    ):
        super().__init__(message, 401, request_id=request_id)


class NotFoundError(CodegenAPIError):
    """Resource not found error"""

    def __init__(
        self, message: str = "Resource not found", request_id: Optional[str] = None
    ):
        super().__init__(message, 404, request_id=request_id)


class ConflictError(CodegenAPIError):
    """Conflict error (409)"""

    def __init__(
        self, message: str = "Conflict occurred", request_id: Optional[str] = None
    ):
        super().__init__(message, 409, request_id=request_id)


class ServerError(CodegenAPIError):
    """Server-side error (5xx)"""

    def __init__(
        self,
        message: str = "Server error occurred",
        status_code: int = 500,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, status_code, request_id=request_id)


class TimeoutError(CodegenAPIError):
    """Request timeout error"""

    def __init__(
        self, message: str = "Request timed out", request_id: Optional[str] = None
    ):
        super().__init__(message, 408, request_id=request_id)


class NetworkError(CodegenAPIError):
    """Network connectivity error"""

    def __init__(
        self, message: str = "Network error occurred", request_id: Optional[str] = None
    ):
        super().__init__(message, 0, request_id=request_id)


class WebhookError(Exception):
    """Webhook processing error"""

    pass


class BulkOperationError(Exception):
    """Bulk operation error"""

    def __init__(self, message: str, failed_items: Optional[List] = None):
        self.failed_items = failed_items or []
        super().__init__(message)

