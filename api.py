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

import requests
import asyncio
import aiohttp
import time
import logging
import json
import os
from typing import Optional, Dict, Any, List, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps, lru_cache
from threading import Lock
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums
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

# Configuration
@dataclass
class ClientConfig:
    api_token: str = field(default_factory=lambda: os.getenv("CODEGEN_API_TOKEN", ""))
    base_url: str = field(default_factory=lambda: os.getenv("CODEGEN_BASE_URL", "https://api.codegen.com/v1"))
    timeout: int = field(default_factory=lambda: int(os.getenv("CODEGEN_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("CODEGEN_MAX_RETRIES", "3")))
    rate_limit_buffer: float = 0.1

    def __post_init__(self):
        if not self.api_token:
            raise ValueError("API token is required. Set CODEGEN_API_TOKEN environment variable.")

# Data classes
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

# Exceptions
class ValidationError(Exception):
    pass

class CodegenAPIError(Exception):
    def __init__(self, message: str, status_code: int, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)

class RateLimitError(CodegenAPIError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds", 429)

# Rate Limiter
class RateLimiter:
    def __init__(self, requests_per_period: int, period_seconds: int):
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.requests = []
        self.lock = Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.period_seconds]
            
            if len(self.requests) >= self.requests_per_period:
                sleep_time = self.period_seconds - (now - self.requests[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.requests.append(now)

# Retry decorator
def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt == max_retries:
                        raise
                    time.sleep(e.retry_after)
                except requests.RequestException as e:
                    if attempt == max_retries:
                        raise CodegenAPIError(f"Request failed after {max_retries} retries", 0)
                    time.sleep(backoff_factor * (2 ** attempt))
            return None
        return wrapper
    return decorator

# Webhook Handler
class WebhookHandler:
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Register a handler for specific webhook events"""
        self.handlers[event_type] = handler

    def handle_webhook(self, payload: Dict[str, Any]):
        """Process incoming webhook payload"""
        event_type = payload.get("event_type")
        if event_type in self.handlers:
            self.handlers[event_type](payload)
        else:
            logger.warning(f"No handler registered for event type: {event_type}")

# Main Client
class CodegenClient:
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.headers = {"Authorization": f"Bearer {self.config.api_token}"}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.rate_limiter = RateLimiter(60, 60)  # 60 requests per 60 seconds
        self.request_count = 0
        self.start_time = datetime.now()
        self._cache = {}

    def _validate_pagination(self, skip: int, limit: int):
        if skip < 0:
            raise ValidationError("skip must be >= 0")
        if not (1 <= limit <= 100):
            raise ValidationError("limit must be between 1 and 100")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise RateLimitError(retry_after)

        if not response.ok:
            try:
                error_data = response.json()
            except:
                error_data = None
            raise CodegenAPIError(
                f"API request failed: {response.status_code}",
                response.status_code,
                error_data
            )
        
        return response.json()

    @retry_with_backoff(max_retries=3)
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        self.rate_limiter.wait_if_needed()
        self.request_count += 1
        
        start_time = time.time()
        logger.info(f"Making {method} request to {endpoint}")
        
        try:
            url = f"{self.config.base_url}{endpoint}"
            response = self.session.request(method, url, timeout=self.config.timeout, **kwargs)
            duration = time.time() - start_time
            
            logger.info(f"Request completed in {duration:.2f}s - Status: {response.status_code}")
            return self._handle_response(response)
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed after {duration:.2f}s: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get client usage statistics"""
        uptime = datetime.now() - self.start_time
        return {
            "requests_made": self.request_count,
            "uptime_seconds": uptime.total_seconds(),
            "requests_per_minute": self.request_count / (uptime.total_seconds() / 60) if uptime.total_seconds() > 0 else 0
        }

    # Users endpoints
    def get_users(self, org_id: str, skip: int = 0, limit: int = 100) -> UsersResponse:
        """Get paginated list of users for a specific organization."""
        self._validate_pagination(skip, limit)
        
        data = self._make_request(
            "GET", 
            f"/organizations/{org_id}/users",
            params={"skip": skip, "limit": limit}
        )
        
        return UsersResponse(
            items=[UserResponse(**user) for user in data["items"]],
            total=data["total"],
            page=data["page"],
            size=data["size"],
            pages=data["pages"]
        )

    def get_user(self, org_id: str, user_id: str) -> UserResponse:
        """Get details for a specific user in an organization."""
        data = self._make_request("GET", f"/organizations/{org_id}/users/{user_id}")
        return UserResponse(**data)

    @lru_cache(maxsize=128)
    def get_user_cached(self, org_id: str, user_id: str) -> UserResponse:
        """Cached version of get_user for frequently accessed users"""
        return self.get_user(org_id, user_id)

    def get_current_user(self) -> UserResponse:
        """Get current user information from API token."""
        data = self._make_request("GET", "/users/me")
        return UserResponse(**data)

    # Organizations endpoints
    def get_organizations(self, skip: int = 0, limit: int = 100) -> OrganizationsResponse:
        """Get organizations for the authenticated user."""
        self._validate_pagination(skip, limit)
        
        data = self._make_request(
            "GET", 
            "/organizations",
            params={"skip": skip, "limit": limit}
        )
        
        return OrganizationsResponse(
            items=[OrganizationResponse(
                id=org["id"],
                name=org["name"],
                settings=OrganizationSettings()
            ) for org in data["items"]],
            total=data["total"],
            page=data["page"],
            size=data["size"],
            pages=data["pages"]
        )

    # Agent endpoints
    def create_agent_run(
        self, 
        org_id: int, 
        prompt: str, 
        images: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentRunResponse:
        """Create a new agent run."""
        data = {
            "prompt": prompt,
            "images": images,
            "metadata": metadata
        }
        
        result = self._make_request(
            "POST", 
            f"/organizations/{org_id}/agent/run",
            json=data
        )
        
        return AgentRunResponse(
            id=result["id"],
            organization_id=result["organization_id"],
            status=result.get("status"),
            created_at=result.get("created_at"),
            web_url=result.get("web_url"),
            result=result.get("result"),
            source_type=SourceType(result["source_type"]) if result.get("source_type") else None,
            github_pull_requests=[
                GithubPullRequestResponse(**pr) 
                for pr in result.get("github_pull_requests", [])
            ],
            metadata=result.get("metadata")
        )

    def get_agent_run(self, org_id: int, agent_run_id: int) -> AgentRunResponse:
        """Retrieve the status and result of an agent run."""
        result = self._make_request("GET", f"/organizations/{org_id}/agent/run/{agent_run_id}")
        
        return AgentRunResponse(
            id=result["id"],
            organization_id=result["organization_id"],
            status=result.get("status"),
            created_at=result.get("created_at"),
            web_url=result.get("web_url"),
            result=result.get("result"),
            source_type=SourceType(result["source_type"]) if result.get("source_type") else None,
            github_pull_requests=[
                GithubPullRequestResponse(**pr) 
                for pr in result.get("github_pull_requests", [])
            ],
            metadata=result.get("metadata")
        )

    def list_agent_runs(
        self, 
        org_id: int, 
        user_id: Optional[int] = None,
        source_type: Optional[SourceType] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> AgentRunsResponse:
        """List agent runs for an organization with optional filtering."""
        self._validate_pagination(skip, limit)
        
        params = {"skip": skip, "limit": limit}
        if user_id:
            params["user_id"] = user_id
        if source_type:
            params["source_type"] = source_type.value
        
        data = self._make_request(
            "GET", 
            f"/organizations/{org_id}/agent/runs",
            params=params
        )
        
        return AgentRunsResponse(
            items=[
                AgentRunResponse(
                    id=run["id"],
                    organization_id=run["organization_id"],
                    status=run.get("status"),
                    created_at=run.get("created_at"),
                    web_url=run.get("web_url"),
                    result=run.get("result"),
                    source_type=SourceType(run["source_type"]) if run.get("source_type") else None,
                    github_pull_requests=[
                        GithubPullRequestResponse(**pr) 
                        for pr in run.get("github_pull_requests", [])
                    ],
                    metadata=run.get("metadata")
                ) for run in data["items"]
            ],
            total=data["total"],
            page=data["page"],
            size=data["size"],
            pages=data["pages"]
        )

    def resume_agent_run(
        self, 
        org_id: int, 
        agent_run_id: int, 
        prompt: str,
        images: Optional[List[str]] = None
    ) -> AgentRunResponse:
        """Resume a paused agent run."""
        data = {
            "agent_run_id": agent_run_id,
            "prompt": prompt,
            "images": images
        }
        
        result = self._make_request(
            "POST", 
            f"/organizations/{org_id}/agent/run/resume",
            json=data
        )
        
        return AgentRunResponse(
            id=result["id"],
            organization_id=result["organization_id"],
            status=result.get("status"),
            created_at=result.get("created_at"),
            web_url=result.get("web_url"),
            result=result.get("result"),
            source_type=SourceType(result["source_type"]) if result.get("source_type") else None,
            github_pull_requests=[
                GithubPullRequestResponse(**pr) 
                for pr in result.get("github_pull_requests", [])
            ],
            metadata=result.get("metadata")
        )

    # Alpha endpoints - Agent Run Logs
    def get_agent_run_logs(
        self, 
        org_id: int, 
        agent_run_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> AgentRunWithLogsResponse:
        """Retrieve an agent run with its logs using pagination (ALPHA)."""
        self._validate_pagination(skip, limit)
        
        data = self._make_request(
            "GET", 
            f"/organizations/{org_id}/agent/run/{agent_run_id}/logs",
            params={"skip": skip, "limit": limit}
        )
        
        return AgentRunWithLogsResponse(
            id=data["id"],
            organization_id=data["organization_id"],
            logs=[AgentRunLogResponse(**log) for log in data["logs"]],
            status=data.get("status"),
            created_at=data.get("created_at"),
            web_url=data.get("web_url"),
            result=data.get("result"),
            metadata=data.get("metadata"),
            total_logs=data.get("total_logs"),
            page=data.get("page"),
            size=data.get("size"),
            pages=data.get("pages")
        )

    def stream_all_logs(self, org_id: int, agent_run_id: int):
        """Stream all logs with automatic pagination"""
        skip = 0
        while True:
            response = self.get_agent_run_logs(org_id, agent_run_id, skip=skip, limit=100)
            for log in response.logs:
                yield log
            if len(response.logs) < 100:
                break
            skip += 100

# Async Client
class AsyncCodegenClient:
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.config.api_token}"},
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_users_stream(self, org_id: str) -> AsyncGenerator[UserResponse, None]:
        """Stream all users with automatic pagination"""
        skip = 0
        while True:
            # Note: You'd need to implement async versions of the methods
            # This is a simplified example
            params = {"skip": skip, "limit": 100}
            async with self.session.get(
                f"{self.config.base_url}/organizations/{org_id}/users",
                params=params
            ) as response:
                data = await response.json()
                for user in data["items"]:
                    yield UserResponse(**user)
                if len(data["items"]) < 100:
                    break
                skip += 100

# Usage example and webhook setup
if __name__ == "__main__":
    # Initialize client
    client = CodegenClient()
    
    # Setup webhook handler
    webhook_handler = WebhookHandler()
    
    @webhook_handler.register_handler("agent_run.completed")
    def on_agent_run_completed(payload: Dict[str, Any]):
        agent_run_id = payload["data"]["id"]
        print(f"Agent run {agent_run_id} completed!")
    
    @webhook_handler.register_handler("agent_run.failed")
    def on_agent_run_failed(payload: Dict[str, Any]):
        agent_run_id = payload["data"]["id"]
        error = payload["data"].get("error", "Unknown error")
        print(f"Agent run {agent_run_id} failed: {error}")
    
    # Get current user
    user = client.get_current_user()
    print(f"Current user: {user.github_username}")
    
    # Get organizations
    orgs = client.get_organizations()
    if orgs.items:
        org_id = orgs.items[0].id
        
        # Create agent run
        agent_run = client.create_agent_run(
            org_id=org_id,
            prompt="Help me refactor this code",
            metadata={"source": "api_client"}
        )
        print(f"Created agent run: {agent_run.id}")
        
        # Get agent run logs
        logs = client.get_agent_run_logs(org_id, agent_run.id)
        print(f"Agent run has {logs.total_logs} logs")
        
        # Stream all logs
        print("Streaming all logs:")
        for log in client.stream_all_logs(org_id, agent_run.id):
            print(f"[{log.created_at}] {log.message_type}: {log.thought}")
        
        # Get client stats
        stats = client.get_stats()
        print(f"Client stats: {stats}")

