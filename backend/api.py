"""
Enhanced Codegen API Client with comprehensive features

This module provides a complete Python SDK for interacting with the Codegen API,
including both synchronous and asynchronous clients with advanced features like
caching, rate limiting, bulk operations, webhooks, and streaming support.
"""

# ============================================================================
# STANDARD LIBRARY IMPORTS
# ============================================================================
import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import lru_cache, wraps
from threading import Lock
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)

# ============================================================================
# THIRD-PARTY IMPORTS
# ============================================================================
import requests
from requests import exceptions as requests_exceptions

# Optional async HTTP client
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================
class SourceType(Enum):
    """Source types for agent runs"""
    LOCAL = "LOCAL"
    SLACK = "SLACK"
    GITHUB = "GITHUB"
    GITHUB_CHECK_SUITE = "GITHUB_CHECK_SUITE"
    LINEAR = "LINEAR"
    API = "API"
    CHAT = "CHAT"
    JIRA = "JIRA"


class MessageType(Enum):
    """Message types for agent run logs"""
    ACTION = "ACTION"
    PLAN_EVALUATION = "PLAN_EVALUATION"
    FINAL_ANSWER = "FINAL_ANSWER"
    ERROR = "ERROR"
    USER_MESSAGE = "USER_MESSAGE"
    USER_GITHUB_ISSUE_COMMENT = "USER_GITHUB_ISSUE_COMMENT"
    INITIAL_PR_GENERATION = "INITIAL_PR_GENERATION"
    DETECT_PR_ERRORS = "DETECT_PR_ERRORS"
    FIX_PR_ERRORS = "FIX_PR_ERRORS"
    PR_CREATION_FAILED = "PR_CREATION_FAILED"
    PR_EVALUATION = "PR_EVALUATION"
    COMMIT_EVALUATION = "COMMIT_EVALUATION"
    AGENT_RUN_LINK = "AGENT_RUN_LINK"


class AgentRunStatus(Enum):
    """Agent run status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============================================================================
# EXCEPTIONS
# ============================================================================
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


# ============================================================================
# DATA MODELS
# ============================================================================
@dataclass
class UserResponse:
    """User response model"""
    id: int
    email: Optional[str]
    github_user_id: str
    github_username: str
    avatar_url: Optional[str]
    full_name: Optional[str]


@dataclass
class GithubPullRequestResponse:
    """GitHub pull request response model"""
    id: int
    title: str
    url: str
    created_at: str


@dataclass
class AgentRunResponse:
    """Agent run response model"""
    id: int
    organization_id: int
    status: Optional[str]
    created_at: Optional[str]
    web_url: Optional[str]
    result: Optional[str]
    source_type: Optional[SourceType]
    github_pull_requests: Optional[List[GithubPullRequestResponse]]
    metadata: Optional[Dict[str, Any]]


@dataclass
class AgentRunLogResponse:
    """Agent run log response model"""
    agent_run_id: int
    created_at: str
    message_type: str
    thought: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    observation: Optional[Union[Dict[str, Any], str]] = None


@dataclass
class OrganizationSettings:
    """Organization settings model"""
    # Add specific settings fields as they become available
    pass


@dataclass
class OrganizationResponse:
    """Organization response model"""
    id: int
    name: str
    settings: OrganizationSettings


@dataclass
class PaginatedResponse:
    """Base paginated response model"""
    total: int
    page: int
    size: int
    pages: int


@dataclass
class UsersResponse(PaginatedResponse):
    """Paginated users response"""
    items: List[UserResponse]


@dataclass
class AgentRunsResponse(PaginatedResponse):
    """Paginated agent runs response"""
    items: List[AgentRunResponse]


@dataclass
class OrganizationsResponse(PaginatedResponse):
    """Paginated organizations response"""
    items: List[OrganizationResponse]


@dataclass
class AgentRunWithLogsResponse:
    """Agent run with logs response model"""
    id: int
    organization_id: int
    logs: List[AgentRunLogResponse]
    status: Optional[str]
    created_at: Optional[str]
    web_url: Optional[str]
    result: Optional[str]
    metadata: Optional[Dict[str, Any]]
    total_logs: Optional[int]
    page: Optional[int]
    size: Optional[int]
    pages: Optional[int]


@dataclass
class WebhookEvent:
    """Webhook event payload"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    signature: Optional[str] = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    total_items: int
    successful_items: int
    failed_items: int
    success_rate: float
    duration_seconds: float
    errors: List[Dict[str, Any]]
    results: List[Any]


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    method: str
    endpoint: str
    status_code: int
    duration_seconds: float
    timestamp: datetime
    request_id: str
    cached: bool = False


@dataclass
class ClientStats:
    """Comprehensive client statistics"""
    uptime_seconds: float
    total_requests: int
    total_errors: int
    error_rate: float
    requests_per_minute: float
    average_response_time: float
    cache_hit_rate: float
    status_code_distribution: Dict[int, int]
    recent_requests: List[RequestMetrics]


# ============================================================================
# CONFIGURATION
# ============================================================================
@dataclass
class ClientConfig:
    """Configuration for the Codegen client"""

    # Core settings
    api_token: str = field(default_factory=lambda: os.getenv("CODEGEN_API_TOKEN", ""))
    org_id: str = field(default_factory=lambda: os.getenv("CODEGEN_ORG_ID", ""))
    base_url: str = field(
        default_factory=lambda: os.getenv(
            "CODEGEN_BASE_URL", "https://api.codegen.com/v1"
        )
    )

    # Performance settings
    timeout: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_TIMEOUT", "30"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_MAX_RETRIES", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RETRY_DELAY", "1.0"))
    )
    retry_backoff_factor: float = field(
        default_factory=lambda: float(os.getenv("CODEGEN_RETRY_BACKOFF", "2.0"))
    )

    # Rate limiting
    rate_limit_requests_per_period: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_REQUESTS", "60"))
    )
    rate_limit_period_seconds: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_PERIOD", "60"))
    )
    rate_limit_buffer: float = 0.1

    # Caching
    enable_caching: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_CACHING", "true").lower()
        == "true"
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_CACHE_TTL", "300"))
    )
    cache_max_size: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_CACHE_MAX_SIZE", "128"))
    )

    # Features
    enable_webhooks: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_WEBHOOKS", "true").lower()
        == "true"
    )
    enable_bulk_operations: bool = field(
        default_factory=lambda: os.getenv(
            "CODEGEN_ENABLE_BULK_OPERATIONS", "true"
        ).lower()
        == "true"
    )
    enable_streaming: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_STREAMING", "true").lower()
        == "true"
    )
    enable_metrics: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_ENABLE_METRICS", "true").lower()
        == "true"
    )

    # Bulk operations
    bulk_max_workers: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_BULK_MAX_WORKERS", "5"))
    )
    bulk_batch_size: int = field(
        default_factory=lambda: int(os.getenv("CODEGEN_BULK_BATCH_SIZE", "100"))
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_LEVEL", "INFO")
    )
    log_requests: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_REQUESTS", "true").lower()
        == "true"
    )
    log_responses: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_RESPONSES", "false").lower()
        == "true"
    )
    log_request_bodies: bool = field(
        default_factory=lambda: os.getenv("CODEGEN_LOG_REQUEST_BODIES", "false").lower()
        == "true"
    )

    # Webhook settings
    webhook_secret: Optional[str] = field(
        default_factory=lambda: os.getenv("CODEGEN_WEBHOOK_SECRET")
    )

    # User agent
    user_agent: str = field(default_factory=lambda: "codegen-python-client/2.0.0")

    def __post_init__(self):
        if not self.api_token:
            raise ValueError(
                "API token is required. Set CODEGEN_API_TOKEN environment variable or provide it directly."
            )

        # Set up logging
        logging.basicConfig(level=getattr(logging, self.log_level.upper()))


class ConfigPresets:
    """Predefined configuration presets"""

    @staticmethod
    def development() -> ClientConfig:
        """Development configuration with verbose logging and lower limits"""
        return ClientConfig(
            timeout=60,
            max_retries=1,
            rate_limit_requests_per_period=30,
            cache_ttl_seconds=60,
            log_level="DEBUG",
            log_requests=True,
            log_responses=True,
            log_request_bodies=True,
        )

    @staticmethod
    def production() -> ClientConfig:
        """Production configuration with optimized settings"""
        return ClientConfig(
            timeout=30,
            max_retries=3,
            rate_limit_requests_per_period=100,
            cache_ttl_seconds=300,
            log_level="INFO",
            log_requests=True,
            log_responses=False,
            log_request_bodies=False,
        )

    @staticmethod
    def high_performance() -> ClientConfig:
        """High performance configuration for heavy workloads"""
        return ClientConfig(
            timeout=45,
            max_retries=5,
            rate_limit_requests_per_period=200,
            cache_ttl_seconds=600,
            cache_max_size=256,
            bulk_max_workers=10,
            bulk_batch_size=200,
            log_level="WARNING",
        )

    @staticmethod
    def testing() -> ClientConfig:
        """Testing configuration with minimal caching and retries"""
        return ClientConfig(
            timeout=10,
            max_retries=1,
            enable_caching=False,
            rate_limit_requests_per_period=10,
            log_level="DEBUG",
        )


# ============================================================================
# UTILITY CLASSES
# ============================================================================
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


# ============================================================================
# MAIN CLIENT CLASSES
# ============================================================================
class CodegenClient:
    """Enhanced synchronous Codegen API client with comprehensive features"""

    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.headers = {
            "Authorization": f"Bearer {self.config.api_token}",
            "User-Agent": self.config.user_agent,
            "Content-Type": "application/json",
        }

        # Initialize components
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Rate limiting
        self.rate_limiter = RateLimiter(
            self.config.rate_limit_requests_per_period,
            self.config.rate_limit_period_seconds,
        )

        # Caching
        self.cache = (
            CacheManager(
                max_size=self.config.cache_max_size,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            if self.config.enable_caching
            else None
        )

        logger.info(f"Initialized CodegenClient with base URL: {self.config.base_url}")

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return str(uuid.uuid4())

    def _validate_pagination(self, skip: int, limit: int):
        """Validate pagination parameters"""
        if skip < 0:
            raise ValidationError("skip must be >= 0")
        if not (1 <= limit <= 100):
            raise ValidationError("limit must be between 1 and 100")

    def _handle_response(
        self, response: requests.Response, request_id: str
    ) -> Dict[str, Any]:
        """Handle HTTP response with comprehensive error handling"""
        status_code: int = response.status_code

        if status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            raise RateLimitError(retry_after, request_id)

        if status_code == 401:
            raise AuthenticationError(
                "Invalid API token or insufficient permissions", request_id
            )
        elif status_code == 404:
            raise NotFoundError("Requested resource not found", request_id)
        elif status_code == 409:
            raise ConflictError("Resource conflict occurred", request_id)
        elif status_code >= 500:
            raise ServerError(
                f"Server error: {status_code}",
                status_code,
                request_id,
            )
        elif not response.ok:
            try:
                error_data = response.json()
                message = error_data.get(
                    "message", f"API request failed: {status_code}"
                )
            except Exception:
                message = f"API request failed: {status_code}"
                error_data = None
            raise CodegenAPIError(
                message,
                status_code,
                error_data,
                request_id,
            )

        return response.json()

    def _make_request(
        self, method: str, endpoint: str, use_cache: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting, caching, and metrics"""
        request_id = self._generate_request_id()

        # Rate limiting
        self.rate_limiter.wait_if_needed()

        # Check cache
        cache_key = None
        if use_cache and self.cache and method.upper() == "GET":
            cache_key = f"{method}:{endpoint}:{hash(str(kwargs))}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {endpoint} (request_id: {request_id})")
                return cached_result

        # Make request with retry logic
        @retry_with_backoff(
            max_retries=self.config.max_retries,
            backoff_factor=self.config.retry_backoff_factor,
            base_delay=self.config.retry_delay,
        )
        def _execute_request():
            start_time = time.time()
            url = f"{self.config.base_url}{endpoint}"

            if self.config.log_requests:
                logger.info(
                    f"Making {method} request to {endpoint} (request_id: {request_id})"
                )

            try:
                response = self.session.request(
                    method, url, timeout=self.config.timeout, **kwargs
                )
                duration = time.time() - start_time

                if self.config.log_requests:
                    logger.info(
                        f"Request completed in {duration:.2f}s - Status: {response.status_code} (request_id: {request_id})"
                    )

                result = self._handle_response(response, request_id)

                # Cache successful GET requests
                if cache_key and response.ok:
                    self.cache.set(cache_key, result)

                return result

            except requests_exceptions.Timeout:
                raise TimeoutError(
                    f"Request timed out after {self.config.timeout}s", request_id
                )
            except requests_exceptions.ConnectionError as e:
                raise NetworkError(f"Network error: {str(e)}", request_id)

        return _execute_request()

    # ========================================================================
    # USER ENDPOINTS
    # ========================================================================
    def get_users(self, org_id: str, skip: int = 0, limit: int = 100) -> UsersResponse:
        """Get paginated list of users for a specific organization"""
        self._validate_pagination(skip, limit)

        response = self._make_request(
            "GET",
            f"/organizations/{org_id}/users",
            params={"skip": skip, "limit": limit},
            use_cache=True,
        )

        return UsersResponse(
            items=[
                UserResponse(
                    id=user.get("id", 0),
                    email=user.get("email"),
                    github_user_id=user.get("github_user_id", ""),
                    github_username=user.get("github_username", ""),
                    avatar_url=user.get("avatar_url"),
                    full_name=user.get("full_name"),
                )
                for user in response["items"]
                if user.get("id")
                and user.get("github_user_id")
                and user.get("github_username")
            ],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"],
        )

    def get_current_user(self) -> UserResponse:
        """Get current user information from API token"""
        response = self._make_request("GET", "/users/me", use_cache=True)
        return UserResponse(
            id=response.get("id", 0),
            email=response.get("email"),
            github_user_id=response.get("github_user_id", ""),
            github_username=response.get("github_username", ""),
            avatar_url=response.get("avatar_url"),
            full_name=response.get("full_name"),
        )

    # ========================================================================
    # AGENT ENDPOINTS
    # ========================================================================
    def create_agent_run(
        self,
        org_id: int,
        prompt: str,
        images: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentRunResponse:
        """Create a new agent run"""
        # Validate inputs
        if not prompt or len(prompt.strip()) == 0:
            raise ValidationError("Prompt cannot be empty")
        if len(prompt) > 50000:  # Reasonable limit
            raise ValidationError("Prompt cannot exceed 50,000 characters")
        if images and len(images) > 10:
            raise ValidationError("Cannot include more than 10 images")

        data = {"prompt": prompt, "images": images, "metadata": metadata}

        response = self._make_request(
            "POST", f"/organizations/{org_id}/agent/run", json=data
        )

        return self._parse_agent_run_response(response)

    def get_agent_run(self, org_id: int, agent_run_id: int) -> AgentRunResponse:
        """Retrieve the status and result of an agent run"""
        response = self._make_request(
            "GET", f"/organizations/{org_id}/agent/run/{agent_run_id}", use_cache=True
        )
        return self._parse_agent_run_response(response)

    def _parse_agent_run_response(self, data: Dict[str, Any]) -> AgentRunResponse:
        """Parse agent run response data into AgentRunResponse object"""
        return AgentRunResponse(
            id=data["id"],
            organization_id=data["organization_id"],
            status=data.get("status"),
            created_at=data.get("created_at"),
            web_url=data.get("web_url"),
            result=data.get("result"),
            source_type=SourceType(data["source_type"])
            if data.get("source_type")
            else None,
            github_pull_requests=[
                GithubPullRequestResponse(
                    id=pr.get("id", 0),
                    title=pr.get("title", ""),
                    url=pr.get("url", ""),
                    created_at=pr.get("created_at", ""),
                )
                for pr in data.get("github_pull_requests", [])
                if all(key in pr for key in ["id", "title", "url", "created_at"])
            ],
            metadata=data.get("metadata"),
        )

    def wait_for_completion(
        self,
        org_id: int,
        agent_run_id: int,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
    ) -> AgentRunResponse:
        """Wait for an agent run to complete with polling"""
        start_time = time.time()

        while True:
            run = self.get_agent_run(org_id, agent_run_id)

            if run.status in [
                AgentRunStatus.COMPLETED.value,
                AgentRunStatus.FAILED.value,
                AgentRunStatus.CANCELLED.value,
            ]:
                return run

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"Agent run {agent_run_id} did not complete within {timeout} seconds"
                )

            time.sleep(poll_interval)

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the API"""
        try:
            start_time = time.time()
            user = self.get_current_user()
            duration = time.time() - start_time

            return {
                "status": "healthy",
                "response_time_seconds": duration,
                "user_id": user.id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
        logger.info("Client closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# ASYNC CLIENT
# ============================================================================
if AIOHTTP_AVAILABLE:

    class AsyncCodegenClient:
        """Enhanced asynchronous Codegen API client"""

        def __init__(self, config: Optional[ClientConfig] = None):
            self.config = config or ClientConfig()
            self.session: Optional[aiohttp.ClientSession] = None
            self.rate_limiter = RateLimiter(
                self.config.rate_limit_requests_per_period,
                self.config.rate_limit_period_seconds,
            )
            self.cache = (
                CacheManager(
                    max_size=self.config.cache_max_size,
                    ttl_seconds=self.config.cache_ttl_seconds,
                )
                if self.config.enable_caching
                else None
            )

            logger.info(
                f"Initialized AsyncCodegenClient with base URL: {self.config.base_url}"
            )

        async def __aenter__(self):
            """Async context manager entry"""
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.config.api_token}",
                    "User-Agent": self.config.user_agent,
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            )
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Async context manager exit"""
            if self.session:
                await self.session.close()

        async def create_agent_run(
            self,
            org_id: int,
            prompt: str,
            images: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> AgentRunResponse:
            """Create a new agent run asynchronously"""
            if not self.session:
                raise RuntimeError(
                    "Client not initialized. Use 'async with' context manager."
                )

            if not prompt or len(prompt.strip()) == 0:
                raise ValidationError("Prompt cannot be empty")

            data = {"prompt": prompt, "images": images, "metadata": metadata}
            url = f"{self.config.base_url}/organizations/{org_id}/agent/run"

            async with self.session.post(url, json=data) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(retry_after)
                elif response.status == 401:
                    raise AuthenticationError("Invalid API token")
                elif response.status >= 400:
                    raise CodegenAPIError(f"Request failed: {response.status}")

                result = await response.json()
                return AgentRunResponse(
                    id=result["id"],
                    organization_id=result["organization_id"],
                    status=result.get("status"),
                    created_at=result.get("created_at"),
                    web_url=result.get("web_url"),
                    result=result.get("result"),
                    source_type=SourceType(result["source_type"])
                    if result.get("source_type")
                    else None,
                    github_pull_requests=[],
                    metadata=result.get("metadata"),
                )

        async def get_agent_run(
            self, org_id: int, agent_run_id: int
        ) -> AgentRunResponse:
            """Get agent run status asynchronously"""
            if not self.session:
                raise RuntimeError(
                    "Client not initialized. Use 'async with' context manager."
                )

            url = f"{self.config.base_url}/organizations/{org_id}/agent/run/{agent_run_id}"

            async with self.session.get(url) as response:
                if response.status >= 400:
                    raise CodegenAPIError(f"Request failed: {response.status}")

                result = await response.json()
                return AgentRunResponse(
                    id=result["id"],
                    organization_id=result["organization_id"],
                    status=result.get("status"),
                    created_at=result.get("created_at"),
                    web_url=result.get("web_url"),
                    result=result.get("result"),
                    source_type=SourceType(result["source_type"])
                    if result.get("source_type")
                    else None,
                    github_pull_requests=[],
                    metadata=result.get("metadata"),
                )


# ============================================================================
# USAGE EXAMPLES
# ============================================================================
def main():
    """Example usage of the enhanced Codegen client"""
    
    # Example 1: Basic usage with default configuration
    print("=== Basic Usage ===")
    with CodegenClient() as client:
        try:
            # Health check
            health = client.health_check()
            print(f"Health check: {health['status']}")

            # Get current user
            user = client.get_current_user()
            print(f"Current user: {user.github_username}")

        except Exception as e:
            print(f"Error: {e}")

    # Example 2: Using configuration presets
    print("\n=== Using Configuration Presets ===")
    dev_config = ConfigPresets.development()
    with CodegenClient(dev_config) as client:
        try:
            user = client.get_current_user()
            print(f"Development client - User: {user.github_username}")
        except Exception as e:
            print(f"Error: {e}")

    # Example 3: Async usage
    if AIOHTTP_AVAILABLE:
        print("\n=== Async Usage ===")

        async def async_example():
            async with AsyncCodegenClient() as client:
                try:
                    # Example async agent run creation
                    run = await client.create_agent_run(
                        org_id=323,
                        prompt="Create a simple Python function",
                        metadata={"source": "api_example"}
                    )
                    print(f"Created async agent run: {run.id}")
                except Exception as e:
                    print(f"Async error: {e}")

        asyncio.run(async_example())

    print("\n=== Complete! ===")


if __name__ == "__main__":
    main()
