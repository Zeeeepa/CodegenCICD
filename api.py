"""
Enhanced Codegen API Client - All-in-One Implementation
A comprehensive, production-ready Python client with advanced features:
- Async/Await Support with context managers
- Advanced Error Handling & Retry Logic
- Response Caching & Rate Limiting
- Comprehensive Logging & Monitoring
- Webhook Support & Real-time Updates
- Bulk Operations & Streaming
- Configuration Management
"""

import os
import json
import time
import asyncio
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps, lru_cache
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

# HTTP clients
import requests
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class SourceType(Enum):
    LOCAL = "LOCAL"
    SLACK = "SLACK"
    GITHUB = "GITHUB"
    GITHUB_CHECK_SUITE = "GITHUB_CHECK_SUITE"
    LINEAR = "LINEAR"
    API = "API"
    CHAT = "CHAT"
    JIRA = "JIRA"

class MessageType(Enum):
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
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

# ============================================================================
# EXCEPTIONS
# ============================================================================

class ValidationError(Exception):
    """Validation error for request parameters"""
    def __init__(self, message: str, field_errors: Optional[Dict[str, List[str]]] = None):
        self.message = message
        self.field_errors = field_errors or {}
        super().__init__(message)

class CodegenAPIError(Exception):
    """Base exception for Codegen API errors"""
    def __init__(self, message: str, status_code: int = 0, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)

class RateLimitError(CodegenAPIError):
    """Rate limiting error with retry information"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds", 429)

class AuthenticationError(CodegenAPIError):
    """Authentication/authorization error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)

class NotFoundError(CodegenAPIError):
    """Resource not found error"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)

class ConflictError(CodegenAPIError):
    """Conflict error (409)"""
    def __init__(self, message: str = "Conflict occurred"):
        super().__init__(message, 409)

class ServerError(CodegenAPIError):
    """Server-side error (5xx)"""
    def __init__(self, message: str = "Server error occurred"):
        super().__init__(message, 500)

class TimeoutError(CodegenAPIError):
    """Request timeout error"""
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, 408)

class NetworkError(CodegenAPIError):
    """Network connectivity error"""
    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message, 0)

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
    id: int
    email: Optional[str]
    github_user_id: str
    github_username: str
    avatar_url: Optional[str]
    full_name: Optional[str]

@dataclass
class GithubPullRequestResponse:
    id: int
    title: str
    url: str
    created_at: str

@dataclass
class AgentRunResponse:
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
    # Add specific settings fields as they become available
    pass

@dataclass
class OrganizationResponse:
    id: int
    name: str
    settings: OrganizationSettings

@dataclass
class PaginatedResponse:
    total: int
    page: int
    size: int
    pages: int

@dataclass
class UsersResponse(PaginatedResponse):
    items: List[UserResponse]

@dataclass
class AgentRunsResponse(PaginatedResponse):
    items: List[AgentRunResponse]

@dataclass
class OrganizationsResponse(PaginatedResponse):
    items: List[OrganizationResponse]

@dataclass
class AgentRunWithLogsResponse:
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

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ClientConfig:
    """Configuration for the Codegen client"""
    # Core settings
    api_token: str = field(default_factory=lambda: os.getenv("CODEGEN_API_TOKEN", ""))
    org_id: str = field(default_factory=lambda: os.getenv("CODEGEN_ORG_ID", ""))
    base_url: str = field(default_factory=lambda: os.getenv("CODEGEN_BASE_URL", "https://api.codegen.com/v1"))
    
    # Performance settings
    timeout: int = field(default_factory=lambda: int(os.getenv("CODEGEN_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("CODEGEN_MAX_RETRIES", "3")))
    retry_delay: float = field(default_factory=lambda: float(os.getenv("CODEGEN_RETRY_DELAY", "1.0")))
    
    # Rate limiting
    rate_limit_requests_per_period: int = field(default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_REQUESTS", "60")))
    rate_limit_period_seconds: int = field(default_factory=lambda: int(os.getenv("CODEGEN_RATE_LIMIT_PERIOD", "60")))
    rate_limit_buffer: float = 0.1
    
    # Caching
    enable_caching: bool = field(default_factory=lambda: os.getenv("CODEGEN_ENABLE_CACHING", "true").lower() == "true")
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("CODEGEN_CACHE_TTL", "300")))
    cache_max_size: int = field(default_factory=lambda: int(os.getenv("CODEGEN_CACHE_MAX_SIZE", "128")))
    
    # Features
    enable_webhooks: bool = field(default_factory=lambda: os.getenv("CODEGEN_ENABLE_WEBHOOKS", "true").lower() == "true")
    enable_bulk_operations: bool = field(default_factory=lambda: os.getenv("CODEGEN_ENABLE_BULK_OPERATIONS", "true").lower() == "true")
    enable_streaming: bool = field(default_factory=lambda: os.getenv("CODEGEN_ENABLE_STREAMING", "true").lower() == "true")
    enable_metrics: bool = field(default_factory=lambda: os.getenv("CODEGEN_ENABLE_METRICS", "true").lower() == "true")
    
    # Bulk operations
    bulk_max_workers: int = field(default_factory=lambda: int(os.getenv("CODEGEN_BULK_MAX_WORKERS", "5")))
    bulk_batch_size: int = field(default_factory=lambda: int(os.getenv("CODEGEN_BULK_BATCH_SIZE", "100")))
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("CODEGEN_LOG_LEVEL", "INFO"))
    log_requests: bool = field(default_factory=lambda: os.getenv("CODEGEN_LOG_REQUESTS", "true").lower() == "true")
    log_responses: bool = field(default_factory=lambda: os.getenv("CODEGEN_LOG_RESPONSES", "false").lower() == "true")
    
    def __post_init__(self):
        if not self.api_token:
            raise ValueError("API token is required. Set CODEGEN_API_TOKEN environment variable or provide it directly.")
        
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
            log_responses=True
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
            log_responses=False
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
            log_level="WARNING"
        )
    
    @staticmethod
    def testing() -> ClientConfig:
        """Testing configuration with minimal caching and retries"""
        return ClientConfig(
            timeout=10,
            max_retries=1,
            enable_caching=False,
            rate_limit_requests_per_period=10,
            log_level="DEBUG"
        )

# ============================================================================
# UTILITY CLASSES
# ============================================================================

def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0):
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
                        raise CodegenAPIError(f"Request failed after {max_retries} retries: {str(e)}", 0)
                    sleep_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {sleep_time}s: {str(e)}")
                    time.sleep(sleep_time)
            return None
        return wrapper
    return decorator

class RateLimiter:
    """Thread-safe rate limiter"""
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
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.period_seconds]
            
            if len(self.requests) >= self.requests_per_period:
                sleep_time = self.period_seconds - (now - self.requests[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            self.requests.append(now)

class CacheManager:
    """Simple in-memory cache with TTL support"""
    def __init__(self, max_size: int = 128, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._timestamps = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check if expired
            if time.time() - self._timestamps[key] > self.ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                return None
            
            return self._cache[key]

    def set(self, key: str, value: Any):
        """Set value in cache with TTL"""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = min(self._timestamps.keys(), key=self._timestamps.get)
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def clear(self):
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

class WebhookHandler:
    """Webhook event handler with signature verification"""
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Register a handler for specific webhook events"""
        self.handlers[event_type] = handler
        logger.info(f"Registered webhook handler for event type: {event_type}")

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature"""
        if not self.secret_key:
            logger.warning("No secret key configured for webhook signature verification")
            return True
        
        expected_signature = hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    def handle_webhook(self, payload: Dict[str, Any], signature: Optional[str] = None):
        """Process incoming webhook payload"""
        try:
            # Verify signature if provided
            if signature and not self.verify_signature(json.dumps(payload).encode(), signature):
                raise WebhookError("Invalid webhook signature")
            
            event_type = payload.get("event_type")
            if not event_type:
                raise WebhookError("Missing event_type in webhook payload")
            
            if event_type in self.handlers:
                self.handlers[event_type](payload)
                logger.info(f"Successfully processed webhook event: {event_type}")
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise WebhookError(f"Webhook processing failed: {str(e)}")

class BulkOperationManager:
    """Manager for bulk operations with concurrency control"""
    def __init__(self, max_workers: int = 5, batch_size: int = 100):
        self.max_workers = max_workers
        self.batch_size = batch_size

    def execute_bulk_operation(
        self, 
        operation_func: Callable,
        items: List[Any],
        *args,
        **kwargs
    ) -> BulkOperationResult:
        """Execute a bulk operation with error handling and metrics"""
        start_time = time.time()
        results = []
        errors = []
        successful_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(operation_func, item, *args, **kwargs): item 
                for item in items
            }
            
            # Collect results
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                    successful_count += 1
                except Exception as e:
                    error_info = {
                        "item": str(item),
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    errors.append(error_info)
                    logger.error(f"Bulk operation failed for item {item}: {str(e)}")
        
        duration = time.time() - start_time
        success_rate = successful_count / len(items) if items else 0
        
        return BulkOperationResult(
            total_items=len(items),
            successful_items=successful_count,
            failed_items=len(errors),
            success_rate=success_rate,
            duration_seconds=duration,
            errors=errors,
            results=results
        )

class MetricsCollector:
    """Collect and track client metrics"""
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        self.response_times = []
        self.status_codes = {}
        self._lock = Lock()

    def record_request(self, duration: float, status_code: int):
        """Record a request with its duration and status code"""
        with self._lock:
            self.request_count += 1
            self.response_times.append(duration)
            
            if status_code >= 400:
                self.error_count += 1
            
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics"""
        with self._lock:
            uptime = datetime.now() - self.start_time
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            return {
                "uptime_seconds": uptime.total_seconds(),
                "total_requests": self.request_count,
                "total_errors": self.error_count,
                "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
                "requests_per_minute": self.request_count / (uptime.total_seconds() / 60) if uptime.total_seconds() > 0 else 0,
                "average_response_time": avg_response_time,
                "status_code_distribution": self.status_codes.copy(),
                "recent_response_times": self.response_times[-10:] if self.response_times else []
            }

    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.request_count = 0
            self.error_count = 0
            self.start_time = datetime.now()
            self.response_times.clear()
            self.status_codes.clear()

# ============================================================================
# MAIN CLIENT CLASSES
# ============================================================================

class CodegenClient:
    """Enhanced synchronous Codegen API client with advanced features"""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.headers = {"Authorization": f"Bearer {self.config.api_token}"}
        
        # Initialize components
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            self.config.rate_limit_requests_per_period,
            self.config.rate_limit_period_seconds
        )
        
        # Caching
        self.cache = CacheManager(
            max_size=self.config.cache_max_size,
            ttl_seconds=self.config.cache_ttl_seconds
        ) if self.config.enable_caching else None
        
        # Webhooks
        self.webhook_handler = WebhookHandler() if self.config.enable_webhooks else None
        
        # Bulk operations
        self.bulk_manager = BulkOperationManager(
            max_workers=self.config.bulk_max_workers,
            batch_size=self.config.bulk_batch_size
        ) if self.config.enable_bulk_operations else None
        
        # Metrics
        self.metrics = MetricsCollector() if self.config.enable_metrics else None
        
        logger.info(f"Initialized CodegenClient with base URL: {self.config.base_url}")

    def _validate_pagination(self, skip: int, limit: int):
        """Validate pagination parameters"""
        if skip < 0:
            raise ValidationError("skip must be >= 0")
        if not (1 <= limit <= 100):
            raise ValidationError("limit must be between 1 and 100")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle HTTP response with comprehensive error handling"""
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(retry_after)
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API token or insufficient permissions")
        elif response.status_code == 404:
            raise NotFoundError("Requested resource not found")
        elif response.status_code == 409:
            raise ConflictError("Resource conflict occurred")
        elif response.status_code >= 500:
            raise ServerError(f"Server error: {response.status_code}")
        elif not response.ok:
            try:
                error_data = response.json()
                message = error_data.get('message', f'API request failed: {response.status_code}')
            except:
                message = f"API request failed: {response.status_code}"
            raise CodegenAPIError(message, response.status_code, error_data if 'error_data' in locals() else None)
        
        return response.json()

    @retry_with_backoff(max_retries=3)
    def _make_request(self, method: str, endpoint: str, use_cache: bool = False, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with rate limiting, caching, and metrics"""
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Check cache
        cache_key = None
        if use_cache and self.cache and method.upper() == 'GET':
            cache_key = f"{method}:{endpoint}:{hash(str(kwargs))}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {endpoint}")
                return cached_result
        
        # Make request
        start_time = time.time()
        url = f"{self.config.base_url}{endpoint}"
        
        if self.config.log_requests:
            logger.info(f"Making {method} request to {endpoint}")
        
        try:
            response = self.session.request(method, url, timeout=self.config.timeout, **kwargs)
            duration = time.time() - start_time
            
            if self.config.log_requests:
                logger.info(f"Request completed in {duration:.2f}s - Status: {response.status_code}")
            
            # Record metrics
            if self.metrics:
                self.metrics.record_request(duration, response.status_code)
            
            result = self._handle_response(response)
            
            # Cache successful GET requests
            if cache_key and response.ok:
                self.cache.set(cache_key, result)
            
            return result
            
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_request(duration, 408)
            raise TimeoutError(f"Request timed out after {self.config.timeout}s")
        except requests.exceptions.ConnectionError as e:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_request(duration, 0)
            raise NetworkError(f"Network error: {str(e)}")
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed after {duration:.2f}s: {str(e)}")
            if self.metrics:
                self.metrics.record_request(duration, 0)
            raise

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
            use_cache=True
        )
        
        return UsersResponse(
            items=[UserResponse(**user) for user in response["items"]],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"]
        )

    def get_user(self, org_id: str, user_id: str) -> UserResponse:
        """Get details for a specific user in an organization"""
        response = self._make_request(
            "GET", 
            f"/organizations/{org_id}/users/{user_id}",
            use_cache=True
        )
        return UserResponse(**response)

    @lru_cache(maxsize=32)
    def get_user_cached(self, org_id: str, user_id: str) -> UserResponse:
        """Cached version of get_user for frequently accessed users"""
        return self.get_user(org_id, user_id)

    def get_current_user(self) -> UserResponse:
        """Get current user information from API token"""
        response = self._make_request("GET", "/users/me", use_cache=True)
        return UserResponse(**response)

    # ========================================================================
    # ORGANIZATION ENDPOINTS
    # ========================================================================

    def get_organizations(self, skip: int = 0, limit: int = 100) -> OrganizationsResponse:
        """Get organizations for the authenticated user"""
        self._validate_pagination(skip, limit)
        
        response = self._make_request(
            "GET", 
            "/organizations",
            params={"skip": skip, "limit": limit},
            use_cache=True
        )
        
        return OrganizationsResponse(
            items=[OrganizationResponse(
                id=org["id"],
                name=org["name"],
                settings=OrganizationSettings()  # Populate as needed
            ) for org in response["items"]],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"]
        )

    # ========================================================================
    # AGENT ENDPOINTS
    # ========================================================================

    def create_agent_run(
        self, 
        org_id: int, 
        prompt: str, 
        images: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentRunResponse:
        """Create a new agent run"""
        # Validate inputs
        if not prompt or len(prompt.strip()) == 0:
            raise ValidationError("Prompt cannot be empty")
        if len(prompt) > 10000:
            raise ValidationError("Prompt cannot exceed 10,000 characters")
        if images and len(images) > 10:
            raise ValidationError("Cannot include more than 10 images")
        
        data = {
            "prompt": prompt,
            "images": images,
            "metadata": metadata
        }
        
        response = self._make_request(
            "POST", 
            f"/organizations/{org_id}/agent/run",
            json=data
        )
        
        return self._parse_agent_run_response(response)

    def get_agent_run(self, org_id: int, agent_run_id: int) -> AgentRunResponse:
        """Retrieve the status and result of an agent run"""
        response = self._make_request(
            "GET", 
            f"/organizations/{org_id}/agent/run/{agent_run_id}",
            use_cache=True
        )
        return self._parse_agent_run_response(response)

    def list_agent_runs(
        self, 
        org_id: int, 
        user_id: Optional[int] = None,
        source_type: Optional[SourceType] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> AgentRunsResponse:
        """List agent runs for an organization with optional filtering"""
        self._validate_pagination(skip, limit)
        
        params = {"skip": skip, "limit": limit}
        if user_id:
            params["user_id"] = user_id
        if source_type:
            params["source_type"] = source_type.value
        
        response = self._make_request(
            "GET", 
            f"/organizations/{org_id}/agent/runs",
            params=params,
            use_cache=True
        )
        
        return AgentRunsResponse(
            items=[self._parse_agent_run_response(run) for run in response["items"]],
            total=response["total"],
            page=response["page"],
            size=response["size"],
            pages=response["pages"]
        )

    def resume_agent_run(
        self, 
        org_id: int, 
        agent_run_id: int, 
        prompt: str,
        images: Optional[List[str]] = None
    ) -> AgentRunResponse:
        """Resume a paused agent run"""
        if not prompt or len(prompt.strip()) == 0:
            raise ValidationError("Prompt cannot be empty")
        
        data = {
            "agent_run_id": agent_run_id,
            "prompt": prompt,
            "images": images
        }
        
        response = self._make_request(
            "POST", 
            f"/organizations/{org_id}/agent/run/resume",
            json=data
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
            source_type=SourceType(data["source_type"]) if data.get("source_type") else None,
            github_pull_requests=[
                GithubPullRequestResponse(**pr) 
                for pr in data.get("github_pull_requests", [])
            ],
            metadata=data.get("metadata")
        )

    # ========================================================================
    # ALPHA ENDPOINTS
    # ========================================================================

    def get_agent_run_logs(
        self, 
        org_id: int, 
        agent_run_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> AgentRunWithLogsResponse:
        """Retrieve an agent run with its logs using pagination (ALPHA)"""
        self._validate_pagination(skip, limit)
        
        response = self._make_request(
            "GET", 
            f"/alpha/organizations/{org_id}/agent/run/{agent_run_id}/logs",
            params={"skip": skip, "limit": limit},
            use_cache=True
        )
        
        return AgentRunWithLogsResponse(
            id=response["id"],
            organization_id=response["organization_id"],
            logs=[AgentRunLogResponse(**log) for log in response["logs"]],
            status=response.get("status"),
            created_at=response.get("created_at"),
            web_url=response.get("web_url"),
            result=response.get("result"),
            metadata=response.get("metadata"),
            total_logs=response.get("total_logs"),
            page=response.get("page"),
            size=response.get("size"),
            pages=response.get("pages")
        )

    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================

    def bulk_get_users(self, org_id: str, user_ids: List[str]) -> BulkOperationResult:
        """Fetch multiple users concurrently"""
        if not self.bulk_manager:
            raise BulkOperationError("Bulk operations are disabled")
        
        return self.bulk_manager.execute_bulk_operation(
            self.get_user, user_ids, org_id
        )

    def bulk_create_agent_runs(
        self, 
        org_id: int, 
        run_configs: List[Dict[str, Any]]
    ) -> BulkOperationResult:
        """Create multiple agent runs concurrently"""
        if not self.bulk_manager:
            raise BulkOperationError("Bulk operations are disabled")
        
        def create_run(config):
            return self.create_agent_run(
                org_id=org_id,
                prompt=config["prompt"],
                images=config.get("images"),
                metadata=config.get("metadata")
            )
        
        return self.bulk_manager.execute_bulk_operation(create_run, run_configs)

    # ========================================================================
    # STREAMING METHODS
    # ========================================================================

    def get_all_users(self, org_id: str) -> List[UserResponse]:
        """Get all users with automatic pagination"""
        if not self.config.enable_streaming:
            raise ValidationError("Streaming is disabled")
        
        all_users = []
        skip = 0
        
        while True:
            response = self.get_users(org_id, skip=skip, limit=100)
            all_users.extend(response.items)
            
            if len(response.items) < 100:
                break
            skip += 100
        
        return all_users

    def get_all_agent_runs(self, org_id: int) -> List[AgentRunResponse]:
        """Get all agent runs with automatic pagination"""
        if not self.config.enable_streaming:
            raise ValidationError("Streaming is disabled")
        
        all_runs = []
        skip = 0
        
        while True:
            response = self.list_agent_runs(org_id, skip=skip, limit=100)
            all_runs.extend(response.items)
            
            if len(response.items) < 100:
                break
            skip += 100
        
        return all_runs

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive client statistics"""
        stats = {
            "config": {
                "base_url": self.config.base_url,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "rate_limit_requests_per_period": self.config.rate_limit_requests_per_period,
                "caching_enabled": self.config.enable_caching,
                "webhooks_enabled": self.config.enable_webhooks,
                "bulk_operations_enabled": self.config.enable_bulk_operations,
                "streaming_enabled": self.config.enable_streaming,
                "metrics_enabled": self.config.enable_metrics
            }
        }
        
        if self.metrics:
            stats["metrics"] = self.metrics.get_stats()
        
        if self.cache:
            stats["cache"] = {
                "max_size": self.cache.max_size,
                "ttl_seconds": self.cache.ttl_seconds,
                "current_size": len(self.cache._cache)
            }
        
        return stats

    def clear_cache(self):
        """Clear all cached data"""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")

    def reset_metrics(self):
        """Reset all metrics"""
        if self.metrics:
            self.metrics.reset()
            logger.info("Metrics reset")

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
            
            # Initialize components (similar to sync client)
            self.rate_limiter = RateLimiter(
                self.config.rate_limit_requests_per_period,
                self.config.rate_limit_period_seconds
            )
            
            self.cache = CacheManager(
                max_size=self.config.cache_max_size,
                ttl_seconds=self.config.cache_ttl_seconds
            ) if self.config.enable_caching else None
            
            self.webhook_handler = WebhookHandler() if self.config.enable_webhooks else None
            self.metrics = MetricsCollector() if self.config.enable_metrics else None
            
            logger.info(f"Initialized AsyncCodegenClient with base URL: {self.config.base_url}")

        async def __aenter__(self):
            """Async context manager entry"""
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.config.api_token}"},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Async context manager exit"""
            if self.session:
                await self.session.close()

        async def _make_request(self, method: str, endpoint: str, use_cache: bool = False, **kwargs) -> Dict[str, Any]:
            """Make async HTTP request with rate limiting, caching, and metrics"""
            if not self.session:
                raise RuntimeError("Client not initialized. Use 'async with' context manager.")
            
            # Rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Check cache
            cache_key = None
            if use_cache and self.cache and method.upper() == 'GET':
                cache_key = f"{method}:{endpoint}:{hash(str(kwargs))}"
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {endpoint}")
                    return cached_result
            
            # Make request
            start_time = time.time()
            url = f"{self.config.base_url}{endpoint}"
            
            if self.config.log_requests:
                logger.info(f"Making async {method} request to {endpoint}")
            
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    duration = time.time() - start_time
                    
                    if self.config.log_requests:
                        logger.info(f"Async request completed in {duration:.2f}s - Status: {response.status}")
                    
                    # Record metrics
                    if self.metrics:
                        self.metrics.record_request(duration, response.status)
                    
                    # Handle response
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise RateLimitError(retry_after)
                    elif response.status == 401:
                        raise AuthenticationError("Invalid API token or insufficient permissions")
                    elif response.status == 404:
                        raise NotFoundError("Requested resource not found")
                    elif response.status >= 500:
                        raise ServerError(f"Server error: {response.status}")
                    elif not response.ok:
                        try:
                            error_data = await response.json()
                            message = error_data.get('message', f'API request failed: {response.status}')
                        except:
                            message = f"API request failed: {response.status}"
                        raise CodegenAPIError(message, response.status, error_data if 'error_data' in locals() else None)
                    
                    result = await response.json()
                    
                    # Cache successful GET requests
                    if cache_key and response.ok:
                        self.cache.set(cache_key, result)
                    
                    return result
                    
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                if self.metrics:
                    self.metrics.record_request(duration, 408)
                raise TimeoutError(f"Request timed out after {self.config.timeout}s")
            except aiohttp.ClientError as e:
                duration = time.time() - start_time
                if self.metrics:
                    self.metrics.record_request(duration, 0)
                raise NetworkError(f"Network error: {str(e)}")

        # Async versions of main methods
        async def get_current_user(self) -> UserResponse:
            """Get current user information from API token"""
            response = await self._make_request("GET", "/users/me", use_cache=True)
            return UserResponse(**response)

        async def create_agent_run(
            self, 
            org_id: int, 
            prompt: str, 
            images: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None
        ) -> AgentRunResponse:
            """Create a new agent run"""
            if not prompt or len(prompt.strip()) == 0:
                raise ValidationError("Prompt cannot be empty")
            
            data = {
                "prompt": prompt,
                "images": images,
                "metadata": metadata
            }
            
            response = await self._make_request(
                "POST", 
                f"/organizations/{org_id}/agent/run",
                json=data
            )
            
            return AgentRunResponse(
                id=response["id"],
                organization_id=response["organization_id"],
                status=response.get("status"),
                created_at=response.get("created_at"),
                web_url=response.get("web_url"),
                result=response.get("result"),
                source_type=SourceType(response["source_type"]) if response.get("source_type") else None,
                github_pull_requests=[
                    GithubPullRequestResponse(**pr) 
                    for pr in response.get("github_pull_requests", [])
                ],
                metadata=response.get("metadata")
            )

        async def get_users_stream(self, org_id: str) -> AsyncGenerator[UserResponse, None]:
            """Stream all users with automatic pagination"""
            skip = 0
            while True:
                response = await self._make_request(
                    "GET", 
                    f"/organizations/{org_id}/users",
                    params={"skip": skip, "limit": 100},
                    use_cache=True
                )
                
                users_response = UsersResponse(
                    items=[UserResponse(**user) for user in response["items"]],
                    total=response["total"],
                    page=response["page"],
                    size=response["size"],
                    pages=response["pages"]
                )
                
                for user in users_response.items:
                    yield user
                
                if len(users_response.items) < 100:
                    break
                skip += 100

        def get_stats(self) -> Dict[str, Any]:
            """Get comprehensive client statistics"""
            stats = {
                "config": {
                    "base_url": self.config.base_url,
                    "timeout": self.config.timeout,
                    "async_client": True
                }
            }
            
            if self.metrics:
                stats["metrics"] = self.metrics.get_stats()
            
            return stats

# ============================================================================
# USAGE EXAMPLES AND MAIN
# ============================================================================

def main():
    """Example usage of the enhanced Codegen client"""
    
    # Example 1: Basic usage with default configuration
    print("=== Basic Usage ===")
    client = CodegenClient()
    
    try:
        # Get current user
        user = client.get_current_user()
        print(f"Current user: {user.github_username}")
        
        # Get organizations
        orgs = client.get_organizations()
        if orgs.items:
            org_id = orgs.items[0].id
            print(f"Using organization: {orgs.items[0].name}")
            
            # Create agent run
            agent_run = client.create_agent_run(
                org_id=org_id,
                prompt="Help me refactor this code",
                metadata={"source": "enhanced_api_client", "version": "2.0"}
            )
            print(f"Created agent run: {agent_run.id}")
            
            # Get agent run logs
            logs = client.get_agent_run_logs(org_id, agent_run.id)
            print(f"Agent run has {logs.total_logs} logs")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
    
    # Example 2: Using configuration presets
    print("\n=== Using Configuration Presets ===")
    dev_config = ConfigPresets.development()
    with CodegenClient(dev_config) as client:
        stats = client.get_stats()
        print(f"Client stats: {stats}")
    
    # Example 3: Webhook handling
    print("\n=== Webhook Handling ===")
    client = CodegenClient()
    
    if client.webhook_handler:
        @client.webhook_handler.register_handler("agent_run.completed")
        def on_agent_run_completed(payload: Dict[str, Any]):
            agent_run_id = payload["data"]["id"]
            print(f"Agent run {agent_run_id} completed!")
        
        # Simulate webhook payload
        webhook_payload = {
            "event_type": "agent_run.completed",
            "data": {"id": 12345},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            client.webhook_handler.handle_webhook(webhook_payload)
        except Exception as e:
            print(f"Webhook error: {e}")
    
    client.close()

if __name__ == "__main__":
    main()
